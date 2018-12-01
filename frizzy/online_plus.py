import time
import timeit
import datetime
import asyncio
import aiohttp
import requests
import pytz
import traceback
import sys
from typing import List, Dict, Any
import threading
from frizzy.utils import log_debug, log_warning, BaseOrderItem, AsyncOrderItem, ThreadOrderItem, OrderProcessor


class OnlinePlusOrderProcessor(OrderProcessor):

    DEFAULT_HOST = 'onlineplus.mofidonline.com'

    def get_default_host(self):
        return OnlinePlusOrderProcessor.DEFAULT_HOST

    @staticmethod
    def get_send_order_url(host: str) -> str:
        return 'https://'+host+'/Customer/SendOrder'

    @staticmethod
    def get_order_side_int(order_side_str: str) -> int:
        if order_side_str == 'buy':
            return 65
        else:
            return 86

    @staticmethod
    def get_order_side_title(order_side_str: str) -> str:
        if order_side_str == 'buy':
            return "خرید"
        else:
            return "فروش"

    @staticmethod
    def get_headers_with_cookie(host: str, order_item: BaseOrderItem) -> Dict[str, Any]:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.8,fa;q=0.6',
            "content-type": "application/json;charset=UTF-8",
            "cookie": order_item.cookie,
            "host": host,
            "origin": "https://"+host,
            "referer": "https://"+host+"/Home/Index",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
        }

    @staticmethod
    def get_temp_date(order_item: BaseOrderItem) -> Dict[str, Any]:
        return {
            'FinancialProvider': "نزد کارگزار",
            'FinancialProviderId': 1,
            'FinancialProviderObject': {
                'Title': 'نزد کارگزار',
                'Value': 1
            },
            'isin': order_item.isin_code,
            'maxShow': 0,
            'minimumQuantity': 0,
            'orderCount': order_item.quantity,
            'orderPrice': order_item.price,
            'orderSide': OnlinePlusOrderProcessor.get_order_side_int(order_item.side),
            'orderSideStr': OnlinePlusOrderProcessor.get_order_side_title(order_item.side),
            'orderType': 75,
            'orderValidity': 74,
            'orderValiditydate': '',
            'orderid': -1,
            'symbolId': 0,
            'symboleTitle': order_item.symbol,
            'triggerPrice': 0
        }

    # noinspection PyMethodMayBeStatic
    async def send_order_async(self,
                               host: str,
                               async_order: AsyncOrderItem,
                               session: aiohttp.ClientSession, sem: asyncio.Semaphore, datetime_end: datetime.datetime):
        headers = OnlinePlusOrderProcessor.get_headers_with_cookie(host, async_order)
        tmp_data = OnlinePlusOrderProcessor.get_temp_date(async_order)
        send_order_url = OnlinePlusOrderProcessor.get_send_order_url(host=host)
        # acquire a semaphore
        async with sem:
            try:
                dt_now = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran"))
                tic = timeit.default_timer()
                if dt_now <= datetime_end:
                    try:
                        async with session.post(url=send_order_url, json=tmp_data, headers=headers, verify_ssl=False) as resp:
                            # pass
                            toc = timeit.default_timer()
                            log_debug("resp:" + await resp. text() + ", sendTime: " + dt_now.strftime("%H:%M:%S.%f") + ', duration:' + str(toc-tic) + ' seconds')  # delete later
                            # log_debug("resp:"+str(resp.status)+", sendTime: "+dt_now.strftime("%H:%M:%S.%f")+', duration:'+str(toc-tic) +' seconds')
                    except Exception as ex:
                        log_warning(str(ex) + '\n' + traceback.format_exc())
                else:
                    # this usually happens if a lot of tasks are waiting behind semaphore.
                    # since time has passed the datetime_end, we should not make new request
                    log_debug("time is passed of datetime_end so we do not make new request")
            except:
                log_debug("Exception happened when sending request: "+traceback. format_exc())

    async def send_orders_async(self,
                                host: str,
                                async_order: AsyncOrderItem,
                                datetime_start: datetime.datetime, datetime_end: datetime.datetime):
        tasks = []
        sem = asyncio.Semaphore(async_order.limit)
        delta_time = 1.0 / async_order.request_per_second

        timeout = aiohttp.ClientTimeout(total=40, connect=30)  # unit is seconds

        connector = aiohttp.TCPConnector(limit=None, verify_ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            a = 0
            while True:
                if datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) < datetime_start:
                    await asyncio.sleep(0.1)
                    continue
                if datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) > datetime_end:
                    break
                a += 1
                # if a%50 ==49:# delete this later. just for test
                #    await asyncio.sleep(1)
                log_debug(str(a)+" sending req at:"+str(datetime. datetime.now(tz=pytz . timezone("Asia/Tehran"))))

                coro = self.send_order_async(
                    host=host,
                    async_order=async_order,
                    session=session,
                    sem=sem,
                    datetime_end=datetime_end)
                task = asyncio.ensure_future(coro)
                tasks.append(task)
                # await asyncio.sleep(0) # if we do this, we send all requests at once
                # it is better to send requests uniformly spread over time
                await asyncio.sleep(delta_time*0.7)
            log_debug('waiting for tasks')
            if len(tasks) != 0:
                await asyncio.wait(tasks)
                log_debug('wait finished')

    def process_orders_async(self,
                             host: str,
                             async_orders: List[AsyncOrderItem],
                             datetime_start: datetime.datetime,
                             datetime_end: datetime.datetime):

        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()

        async_tasks = []
        for async_order in async_orders:
            async_tasks.append(
                self.send_orders_async(
                    host=host,
                    async_order=async_order,
                    datetime_start=datetime_start,
                    datetime_end=datetime_end)
            )
        log_debug('waiting for ' + str(len(async_tasks)) + ' tasks')
        loop.run_until_complete(asyncio.wait(async_tasks))

    # noinspection PyMethodMayBeStatic
    def send_thread_order_until_time(self,
                                     host: str,
                                     threaded_order: ThreadOrderItem,
                                     datetime_start: datetime.datetime, datetime_end: datetime.datetime, headers: Dict[str, Any]):

        tmp_data = OnlinePlusOrderProcessor.get_temp_date(threaded_order)
        send_order_url = OnlinePlusOrderProcessor.get_send_order_url(host=host)

        total_wait_time = (datetime_start - datetime.datetime.now(tz=pytz.timezone("Asia/Tehran"))).total_seconds()
        if total_wait_time > 0:
            log_debug('waiting '+str(total_wait_time)+' seconds')
            time.sleep(total_wait_time)
        dt_now = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran"))
        while dt_now < datetime_end:
            tic = timeit.default_timer()
            log_debug('sending order')
            try:
                o = requests.post(url=send_order_url, json=tmp_data, headers=headers, timeout=10000)
                log_debug('order id:' + str(o.text))
            except Exception as ex:
                log_debug(str(ex))
            toc = timeit.default_timer()
            log_debug('order for '+threaded_order.isin_code+' sent in ' + str(toc - tic) + ' seconds (' + dt_now.strftime('%H:%M:%S.%f') + ')')
            # time.sleep(0.5)
            time.sleep(0.001)
            dt_now = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran"))
        log_debug('Thread for '+threaded_order.isin_code+' finished')

    def send_thread_orders(self,
                           host: str,
                           thread_orders: List[ThreadOrderItem],
                           datetime_start: datetime.datetime, datetime_end: datetime.datetime):
        log_debug('Starting threads from '+datetime_start.strftime('%H:%M:%S.%f')+' to '+datetime_end.strftime('%H:%M:%S.%f'))
        for threaded_order in thread_orders:
            for i in range(0, threaded_order.threads):
                headers = OnlinePlusOrderProcessor.get_headers_with_cookie(host, threaded_order)
                threading.Thread(target=self.send_thread_order_until_time, args=(host,
                                                                                 threaded_order,
                                                                                 datetime_start, datetime_end, headers)).start()
        log_debug('All threads started')


