from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
import json
import pytz
import datetime
from frizzy.utils import parse_float, parse_int, parse_string, OrderRequestItem, OrderListRequestData, OrderProcessor, process_requests
from frizzy.easy_trader import EasyTraderOrderProcessor
from frizzy.online_plus import OnlinePlusOrderProcessor
from frizzy.agah_online import AgahOnlineOrderProcessor
from frizzy.farabixo import FarabixoProcessor
from socket import gethostname
from django.views.decorators.csrf import csrf_exempt
from typing import List, Tuple, Optional

# Create your views here.


def get_health(request):
    return HttpResponse('Alive')


def get_host_name(request):
    return HttpResponse(gethostname())


def get_server_time(request):
    return HttpResponse(datetime.datetime.now(tz=pytz.timezone("Asia/Tehran")).strftime('%Y-%m-%d %H:%M:%S %Z'))


def get_request_orders(json_data) -> Tuple[Optional[OrderListRequestData], Optional[HttpResponseBadRequest]]:
    orders = json_data.get('o', None)
    test = json_data.get('t', None)
    order_type = json_data.get('ot', None)
    host = json_data.get('h', None)

    if test is None:
        test = False
    else:
        if not isinstance(test, bool):
            return None, HttpResponseBadRequest('Invalid test: ' + str(test) + ', must be bool')

    if order_type is None or order_type == '':
        return None, HttpResponseBadRequest('Null or emtpy order type, must be ' + OrderRequestItem.ORDER_TYPE_ASYNC + ' or ' + OrderRequestItem.ORDER_TYPE_THREADED)
    else:
        order_type = str(order_type)
        if order_type != OrderRequestItem.ORDER_TYPE_ASYNC and order_type != OrderRequestItem.ORDER_TYPE_THREADED:
            return None, HttpResponseBadRequest('Invalid order type, must be ' + OrderRequestItem.ORDER_TYPE_ASYNC + ' or ' + OrderRequestItem.ORDER_TYPE_THREADED)

    if orders is None:
        return None, HttpResponseBadRequest('Invalid request, no orders list in json body')
    elif not isinstance(orders, list):
        return None, HttpResponseBadRequest('Invalid request, invalid type for orders ' + str(type(orders)) + ', must be list')
    request_orders = []  # type: List[OrderRequestItem]
    for order_item in orders:
        isin_code = order_item.get('i', None)
        symbol = order_item.get('sm', None)
        quantity = order_item.get('q', None)
        price = order_item.get('p', None)
        side = order_item.get('s', None)
        cookie = order_item.get('c', None)
        cookie2 = order_item.get('c2', None)
        limit = order_item.get('l', None)
        rps = order_item.get('r', None)
        threads = order_item.get('t', None)

        instrument_id = order_item.get('ii', None)
        customer_id = order_item.get('ci', None)
        customer_title = order_item.get('ct', None)

        isin_ok, isin_code, isin_error_message = parse_string(isin_code)
        if isin_ok is False:
            return None, HttpResponseBadRequest('Invalid isin code: ' + isin_error_message)

        symbol_ok, symbol, symbol_error_message = parse_string(symbol)
        if symbol_ok is False:
            return None, HttpResponseBadRequest('Invalid symbol: ' + symbol_error_message)

        quantity_ok, quantity, quantity_error_message = parse_int(quantity)
        if quantity_ok is False:
            return None, HttpResponseBadRequest('Invalid quantity: ' + quantity_error_message)

        price_ok, price, price_error_message = parse_int(price)
        if price_ok is False:
            return None, HttpResponseBadRequest('Invalid price: ' + price_error_message)

        side_ok, side, side_error_message = parse_string(side)
        if side_ok is False:
            return None, HttpResponseBadRequest('Invalid side: ' + side_error_message)
        if side != 'buy' and side != 'sell':
            return None, HttpResponseBadRequest('Invalid side, only buy and sell values are accepted')

        cookie_ok, cookie, cookie_error_message = parse_string(cookie)
        if cookie_ok is False:
            return None, HttpResponseBadRequest('Invalid cookie: ' + cookie_error_message)

        if cookie2 is not None:
            cookie2_ok, cookie2, cookie2_error_message = parse_string(cookie2)
            if cookie2_ok is False:
                return None, HttpResponseBadRequest('Invalid cookie2: ' + cookie2_error_message)

        if limit is None:
            limit = 10000
        else:
            limit_ok, limit, limit_error_message = parse_int(limit)
            if limit_ok is False:
                return None, HttpResponseBadRequest('Invalid limit: ' + limit_error_message)

        if rps is None:
            rps = 100
        else:
            rps_ok, rps, rps_error_message = parse_int(rps)
            if rps_ok is False:
                return None, HttpResponseBadRequest('Invalid request per second: ' + rps_error_message)

        if threads is None:
            threads = 30
        else:
            threads_ok, threads, threads_error_message = parse_int(threads)
            if threads_ok is False:
                return None, HttpResponseBadRequest('Invalid threads: ' + threads_error_message)

        if instrument_id is not None:
            instrument_id_ok, instrument_id, instrument_id_error_message = parse_int(instrument_id)
            if instrument_id_ok is False:
                return None, HttpResponseBadRequest('Invalid instrument_id: ' + instrument_id_error_message)

        if customer_id is not None:
            customer_id_ok, customer_id, customer_id_error_message = parse_int(customer_id)
            if customer_id_ok is False:
                return None, HttpResponseBadRequest('Invalid customer_id: ' + customer_id_error_message)

        if customer_title is not None:
            customer_title_ok, customer_title, customer_title_error_message = parse_string(customer_title)
            if customer_title_ok is False:
                return None, HttpResponseBadRequest('Invalid customer_title: ' + customer_title_error_message)

        request_orders.append(OrderRequestItem(isin_code=isin_code, symbol=symbol, quantity=quantity, price=price, side=side, cookie=cookie, cookie2=cookie2,
                                               request_per_second=rps, limit=limit, threads=threads,
                                               instrument_id=instrument_id, customer_id=customer_id, customer_title=customer_title))
    return OrderListRequestData(host, request_orders, test, order_type), None


@csrf_exempt
def send_easy_trader(request):
    return send_request(request=request, processor=EasyTraderOrderProcessor())


@csrf_exempt
def send_online_plus(request):
    return send_request(request=request, processor=OnlinePlusOrderProcessor())


@csrf_exempt
def send_agah_online(request):
    return send_request(request=request, processor=AgahOnlineOrderProcessor())


@csrf_exempt
def send_farabixo(request):
    return send_request(request=request, processor=FarabixoProcessor())


def send_request(request, processor: OrderProcessor):
    if request.method == 'POST' and request.META['CONTENT_TYPE'] is not None and 'application/json' in request.META['CONTENT_TYPE']:
        print(request.body)
        json_data = json.loads(request.body)

        response, http_error = get_request_orders(json_data)
        if http_error is not None:
            return http_error
        elif response is None:
            return HttpResponseBadRequest('Null orders')
        else:
            # request_orders = response.requests
            # test = response.test
            # order_type = response.order_type
            message = process_requests(
                processor=processor,
                order_data=response
            )
            return HttpResponse(message)

    else:
        print('NOT FOUND')
        print(request.method)
        print(request.META['CONTENT_TYPE'])
        return HttpResponseForbidden()