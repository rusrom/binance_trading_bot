from datetime import datetime
import logging
import os
import time

import config
import sqlite_db
import log_message
from api import Binance
from tools import *


# Папка с ботом
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Подключаем логирование
LOG_DIR = 'logs'
LOG_FILE = 'binance-bot.log'

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(os.path.join(BOT_DIR, LOG_DIR, LOG_FILE), encoding='utf-8'),
        logging.StreamHandler()
    ])

# Инициализация базы данных
sqlite_db.check()

# Инициализация API Binance
bot = Binance(config.API_KEY, config.API_SECRET)

# Получаем ограничения торгов по всем парам с биржи
# local_time = int(time.time())
# limits = bot.exchangeInfo()
# TODO: [IMPROVE] Время можно получить используя: GET /api/v1/time при замене BINANCE_LIMITS записью в конфиге а н ев запросе
# server_time = int(limits['serverTime'])//1000
# TODO: [DELETE] Стерть тестовый словарь limits. Он был сделан для тестов что бы не дергать API Binance

# limits = {
#     'exchangeFilters': [],
#     'rateLimits': [
#         {
#             'interval': 'MINUTE',
#             'limit': 1200,
#             'rateLimitType': 'REQUESTS'
#         },
#         {
#             'interval': 'SECOND',
#             'limit': 10,
#             'rateLimitType': 'ORDERS'
#         },
#         {
#             'interval': 'DAY',
#             'limit': 100000,
#             'rateLimitType': 'ORDERS'
#         }
#     ],
#     'serverTime': 1528206478330,
#     'symbols': [
#         {
#             'baseAsset': 'LTC',
#             'baseAssetPrecision': 8,
#             'filters': [
#                 {
#                     'filterType': 'PRICE_FILTER',
#                     'maxPrice': '10000000.00000000',
#                     'minPrice': '0.01000000',
#                     'tickSize': '0.01000000'
#                 },
#                 {
#                     'filterType': 'LOT_SIZE',
#                     'maxQty': '10000000.00000000',
#                     'minQty': '0.00001000',
#                     'stepSize': '0.00001000'
#                 },
#                 {
#                     'filterType': 'MIN_NOTIONAL',
#                     'minNotional': '10.00000000'
#                 }
#             ],
#             'icebergAllowed': False,
#             'orderTypes': [
#                 'LIMIT',
#                 'LIMIT_MAKER',
#                 'MARKET',
#                 'STOP_LOSS_LIMIT',
#                 'TAKE_PROFIT_LIMIT'
#             ],
#             'quoteAsset': 'USDT',
#             'quotePrecision': 8,
#             'status': 'TRADING',
#             'symbol': 'LTCUSDT'}
#     ],
#     'timezone': 'UTC'
# }

# Инициализация местного времени и времени сервера биржи Binance
# shift_seconds = server_time-local_time
# bot.set_shift_seconds(shift_seconds)

# logging.debug(log_message.time_shift.format(
#     local_time_d=datetime.fromtimestamp(local_time), local_time_u=local_time,
#     server_time_d=datetime.fromtimestamp(server_time), server_time_u=server_time,
#     diff=abs(local_time-server_time), warn="ТЕКУЩЕЕ ВРЕМЯ ВЫШЕ" if local_time > server_time else 'ТЕКУЩЕЕ ВРЕМЯ МЕНЬШЕ',
#     fake_time_d=datetime.fromtimestamp(local_time+shift_seconds), fake_time_u=local_time+shift_seconds
# ))

# Комиссии биржи
fees = config.FEES

# Получение настроек пары: pair_name, и ее настроек: pair_settings на каждой итерации
pair_name = config.trading_pairs['pair']
pair_settings = config.trading_pairs