if __name__ == "__main__":
    data = dict(map(lambda x: x.lstrip('-').split('='), sys.argv[1:]))
    isin_code = data['i']
    quantity = int(data['q'])
    price = int(data['p'])
    order_side = data['s']
    symbol = data['sm']
    user_cookie = data['c']
    broker_host = data['h']
    test = data.get('t', 'false')
    limit = int(data.get('l', 10000))
    rps = int(data.get('r', 100))
    if test:
        dt_start = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) + datetime.timedelta(seconds=5)
        dt_end = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) + datetime.timedelta(seconds=5 + 5)
    else:
        dt_start = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")).replace(hour=8, minute=29, second=50, microsecond=0)
        dt_end = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")).replace(hour=8, minute=30, second=5, microsecond=0)
    OnlinePlusOrderProcessor().process_orders_async(host=broker_host,
                                                    async_orders=[AsyncOrderItem(isin_code=isin_code,
                                                                                 symbol=symbol,
                                                                                 quantity=quantity,
                                                                                 price=price,
                                                                                 side=order_side,
                                                                                 cookie=user_cookie,
                                                                                 request_per_second=rps,
                                                                                 limit=limit,
                                                                                 cookie2=None,
                                                                                 instrument_id=None,
                                                                                 customer_id=None,
                                                                                 customer_title=None)],
                                                    datetime_start=dt_start, datetime_end=dt_end)
