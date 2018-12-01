from typing import Optional, Any
import logging
from typing import List
import threading
import abc
import datetime
import pytz


logger = logging.getLogger('kappa')


def log_debug(message: str):
    logger.debug(message)


def log_warning(message: str):
    logger.warning(message)


def log_error(message: str):
    logger.error(message)


class BaseOrderItem:
    def __init__(self, isin_code: str, symbol: str, quantity: int, price: int, side: str, cookie: str, cookie2: Optional[str],
                 instrument_id: Optional[int], customer_id: Optional[int], customer_title: Optional[str]):
        super(BaseOrderItem, self).__init__()
        self.isin_code = isin_code
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.side = side
        self.cookie = cookie
        self.cookie2 = cookie2

        self.instrument_id = instrument_id
        self.customer_id = customer_id
        self.customer_title = customer_title


class ThreadOrderItem(BaseOrderItem):
    def __init__(self, isin_code: str, symbol: str, quantity: int, price: int, side: str, cookie: str, cookie2: Optional[str],
                 instrument_id: Optional[int], customer_id: Optional[int], customer_title: Optional[str],
                 threads: int):
        super(ThreadOrderItem, self).__init__(isin_code=isin_code, symbol=symbol, quantity=quantity, price=price, side=side, cookie=cookie, cookie2=cookie2,
                                              instrument_id=instrument_id, customer_id=customer_id, customer_title=customer_title)
        self.threads = threads


class AsyncOrderItem(BaseOrderItem):
    def __init__(self, isin_code: str, symbol: str, quantity: int, price: int, side: str, cookie: str, cookie2: Optional[str],
                 instrument_id: Optional[int], customer_id: Optional[int], customer_title: Optional[str],
                 request_per_second: int, limit: int):
        super(AsyncOrderItem, self).__init__(isin_code=isin_code, symbol=symbol, quantity=quantity, price=price, side=side, cookie=cookie, cookie2=cookie2,
                                             instrument_id=instrument_id, customer_id=customer_id, customer_title=customer_title)
        self.request_per_second = request_per_second
        self.limit = limit


class OrderRequestItem:
    ORDER_TYPE_ASYNC = 'async'
    ORDER_TYPE_THREADED = 'thread'

    def __init__(self, isin_code: str, symbol: str, instrument_id: Optional[int],
                 customer_id: Optional[int], customer_title: Optional[str],
                 quantity: int, price: int, side: str,
                 cookie: str, cookie2: Optional[str],
                 request_per_second: Optional[int], limit: Optional[int], threads: Optional[int]):
        super(OrderRequestItem, self).__init__()
        self.isin_code = isin_code
        self.symbol = symbol
        self.instrument_id = instrument_id

        self.customer_id = customer_id
        self.customer_title = customer_title

        self.quantity = quantity
        self.price = price
        self.side = side
        self.cookie = cookie
        self.cookie2 = cookie2
        self.request_per_second = request_per_second
        self.limit = limit
        self.threads = threads

    def to_thread_order(self) -> ThreadOrderItem:
        return ThreadOrderItem(isin_code=self.isin_code, symbol=self.symbol, quantity=self.quantity, price=self.price, side=self.side,
                               cookie=self.cookie, cookie2=self.cookie2, instrument_id=self.instrument_id, customer_id=self.customer_id,
                               customer_title=self.customer_title, threads=self.threads)

    def to_async_order(self) -> AsyncOrderItem:
        return AsyncOrderItem(isin_code=self.isin_code, symbol=self.symbol, quantity=self.quantity, price=self.price, side=self.side,
                               cookie=self.cookie, cookie2=self.cookie2, instrument_id=self.instrument_id, customer_id=self.customer_id,
                               customer_title=self.customer_title, request_per_second=self.request_per_second, limit=self.limit)


class OrderListRequestData:
    def __init__(self, host: str, requests: List[OrderRequestItem], test: bool, order_type: str):
        super(OrderListRequestData, self).__init__()
        self.host = host
        self.requests = requests
        self.test = test
        self.order_type = order_type


class OrderProcessor:

    @abc.abstractmethod
    def get_default_host(self):
        raise NotImplementedError("Please Implement get_default_host method")

    @abc.abstractmethod
    def process_orders_async(self, host: str, async_orders: List[AsyncOrderItem], dt_start: datetime.datetime, dt_end: datetime.datetime):
        raise NotImplementedError("Please Implement process_orders_async method")

    @abc.abstractmethod
    def send_thread_orders(self, host: str, thread_orders: List[ThreadOrderItem], dt_start: datetime.datetime, dt_end: datetime.datetime):
        raise NotImplementedError("Please Implement send_thread_orders method")


def process_requests(
        processor: OrderProcessor,
        order_data: OrderListRequestData) -> str:
    orders_list = order_data.requests
    test = order_data.test
    order_type = order_data.order_type

    if orders_list is None or len(orders_list) == 0:
        return 'Null or empty order list'

    full_message = ''
    async_orders = []  # type: List[AsyncOrderItem]
    thread_orders = []  # type: List[ThreadOrderItem]
    for order_item in orders_list:
        if full_message != '':
            full_message += '\n'
        if order_item.side == 'buy':
            order_side = 0
        else:
            order_side = 1

        message = ''
        if order_side == 0:
            message += 'Buy '
        else:
            message += 'Sell '
        message += str(order_item.quantity) + ' units of ' + order_item.isin_code + ' for ' + str(order_item.price) + ' rials '
        if test is True:
            message += 'in test mode '
        else:
            message += 'in REAL mode '
        message += 'of type ' + order_type + ' '
        if order_type == OrderRequestItem.ORDER_TYPE_ASYNC:
            message += 'with req/sec: ' + str(order_item.request_per_second) + ', and limit: ' + str(order_item.limit)
        if order_type == OrderRequestItem.ORDER_TYPE_ASYNC:
            async_orders.append(order_item.to_async_order())
        else:
            thread_orders.append(order_item.to_thread_order())
        full_message += message

    if test:
        dt_start = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) + datetime.timedelta(seconds=5)
        dt_end = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")) + datetime.timedelta(seconds=5 + 5)
    else:
        dt_start = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")).replace(hour=8, minute=29, second=50, microsecond=0)
        dt_end = datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")).replace(hour=8, minute=30, second=5, microsecond=0)

    if len(async_orders) > 0:
        threading.Thread(target=processor.process_orders_async, args=(order_data.host if (order_data.host is not None and order_data.host != '') else processor.get_default_host(),
                                                                      async_orders, dt_start, dt_end)).start()
    elif len(thread_orders) > 0:
        processor.send_thread_orders(host=order_data.host if (order_data.host is not None and order_data.host != '') else processor.get_default_host(), thread_orders=thread_orders, dt_start=dt_start, dt_end=dt_end)
    log_debug(full_message)
    return full_message


def parse_string(x: Any) -> (bool, Optional[str], str):
    if x is None:
        return False, None, 'Null value'
    try:
        return True, str(x), 'OK'
    except:
        return False, None, 'Invalid type '+str(type(x))


def parse_int(x: Any) -> (bool, Optional[int], str):
    if x is None:
        return False, None, 'Null value'
    try:
        return True, int(float(x)), 'OK'
    except:
        return False, None, 'Invalid type '+str(type(x))


def parse_float(x: Any) -> (bool, Optional[float], str):
    if x is None:
        return False, None, 'Null value'
    try:
        return True, float(x), 'OK'
    except:
        return False, None, 'Invalid type '+str(type(x))