# Получаем лимиты биржи по текущей паре limits = bot.exchangeInfo()
# TODO: Ограничения можно прописать напимер в конфиге, что бы не дергать лишний раз биржу!
BINANCE_LIMITS = {
    'baseAsset': 'LTC',
    'baseAssetPrecision': 8,
    'filters': [
        {
            'filterType': 'PRICE_FILTER',
            'maxPrice': '10000000.00000000',
            'minPrice': '0.01000000',
            'tickSize': '0.01000000'
        },
        {
            'filterType': 'LOT_SIZE',
            'maxQty': '10000000.00000000',
            'minQty': '0.00001000',
            'stepSize': '0.00001000'
        },
        {
            'filterType': 'MIN_NOTIONAL',
            'minNotional': '10.00000000'
        }
    ],
    'icebergAllowed': False,
    'orderTypes': [
        'LIMIT',
        'LIMIT_MAKER',
        'MARKET',
        'STOP_LOSS_LIMIT',
        'TAKE_PROFIT_LIMIT'
    ],
    'quoteAsset': 'USDT',
    'quotePrecision': 8,
    'status': 'TRADING',
    'symbol': 'LTCUSDT'}

# Главный цикл программы
while True:

    # Получаем активный ордер из БД
    active_order = sqlite_db.get_active_order()
    print('Active order info', active_order)

    if active_order:

        # =======================
        # ПОСЛЕДНИЙ ОРДЕР В ЦИКЛЕ
        # =======================

        # -----------------------------------------------------
        # ФАЗА 1 - ОЖИДАНИЕ ЦЕНЫ С ОТСТУПОМ ДЛЯ ВХОДА В СДЕЛКУ
        # -----------------------------------------------------
        if not active_order['order_id']:

            logging.debug('Waiting for {wait} or cancel on {cancel}'.format(
                wait=active_order['wait_price'],
                cancel=active_order['wait_cancel']))

            # Цикл контроля ожидающего ордера
            while True:

                # Получаем лучшие цены
                best_price = bot.tickerBookTicker(symbol=pair_name)

                check_status = waiting_check(active_order, best_price)

                print('Current Bid: {} | Order start at: {} | Stop waiting at: {}'.format(
                    best_price['bidPrice'], active_order['wait_price'], active_order['wait_cancel']
                ))

                # Фаза ожидания цены входа в сделку или отмены ожидания
                if check_status == 'wait':
                    print(check_status)
                    time.sleep(2)
                    # Сдедующая проверка через 2 сек
                    continue

                # ОТМЕНА ОЖИДАНИЯ Цена пошла не в сторону полученного сигнала
                if check_status == 'cancel':
                    logging.debug('CANCEL waiting {} ORDER'.format(active_order['signal']))

                    # Формирование отчета по отмене ожидающего ордера
                    waiting_order = sqlite_db.get_active_order()
                    waiting_order.update({'finished': time.time()})

                    # Запись в историю цикла который был отменен по ожиданию
                    sqlite_db.write_close_cycle_to_history(waiting_order)

                    # Очистка БД с активными ордерами
                    sqlite_db.clear_active_orders()

                    # Выход из цикла контроля ожидающего ордера
                    break

                # ВХОД В СДЕЛКУ ВЫСТАВЛЕНИЕМ ОТЛОЖЕННОГО ОРДЕРА ПО СИГНАЛУ
                if check_status == 'order':

                    logging.debug('Make {} ORDER | Ask Best Price: {}'.format(active_order['signal'], best_price['askPrice']))

                    # Рассчет всех необходимых параметров для ордера на продажу:
                    price, amount, notional, spread = calculate_first_order(
                        active_order['signal'], best_price, pair_settings,
                        BINANCE_LIMITS)

                    # Вывод информации о рассчитанных параметрах
                    logging.debug(
                        'Best Bid: {best_bid} {quote} | Best Ask: {best_ask} {quote} | Spread: {spread}%'.format(
                            quote=pair_settings['quote'],
                            best_bid=float(best_price['bidPrice']),
                            best_ask=float(best_price['askPrice']),
                            spread=spread))
                    logging.debug(
                        'Ask price: {ask_price} {ticker_quote} | Sell amount: {sell_amount} {ticker_base} | '
                        'Notional: {notional} {ticker_quote}'.format(
                            ask_price=price, ticker_quote=pair_settings['quote'], sell_amount=amount,
                            ticker_base=pair_settings['base'], notional=notional))

                    # Проверяем minNotional
                    if notional < float(BINANCE_LIMITS['filters'][2]['minNotional']):
                        logging.debug(
                            '[ERROR] NOT ENOUGH NOTIONAL | Binance minNotional: {minNotional} {ticker_quote} | '
                            'Sell order notional: {notional} {ticker_quote}'.format(
                                ticker_quote=pair_settings['quote'],
                                minNotional=BINANCE_LIMITS['filters'][2]['minNotional'],
                                notional=notional))

                        raise NotImplementedError('[ERROR] NOT ENOUGH FIRST ORDER NOTIONAL')

                    # ------------------------------
                    # Выставление лимитного ордера
                    # ------------------------------
                    logging.debug('Sending LIMIT {} ORDER...'.format(active_order['signal']))

                    first_order = bot.createOrder(
                        symbol=active_order['pair'],
                        side=active_order['signal'],
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=amount,
                        price=price
                    )

                    # Если ордер удалось поставить
                    if first_order.get('orderId'):
                        logging.debug('{} ORDER {} successfully placed.'.format(
                            active_order['signal'], first_order['orderId']))
                        logging.debug('Updating DB with LIMIT {} ORDER data...'.format(
                            active_order['signal']))

                        # ЗАПИСЬ В БД инфо об ордере
                        sqlite_db.update_active_order(
                            first_order['type'],
                            best_price['bidPrice'],
                            best_price['askPrice'],
                            spread,
                            first_order['transactTime'] / 1000,
                            price,
                            first_order['orderId'],
                            first_order['transactTime'] / 1000,
                            amount,
                            price,
                            notional,
                            first_order['status']
                        )
                        # Выход из цикла контроля ожидающего первого ордера
                        break
                    else:
                        raise NotImplementedError('Cant send first limit order', first_order)

        # ---------------------------------------------
        # ФАЗА 2 - КОНТРОЛЬ НАПОЛНЕНИЯ ПЕРВОГО ОРДЕРА
        # ---------------------------------------------
        if active_order['order_id'] and not active_order['filled']:

            # КОНТРОЛЬ НАПОЛНЕНИЯ ПЕРВОГО ОРДЕРА
            while not active_order['filled']:
                # Информация по ордеру
                order_info = bot.orderInfo(orderId=active_order['order_id'], symbol=active_order['pair'])

                # TODO: [DELETE] УДАЛИТЬ resp РАСКОММЕНТИРОВАТЬ resp
                # order_info = {
                #     'symbol': 'LTCUSDT',
                #     'orderId': 32538143,
                #     'clientOrderId': 'CaoFcK1umTRFGiCEXJobJY',
                #     'price': '97.75000000',
                #     'origQty': '0.11253000',
                #     'executedQty': '0.11253000',
                #     'status': 'FILLED',
                #     'timeInForce': 'GTC',
                #     'type': 'LIMIT',
                #     'side': 'SELL',
                #     'stopPrice': '0.00000000',
                #     'icebergQty': '0.00000000',
                #     'time': 1529522451539,
                #     'isWorking': True
                # }

                # Ордер не исполнен
                if order_info['status'] == 'NEW':
                    # ---------------------------------------------------
                    # Отмена ордера если цена пошла не в сторону сигнала
                    # ---------------------------------------------------

                    # Лучшие цены BestPrice
                    best_price = bot.tickerBookTicker(symbol=pair_name)

                    # Сравнение цены ордера с ценами стакана BestPrice
                    if price_isnt_best_price(active_order, best_price):

                        # Отмена активного ордера так как цена хуже BestPrice
                        cancel_order = bot.cancelOrder(
                            orderId=active_order['order_id'],
                            symbol=active_order['pair'],
                        )

                        # Проверка отмены ордера
                        if check_order_send(cancel_order):
                            logging.debug('Waiting order was canceled because of BestPrice')

                            logging.debug('Re-calculate {} ORDER | Ask Best Price: {}'.format(
                                active_order['signal'], best_price['askPrice']))

                            # Рассчет всех необходимых параметров для ордера на продажу:
                            price, amount, notional, spread = calculate_first_order(
                                active_order['signal'], best_price, pair_settings, BINANCE_LIMITS)

                            # Вывод информации о рассчитанных параметрах
                            if active_order['signal'] == 'SELL':
                                logging.debug(
                                    'Ask price: {ask_price} {ticker_quote} | Sell amount: {sell_amount} {ticker_base} '
                                    '| Notional: {notional} {ticker_quote}'.format(
                                        ask_price=price, ticker_quote=pair_settings['quote'], sell_amount=amount,
                                        ticker_base=pair_settings['base'], notional=notional))

                            # Проверяем minNotional
                            if notional < float(BINANCE_LIMITS['filters'][2]['minNotional']):
                                raise NotImplementedError(
                                    'NOT ENOUGH FIRST ORDER RE-SEND NOTIONAL | Binance minNotional: {minNotional} '
                                    '{ticker_quote} | Sell order notional: {notional} {ticker_quote}'.format(
                                        ticker_quote=pair_settings['quote'],
                                        minNotional=BINANCE_LIMITS['filters'][2]['minNotional'],
                                        notional=notional))

                            # ------------------------------
                            # Выставление лимитного ордера
                            # ------------------------------
                            logging.debug('Re-sending LIMIT {} ORDER...'.format(active_order['signal']))

                            re_order = bot.createOrder(
                                symbol=active_order['pair'],
                                side=active_order['signal'],
                                type='LIMIT',
                                timeInForce='GTC',
                                quantity=amount,
                                price=price
                            )

                            # Если ордер удалось поставить
                            if re_order.get('orderId'):
                                logging.debug('LIMIT {} ORDER {} was successfully re-placed.'.format(
                                    active_order['signal'], re_order['orderId']))

                                # ЗАПИСЬ В БД инфо об измененном ордере
                                sqlite_db.update_active_re_order(
                                    re_order['orderId'],
                                    re_order['transactTime'] / 1000,
                                    amount,
                                    price,
                                    notional,
                                    re_order['status']
                                )

                                # Обновляем информацию active_order так как поменялся order_id
                                active_order = sqlite_db.get_active_order()

                            else:
                                # Ошибка в выставлении ордера
                                raise NotImplementedError('Cant re-send first order', re_order)

                        else:
                            # Ошибка отмены ордера
                            raise NotImplementedError('First order cancel error', cancel_order)

                    # --------------------------------------------------------------------
                    # Цена выставленого ордера лучшая в стакане BestPrice
                    # --------------------------------------------------------------------
                    else:
                        logging.debug('Order: {} | Status: {}'.format(order_info['orderId'], order_info['status']))

                # Ордер исполнен частично
                if order_info['status'] == 'PARTIALLY_FILLED':
                    logging.debug('Order: {} was {} with {}'.format(
                        order_info['orderId'], order_info['status'], order_info['executedQty']))

                # Ордер исполнен
                if order_info['status'] == 'FILLED':
                    logging.debug('Order: {} was {}'.format(order_info['orderId'], order_info['status']))

                    # Запись в БД времени исполнения ордера
                    sqlite_db.update_active_order_filled(order_info['status'], order_info['time']/1000)

                    # TODO: [TEST] Протестировать как сработает без обновления active_order при FILLED
                    # Получаем обновленную информацию об активном ордере из БД
                    # active_order = sqlite_db.get_active_order()

                    # ВЫХОД ИЗ ФАЗЫ 2
                    break

                # Время между запросами на проверку информации по ордеру
                time.sleep(2)

            # [КОНЕЦ ФАЗЫ 2] Переход к началу главного цикла программы и обновление информации active_order
            continue

        # ---------------------------------------------------------------------------
        # ФАЗА 3 - РАССЧЕТ И ВЫСТАВЛЕНИЕ ЗАКРЫВАЮЩИХ TAKE PROFIT и STOP LOSS ОРДЕРОВ
        # ---------------------------------------------------------------------------
        if active_order['filled'] and not active_order['tp_price']:

            logging.debug(
                '[FILLED] ACTIVE {signal} ORDER: {order} | Amount: {amount} {ticker_base} | '
                'Price: {price} {ticker_quote} | Notional: {notional} {ticker_quote}'.format(
                    ticker_base=pair_settings['base'], ticker_quote=pair_settings['quote'],
                    signal=active_order['signal'], order=active_order['order_id'],
                    price=active_order['price'], amount=active_order['amount'], notional=active_order['notional']))

            # Начинаем рассчёт TAKE PROFIT и STOP LOSS ордеров
            logging.debug('Calculating closing TP & SL orders...')

            # Рассчет параметров для 2-х закрывающих ордеров: STOP LOSS и TAKE PROFIT
            actual_amount, tp_amount, tp_price, sl_amount, sl_price = calculate_close_order(
                active_order, fees, BINANCE_LIMITS, pair_settings)

            if active_order['signal'] == 'SELL':
                logging.debug(
                    'Actual amount {actual_amount} {ticker_quote} | '
                    'TP amount: {tp_amount} {ticker_base} | TP price: {tp_price} {ticker_quote} | '
                    'SL amount: {sl_amount} {ticker_base} | SL price {sl_price} {ticker_quote}'.format(
                        tp_amount=tp_amount, tp_price=tp_price,
                        sl_amount=sl_amount, sl_price=sl_price,
                        actual_amount=actual_amount,
                        ticker_base=pair_settings['base'], ticker_quote=pair_settings['quote']
                    ))

            # --------------------------------------------------
            # Вывставление LIMIT TAKE PROFIT TP и STOP LIMIT SL
            # --------------------------------------------------

            # Определение стороны закрывающего ордера
            closing_order_side = 'BUY' if active_order['signal'] == 'SELL' else 'SELL'

            # Выставление лимитного TAKE PROFIT ордера

            logging.debug('Sending TAKE PROFIT LIMIT {} ORDER...'.format(closing_order_side))

            # tp_order = {
            #     'clientOrderId': 'PKduu4cK55suk0j0DXMKWA',
            #     'executedQty': '0.00000000',
            #     'orderId': 77777777,
            #     'origQty': '0.15000000',
            #     'price': '96.23000000',
            #     'side': 'SELL',
            #     'status': 'NEW',
            #     'stopPrice': '96.23000000',
            #     'symbol': 'LTCUSDT',
            #     'timeInForce': 'GTC',
            #     'transactTime': 1529478148911,
            #     'type': 'STOP_LOSS_LIMIT'
            # }
            tp_order = bot.createOrder(
                symbol=active_order['pair'],
                side=closing_order_side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=tp_amount,
                price=tp_price
            )

            logging.debug('Sending STOP LOSS LIMIT {} ORDER...'.format(closing_order_side))

            # sl_order = {
            #     'clientOrderId': 'PKduu4cK55suk0j0DXMKWA',
            #     'executedQty': '0.00000000',
            #     'orderId': 55555555,
            #     'origQty': '0.15000000',
            #     'price': '96.23000000',
            #     'side': 'SELL',
            #     'status': 'NEW',
            #     'stopPrice': '96.23000000',
            #     'symbol': 'LTCUSDT',
            #     'timeInForce': 'GTC',
            #     'transactTime': 1529478148911,
            #     'type': 'STOP_LOSS_LIMIT'
            # }
            sl_order = bot.createOrder(
                symbol=active_order['pair'],
                side=closing_order_side,
                type='STOP_LOSS_LIMIT',
                timeInForce='GTC',
                quantity=sl_amount,
                stopPrice=sl_price,
                price=sl_price
            )

            # Если ордера удалось поставить
            if tp_order.get('orderId') and sl_order.get('orderId'):
                logging.debug('2 CLOSING {} Orders successfully placed.'.format(active_order['signal']))

                # ЗАПИСЬ В БД инфо о 2-х закрывающих ордерах
                sqlite_db.update_active_order_tp_sl(
                    actual_amount, tp_order['orderId'], tp_price, tp_amount, sl_order['orderId'], sl_price, sl_amount
                )
            else:
                # Ошибка в выставлении закрывающих ордеров
                raise NotImplementedError('Cant send one or both closing order(s)', tp_order, sl_order)

            # [КОНЕЦ ФАЗЫ 3] Переход к началу главного цикла программы и обновление информации active_order
            continue

        # ----------------------------------------------------------------
        # ФАЗА 4 - КОНТРОЛЬ ЗАКРЫВАЮЩЕГО ОРДЕРА TAKE PROFIT или STOP LOSS
        # ----------------------------------------------------------------
        if active_order['tp_price'] and active_order['sl_price']:

            logging.debug('Waiting for TP or SL...')

            # Контроль закрывающих TP и SL ордеров
            while True:

                # Все открытые ордера по паре
                closing_orders = bot.openOrders(symbol=active_order['pair'])

                # Если пришол ответ с ошибкой
                if closing_orders.get('code'):
                    raise NotImplementedError('Problem with getting info about open orders', closing_orders)

                # Сколько открытых ордеров
                if len(closing_orders) == 2:
                    logging.debug('2 closing orders are active')
                    # Проверка закрывающих ордеров с интервалом в 5 сек
                    time.sleep(5)
                else:
                    # Какой ордер сработал TP или SL
                    closing_result = 'TP' if closing_orders[0]['type'] == 'STOP_LOSS_LIMIT' else 'SL'

                    # Отмена оставшегося ордера
                    cancel_order = bot.cancelOrder(
                        orderId=closing_orders[0]['orderId'],
                        symbol=closing_orders[0]['symbol']
                    )

                    # Проверка на успешную отмену оставшегося ордера
                    if cancel_order.get('code'):
                        raise NotImplementedError('Problem with cancel remaining closing order', cancel_order)

                    # Формирование полного отчета по закрытому циклу
                    closed_cycle = sqlite_db.get_active_order()
                    closed_cycle.update({'close': closing_result, 'finished': time.time()})

                    # Запись в историю завершенного цикла
                    sqlite_db.write_close_cycle_to_history(closed_cycle)

                    # Очистка БД с активными ордерами
                    sqlite_db.clear_active_orders()

                    # TODO: [STOP APP] Выход из программы после успешного прохода полного цикла
                    raise NotImplementedError('[SUCCESS] Program worked! Full cycle ended! Congratulations!')


        # Уходим в начало цикла while который проверяем active orders
        continue

    else:

        # =====================
        # ПЕРВЫЙ ОРДЕР В ЦИКЛЕ
        # =====================

        logging.debug('!!!!! NO ACTIVE ORDERS !!!!!')
        logging.debug("***** Start working with {pair} *****".format(pair=pair_name))

        # TODO: Сделать модуль который выдает сигналы
        signal = 'SELL'
        logging.debug('Signal: {signal}'.format(signal=signal))

        # ---------------------------
        # ЕСЛИ СИГНАЛ ПОКУПКА / BUY
        # ---------------------------

        if signal == 'BUY':

            # Мы в ветке НАЧАЛА ЦИКЛА: УСТАНОВКА ПЕРВВОГО ОРДЕРА НА ПОКУПКУ LTC
            logging.debug('Start calculating order for buying {} ...'.format(pair_settings['base']))

            # Получаем лучшую цену в стакане - первая цена Bid
            # TODO: Раскомментировать строку ниже что бы получать данные с биржи
            best_price = bot.tickerBookTicker(symbol=pair_name)

            # Рассчет всех необходимых параметров для ордера на покупку:
            bid_price, buy_amount, notional, cancel_price, spread = calculate_first_order(
                signal, best_price, pair_settings,
                BINANCE_LIMITS, config.OFFSET_ORDER, config.OFFSET_CANCEL)

            # Вывод информации о рассчитанных параметрах
            logging.debug('Order book best Bid price: {best_price} {ticker}'.format(
                best_price=best_price, ticker=pair_settings['quote']))
            logging.debug(
                'Bid price: {bid_price} {ticker_quote} | Buy amount: {buy_amount} {ticker_base} | '
                'Notional: {notional} {ticker_quote} | Cancel price: {cancel_price} {ticker_quote}'.format(
                    bid_price=bid_price, ticker_quote=pair_settings['quote'], buy_amount=buy_amount,
                    ticker_base=pair_settings['base'], notional=notional, cancel_price=cancel_price))

            # Проверяем minNotional
            if notional < float(BINANCE_LIMITS['filters'][2]['minNotional']):
                logging.debug(
                    '[ERROR] NOT ENOUGH NOTIONAL | Binance minNotional: {minNotional} {ticker_quote} | '
                    'Buy order notional: {notional} {ticker_quote}'.format(
                        ticker_quote=pair_settings['quote'],
                        minNotional=BINANCE_LIMITS['filters'][2]['minNotional'],
                        notional=notional))
                break

            # НАЧИНАЕМ ВЫСТАВЛЯТЬ СТОП БАЙ ОРДЕР
            logging.debug('Start making BUY STOP LIMIT ORDER ...')

        # ---------------------------
        # ЕСЛИ СИГНАЛ ПРОДАЖА / SELL
        # ---------------------------

        if signal == 'SELL':

            # Мы в ветке НАЧАЛА ЦИКЛА: УСТАНОВКА ПЕРВВОГО ОРДЕРА НА ПРОДАЖУ LTC
            logging.debug('Start calculating waiting prices for selling {} ...'.format(pair_settings['base']))

            # Получаем лучшую цену в стакане - первая цена Bid
            best_price = bot.tickerBookTicker(symbol=pair_name)

            # ================================================== #
            # NEW WAVE )
            # ================================================== #

            # Рассчетная Bid Best Price
            logging.debug('Bid best price: {} {}'.format(best_price['bidPrice'].rstrip('0'), pair_settings['quote']))

            # Цена Bid при которой произойдет выставление ордера на продажу по Best Price Ask на тот момент
            wait_price_sell = subtract_percent_from_price(float(best_price['bidPrice']), config.OFFSET_ORDER)
            wait_price_sell = float(adjust_to_step(wait_price_sell, BINANCE_LIMITS['filters'][0]['tickSize']))

            # Цена Bid при которой произойдет отмена слежения
            wait_cancel = add_percent_to_price(float(best_price['bidPrice']), config.OFFSET_CANCEL)
            wait_cancel = float(adjust_to_step(wait_cancel, BINANCE_LIMITS['filters'][0]['tickSize']))

            # Запись в ДБ цен ожидания
            sqlite_db.write_waiting_data(signal, pair_settings['pair'], wait_price_sell, wait_cancel)

            # Переход в завершающий цикл
            continue

