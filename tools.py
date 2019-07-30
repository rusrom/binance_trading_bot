import decimal
import logging


# Ф-ция, которая приводит любое число к числу, кратному шагу, указанному биржей
# Если передать параметр increase=True то округление произойдет к следующему шагу
# def adjust_to_step(value, step, increase=False):
#     return ((int(value * 100000000) - int(value * 100000000) % int(
#         float(step) * 100000000)) / 100000000)+(float(step) if increase else 0)


# Приводит любое число к числу, кратному шагу, указанному биржей
def adjust_to_step(value, step):
    value = str(value).rstrip('0')
    step = step.rstrip('0')
    return decimal.Decimal(value).quantize(decimal.Decimal(step), rounding='ROUND_HALF_UP')


# Правильное округление чисел с плавающей точкой
def correct_round(value, precision):
    value = str(value).rstrip('0')
    precision = '1e' + str(-1*precision)
    return decimal.Decimal(value).quantize(decimal.Decimal(precision), rounding='ROUND_HALF_UP')


# Проверяет достаточно ли средств для тогров по паре
def enough_funds(signal, balances, amount, pair_settings):
    if signal == 'BUY':
        return balances[pair_settings['quote']] >= amount
    if signal == 'SELL':
        return balances[pair_settings['base']] >= amount


# Возвращает балансы по текущей паре
def pair_balances(balances, pair_settings):
    return [
        "{ticker}:{bal:.8f}".format(ticker=ticker, bal=balances[ticker])
        for ticker in balances
        if ticker in [pair_settings['base'], pair_settings['quote']]
    ]


# Прибавить процент к числу
def add_percent_to_price(price, percent):
    return price * (1 + percent / 100)


# Отнять процент от числа
def subtract_percent_from_price(price, percent):
    return price * (1 - percent/100)


def spread_percent(best_price):
    return round(float(best_price['askPrice']) * 100 / float(best_price['bidPrice']) - 100, 2)


# Расчет первого ордера в уикле (цена, обьем)
def calculate_first_order(signal, best_price, pair_config, binance_limits):
    # Calculate percent of spread between best prices
    spread = spread_percent(best_price)

    if signal == 'BUY':
        # Расчитываем цену покупки с учетом смещения ORDER_OFFSET
        bid_price = add_percent_to_price(float(best_price['bidPrice']), order_offset)
        # Приводим полученную цену к требованиям биржи о кратности
        bid_price = adjust_to_step(bid_price, binance_limits['filters'][0]['tickSize'])

        # Рассчитываем кол-во, которое можно купить, и тоже приводим его к кратному значению
        buy_amount = adjust_to_step(pair_config['spend_quote'] / bid_price, binance_limits['filters'][1]['stepSize'])

        # Рассчитываем сумму сделки
        notional = bid_price * buy_amount

        return bid_price, buy_amount, notional, spread

    if signal == 'SELL':

        # Цена отложенного ордера на продажу будет равна Ask Best Price
        ask_price = float(best_price['askPrice'])

        # Рассчитываем кол-во, которое можно купить, и тоже приводим его к кратному значению
        sell_amount = float(adjust_to_step(pair_config['spend_quote'] / ask_price, binance_limits['filters'][1]['stepSize']))

        # Рассчитываем сумму сделки
        notional = float(correct_round(ask_price * sell_amount, binance_limits['quotePrecision']))

        return ask_price, sell_amount, notional, spread


# Получилось ли выставить ордер
def check_order_send(new_order):
    return 'orderId' in new_order


# Причина ошибка выставления ордера
def order_send_error(new_order):
    if 'code' in new_order:
        return 'Code: {} | Massage: {}'.format(new_order['code'], new_order['msg'])
    else:
        return '!!! UNEXPECTED ERROR !!! {}'.format(str(new_order))


def waiting_check(active_order, best_price):
    if active_order['signal'] == 'SELL':
        if active_order['wait_price'] >= float(best_price['bidPrice']):
            return 'order'
        elif active_order['wait_cancel'] <= float(best_price['bidPrice']):
            return 'cancel'
        else:
            return 'wait'

    if active_order['signal'] == 'BUY':
        pass


def calculate_close_order(active_order, fees, limits, pair_settings):
    # Определяем какие комиссии использовать
    fee = fees['BNB_FEE'] if fees['USE_BNB_FEES'] else fees['STOCK_FEE']

    if active_order['signal'] == 'SELL':
        # Рассчитываем реальное количество квотируемой валюты (USDT) после продажи базовой валюты (LTC) с учетом комисий
        # actual_quote = round(subtract_percent_from_price(active_order['notional'], fee), limits['quotePrecision'])
        actual_quote = correct_round(subtract_percent_from_price(active_order['notional'], fee), limits['quotePrecision'])

        # Рассчитываем TAKE PROFIT базовой валюты (LTC) с учетом коммисии биржи
        base_to_earn = add_percent_to_price(active_order['amount'], pair_settings['take_profit'] + fee)
        base_to_earn = adjust_to_step(base_to_earn, limits['filters'][1]['stepSize'])

        # Рассчитываем STOP LOSS базовой валюты (LTC) , с учетом коммиссии биржи
        base_to_loss = subtract_percent_from_price((active_order['amount']), fee + pair_settings['stop_loss'])
        base_to_loss = adjust_to_step(base_to_loss, limits['filters'][1]['stepSize'])

        # Находим цену для TAKE PROFIT
        tp_price = actual_quote / base_to_earn
        tp_price = adjust_to_step(tp_price, limits['filters'][0]['tickSize'])

        # Находим цену для STOP LOSS
        sl_price = actual_quote / base_to_loss
        sl_price = adjust_to_step(sl_price, limits['filters'][0]['tickSize'])

        return float(actual_quote), float(base_to_earn), float(tp_price), float(base_to_loss), float(sl_price)

    if active_order['signal'] == 'BUY':
        pass


# Проверка цена первого ордера все еще BestPrice
def price_isnt_best_price(active_order, best_price):
    if active_order['signal'] == 'SELL':
        best_price = float(best_price['askPrice'])
        if active_order['price'] > best_price:
            return True

    if active_order['signal'] == 'BUY':
        best_price = float(best_price['bidPrice'])
        if active_order['price'] < best_price:
            return True

    return False
