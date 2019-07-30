import decimal


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
def calculate_first_order(signal, best_price, pair_config, binance_limits, order_offset, cancel_offset):
    # Calculate percent of spread between best prices
    spread = spread_percent(best_price)

    # Offset correction
    if spread >= 0.1:
        order_offset = spread + 0.05

    if signal == 'BUY':
        # Расчитываем цену покупки с учетом смещения ORDER_OFFSET
        bid_price = add_percent_to_price(float(best_price['bidPrice']), order_offset)
        # Приводим полученную цену к требованиям биржи о кратности
        bid_price = adjust_to_step(bid_price, binance_limits['filters'][0]['tickSize'])

        # Расчитываем цену отмены ордера с учетом смещения CANCEL_OFFSET
        cancel_price = subtract_percent_from_price(float(best_price['bidPrice']), cancel_offset)
        # Приводим цену отмены к требованиям биржи о кратности
        cancel_price = adjust_to_step(cancel_price, binance_limits['filters'][0]['tickSize'])

        # Рассчитываем кол-во, которое можно купить, и тоже приводим его к кратному значению
        buy_amount = adjust_to_step(pair_config['spend_quote'] / bid_price, binance_limits['filters'][1]['stepSize'])

        # Рассчитываем сумму сделки
        notional = bid_price * buy_amount

        return bid_price, buy_amount, notional, cancel_price, spread

    if signal == 'SELL':
        # Расчитываем цену покупки с учетом смещения ORDER_OFFSET
        ask_price = subtract_percent_from_price(float(best_price['askPrice']), order_offset)

        # Приводим полученную цену к требованиям биржи о кратности
        ask_price = adjust_to_step(ask_price, binance_limits['filters'][0]['tickSize'])

        # Расчитываем цену отмены ордера с учетом смещения CANCEL_OFFSET
        cancel_price = add_percent_to_price(float(best_price['askPrice']), cancel_offset)
        # Приводим цену отмены к требованиям биржи о кратности
        cancel_price = adjust_to_step(cancel_price, binance_limits['filters'][0]['tickSize'])

        # Рассчитываем кол-во, которое можно купить, и тоже приводим его к кратному значению
        sell_amount = adjust_to_step(pair_config['spend_quote'] / ask_price, binance_limits['filters'][1]['stepSize'])

        # Рассчитываем сумму сделки
        notional = ask_price * sell_amount

        return ask_price, sell_amount, notional, cancel_price, spread


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