# ===================================================================================================================================================
# ===================================================================================================================================================
# ===================================================================================================================================================

#         # Рассчет всех необходимых параметров для ордера на продажу:
#         ask_price, sell_amount, notional, cancel_price, spread = calculate_first_order(
#             signal, best_price, pair_settings,
#             BINANCE_LIMITS, config.OFFSET_ORDER, config.OFFSET_CANCEL)
#
#         # Вывод информации о рассчитанных параметрах
#         logging.debug('Best Bid: {best_bid} {quote} | Best Ask: {best_ask} {quote} | Spread: {spread}%'.format(
#             quote=pair_settings['quote'],
#             best_bid=float(best_price['bidPrice']),
#             best_ask=float(best_price['askPrice']),
#             spread=spread))
#         logging.debug(
#             'Ask price: {ask_price} {ticker_quote} | Sell amount: {sell_amount} {ticker_base} | '
#             'Notional: {notional} {ticker_quote} | Cancel price: {cancel_price} {ticker_quote}'.format(
#                 ask_price=ask_price, ticker_quote=pair_settings['quote'], sell_amount=sell_amount,
#                 ticker_base=pair_settings['base'], notional=notional, cancel_price=cancel_price))
#
#         # Проверяем minNotional
#         if notional < float(BINANCE_LIMITS['filters'][2]['minNotional']):
#             logging.debug(
#                 '[ERROR] NOT ENOUGH NOTIONAL | Binance minNotional: {minNotional} {ticker_quote} | '
#                 'Sell order notional: {notional} {ticker_quote}'.format(
#                     ticker_quote=pair_settings['quote'],
#                     minNotional=BINANCE_LIMITS['filters'][2]['minNotional'],
#                     notional=notional))
#             break
#
#
#         # НАЧИНАЕМ ВЫСТАВЛЯТЬ СТОП СЕЛ ОРДЕР
#         logging.debug('Making first sell order in cycle ...')
#
#         # Виртуальный ордер
#         new_order = {
#             'clientOrderId': 'gnQjFiVBrZdZQ8OxGfkidX',
#             'executedQty': '0.00000000',
#             'orderId': 30666254,
#             'origQty': float(sell_amount),
#             'price': float(ask_price),
#             'side': signal,
#             'status': 'NEW',
#             'stopPrice': ask_price,
#             'symbol': pair_name,
#             'timeInForce': 'GTC',
#             'transactTime': time.time() * 1000,
#             'type': 'STOP_LOSS_LIMIT'
#         }
#
#         # Отправляем команду на бирже о создании ордера на покупку с рассчитанными параметрами
#         # new_order = bot.createOrder(
#         #     symbol=pair_name,         # STRING
#         #     side='SELL',              # ENUM
#         #     type='STOP_LOSS_LIMIT',   # ENUM
#         #     timeInForce='GTC',        # ENUM
#         #     quantity=sell_amount,     # DECIMAL
#         #     stopPrice=ask_price,      # DECIMAL
#         #     price=ask_price           # DECIMAL
#         # )
#         #
#         # print(new_order)
#
#         # }
#         # response = {
#         #  'clientOrderId': 'gnQjFiVBrZdZQ8OxGfkidX',
#         #  'executedQty': '0.00000000',
#         #  'orderId': 30666254,
#         #  'origQty': '0.10000000',
#         #  'price': '119.98000000',
#         #  'side': 'SELL',
#         #  'status': 'NEW',
#         #  'stopPrice': '120.00000000',
#         #  'symbol': 'LTCUSDT',
#         #  'timeInForce': 'GTC',
#         #  'transactTime': 1528228801690,
#         #  'type': 'STOP_LOSS_LIMIT'
#         # }
#
#         # Проверка выставления ордера
#         if check_order_send(new_order):
#             # Запись в в БД информации об ордере
#             sqlite_db.db_write_first_order(new_order, notional, cancel_price, best_price, spread)
#             logging.debug(str(new_order))
#
#             # Переход в режим контроля активного ордера
#             # TODO: Раскомментировать переход в фазу контроля
#             # continue
#         else:
#             # Ошибка выставления ордера
#             logging.warning(order_send_error('Order send error'))
#
#
#     # TODO: ВАЖНО! break который ниже НУЖНО УДАЛИТЬ! ОН ДЛЯ ПРОВЕРОЧНЫХ ЦЕЛЕЙ И ВЫХОДИТЬ ИЗ БЕСКОНЕЧНОГО ЦЫКЛА!!
#     break
#
# logging.debug('Bot was stopped!')

































