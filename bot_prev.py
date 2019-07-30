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
# TODO: Время можно получить используя: GET /api/v1/time при замене BINANCE_LIMITS записью в конфиге а н ев запросе
# server_time = int(limits['serverTime'])//1000
# TODO: Стеерть тестовый словарь limits. Он был сделан для тестов что бы не дергать API Binance
limits = {
    'exchangeFilters': [],
    'rateLimits': [
        {
            'interval': 'MINUTE',
            'limit': 1200,
            'rateLimitType': 'REQUESTS'
        },
        {
            'interval': 'SECOND',
            'limit': 10,
            'rateLimitType': 'ORDERS'
        },
        {
            'interval': 'DAY',
            'limit': 100000,
            'rateLimitType': 'ORDERS'
        }
    ],
    'serverTime': 1528206478330,
    'symbols': [
        {
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
    ],
    'timezone': 'UTC'
}

# Инициализация местного времени и времени сервера биржи Binance
# shift_seconds = server_time-local_time
# bot.set_shift_seconds(shift_seconds)

# logging.debug(log_message.time_shift.format(
#     local_time_d=datetime.fromtimestamp(local_time), local_time_u=local_time,
#     server_time_d=datetime.fromtimestamp(server_time), server_time_u=server_time,
#     diff=abs(local_time-server_time), warn="ТЕКУЩЕЕ ВРЕМЯ ВЫШЕ" if local_time > server_time else 'ТЕКУЩЕЕ ВРЕМЯ МЕНЬШЕ',
#     fake_time_d=datetime.fromtimestamp(local_time+shift_seconds), fake_time_u=local_time+shift_seconds
# ))


# Получение настроек пары: pair_name, и ее настроек: pair_settings на каждой итерации
pair_name = config.trading_pairs['pair']
pair_settings = config.trading_pairs


# Бесконечный цикл программы
while True:
    # Получаем активный ордер из БД
    logging.debug('Getting active order from DB ...')
    active_order = sqlite_db.get_active_order()

    # ------------------------
    # ПОСЛЕДНИЙ ОРДЕР В ЦИКЛЕ
    # ------------------------
    if active_order:
        # TODO Доделать ветку если есть активные ордера
        logging.debug('Active order: {order}'.format(order=[active_order['order_id'], active_order['pair']]))
        break
    else:
        logging.debug('!!!!! NO ACTIVE ORDERS !!!!!')

    # ----------------------
    # ПЕРВЫЙ ОРДЕР В ЦИКЛЕ
    # ----------------------

    # Получаем все балансы с биржи у которых балансы больше 0
    balances = {
        balance['asset']: float(balance['free'])
        for balance in bot.account()['balances']
        if float(balance['free']) > 0
    }
    # TODO: Раскоментировать balances выше удалить balances ниже
    # balances = {'LTC': 1.0114446, 'USDT': 20.335938, 'NEO': 34.43224554}

    logging.debug("***** Start working with {pair} *****".format(pair=pair_name))

    # TODO: Сделать модуль который выдает сигналы
    signal = 'SELL'
    logging.debug('Signal: {signal}'.format(signal=signal))

    # Получаем лимиты биржи по текущей паре
    # TODO: Ограничения можно прописать напимер в конфиге, что бы не дергать лишний раз биржу!
    for elem in limits['symbols']:
        if elem['symbol'] == pair_name:
            BINANCE_LIMITS = elem
            break
    else:
        raise Exception("Не удалось найти настройки выбранной пары " + pair_name)

    # Вывод в лог балансов по текущей паре
    logging.debug("Balances for {pair_name} {balance}".format(
        pair_name=pair_name, balance=pair_balances(balances, pair_settings)))

    # ---------------------------
    # ЕСЛИ СИГНАЛ ПОКУПКА / BUY
    # ---------------------------

    # Проверяем позволяет ли баланс торговать
    # Баланс должен быть выше лимитов биржи и выше указанной суммы в настройках
    # if signal == 'BUY' and enough_funds(signal, balances, pair_settings):
    # TODO: Раскомментировать условие выше и стереть условие ниже
    if signal == 'BUY':

        # Мы в ветке НАЧАЛА ЦИКЛА: УСТАНОВКА ПЕРВВОГО ОРДЕРА НА ПОКУПКУ LTC
        logging.debug('Start calculating order for buying {} ...'.format(pair_settings['base']))

        # Получаем лучшую цену в стакане - первая цена Bid
        # best_price = bot.tickerBookTicker(symbol=pair_name)['bidPrice']
        # TODO: Раскомментировать строку выше и стереть строку ниже
        # best_price = {
        #   'symbol': 'LTCUSDT',
        #   'bidPrice': '96.47000000', 'bidQty': '4.21764000',
        #   'askPrice': '96.61000000', 'askQty': '0.61605000'
        # }
        best_price = {
          'symbol': 'LTCUSDT',
          'bidPrice': '96.57000000', 'bidQty': '4.21764000',
          'askPrice': '96.61000000', 'askQty': '0.61605000'
        }

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

        # Проверяем хватает ли средств на балансе для покупки
        if not enough_funds(signal, balances, notional, pair_settings):
            logging.debug(
                '[ERROR] NOT ENOUGH {ticker_quote} FUNDS FOR BUY | Need: {amount} {ticker_quote} | '
                'Balance: {balances} {ticker_quote}'.format(
                    ticker_quote=pair_settings['quote'], amount=notional, balances=balances[pair_settings['quote']]))
            break

        # НАЧИНАЕМ ВЫСТАВЛЯТЬ СТОП БАЙ ОРДЕР
        logging.debug('Start making BUY STOP LIMIT ORDER ...')

    # ---------------------------
    # ЕСЛИ СИГНАЛ ПРОДАЖА / SELL
    # ---------------------------

    # Проверяем позволяет ли баланс торговать
    # Баланс должен быть выше лимитов биржи и выше указанной суммы в настройках
    # if signal == 'SELL' and enough_funds(signal, balances, pair_settings):
    if signal == 'SELL':

        # Мы в ветке НАЧАЛА ЦИКЛА: УСТАНОВКА ПЕРВВОГО ОРДЕРА НА ПРОДАЖУ LTC
        logging.debug('Start calculating order for selling {} ...'.format(pair_settings['base']))

        # Получаем лучшую цену в стакане - первая цена Bid
        best_price = bot.tickerBookTicker(symbol=pair_name)
        # TODO: Раскомментировать строку выше и стереть строку ниже
        # best_price = {
        #   'symbol': 'LTCUSDT',
        #   'bidPrice': '96.47000000', 'bidQty': '4.21764000',
        #   'askPrice': '96.61000000', 'askQty': '0.61605000'
        # }

        # Рассчет всех необходимых параметров для ордера на продажу:
        ask_price, sell_amount, notional, cancel_price, spread = calculate_first_order(
            signal, best_price, pair_settings,
            BINANCE_LIMITS, config.OFFSET_ORDER, config.OFFSET_CANCEL)

        # Вывод информации о рассчитанных параметрах
        logging.debug('Best Bid: {best_bid} {quote} | Best Ask: {best_ask} {quote} | Spread: {spread}%'.format(
            quote=pair_settings['quote'],
            best_bid=float(best_price['bidPrice']),
            best_ask=float(best_price['askPrice']),
            spread=spread))
        logging.debug(
            'Ask price: {ask_price} {ticker_quote} | Sell amount: {sell_amount} {ticker_base} | '
            'Notional: {notional} {ticker_quote} | Cancel price: {cancel_price} {ticker_quote}'.format(
                ask_price=ask_price, ticker_quote=pair_settings['quote'], sell_amount=sell_amount,
                ticker_base=pair_settings['base'], notional=notional, cancel_price=cancel_price))

        # Проверяем minNotional
        if notional < float(BINANCE_LIMITS['filters'][2]['minNotional']):
            logging.debug(
                '[ERROR] NOT ENOUGH NOTIONAL | Binance minNotional: {minNotional} {ticker_quote} | '
                'Sell order notional: {notional} {ticker_quote}'.format(
                    ticker_quote=pair_settings['quote'],
                    minNotional=BINANCE_LIMITS['filters'][2]['minNotional'],
                    notional=notional))
            break

        # Проверяем хватает ли средств на балансе для покупки
        if not enough_funds(signal, balances, sell_amount, pair_settings):
            logging.debug(
                '[ERROR] NOT ENOUGH {ticker_base} FUNDS FOR SALE | Need: {amount} {ticker_base} | '
                'Balance: {balances} {ticker_base}'.format(
                    ticker_base=pair_settings['base'], amount=sell_amount, balances=balances[pair_settings['base']]))
            break

        # НАЧИНАЕМ ВЫСТАВЛЯТЬ СТОП СЕЛ ОРДЕР
        logging.debug('Making first sell order in cycle ...')

        # Отправляем команду на бирже о создании ордера на покупку с рассчитанными параметрами
        new_order = bot.createOrder(
            symbol=pair_name,         # STRING
            side='SELL',              # ENUM
            type='STOP_LOSS_LIMIT',   # ENUM
            timeInForce='GTC',        # ENUM
            quantity=sell_amount,     # DECIMAL
            stopPrice=ask_price,      # DECIMAL
            price=ask_price           # DECIMAL
        )

        print(new_order)



        # new_order = {
        #     'clientOrderId': 'gnQjFiVBrZdZQ8OxGfkidX',
        #     'executedQty': '0.00000000',
        #     'orderId': 30666254,
        #     'origQty': float(sell_amount),
        #     'price': float(ask_price),
        #     'side': signal,
        #     'status': 'NEW',
        #     'stopPrice': ask_price,
        #     'symbol': pair_name,
        #     'timeInForce': 'GTC',
        #     'transactTime': time.time() * 1000,
        #     'type': 'STOP_LOSS_LIMIT'
        # }
        # response = {
        #  'clientOrderId': 'gnQjFiVBrZdZQ8OxGfkidX',
        #  'executedQty': '0.00000000',
        #  'orderId': 30666254,
        #  'origQty': '0.10000000',
        #  'price': '119.98000000',
        #  'side': 'SELL',
        #  'status': 'NEW',
        #  'stopPrice': '120.00000000',
        #  'symbol': 'LTCUSDT',
        #  'timeInForce': 'GTC',
        #  'transactTime': 1528228801690,
        #  'type': 'STOP_LOSS_LIMIT'
        # }

        # Проверка выставления ордера
        if check_order_send(new_order):
            # Запись в в БД информации об ордере
            sqlite_db.db_write_first_order(new_order, notional, cancel_price, best_price, spread)
            logging.debug(str(new_order))

            # Переход в режим контроля активного ордера
            # TODO: Раскомментировать переход в фазу контроля
            continue
        else:
            # Ошибка выставления ордера
            logging.warning(order_send_error('Order send error'))


    # TODO: ВАЖНО! break который ниже НУЖНО УДАЛИТЬ! ОН ДЛЯ ПРОВЕРОЧНЫХ ЦЕЛЕЙ И ВЫХОДИТЬ ИЗ БЕСКОНЕЧНОГО ЦЫКЛА!!
    break

logging.debug('Bot was stopped!')

































