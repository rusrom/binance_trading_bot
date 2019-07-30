import os.path
import sqlite3

import sqlite_queries


DB_DIR = 'db'
DB_FILE = 'binance.db'

db_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_DIR)
db_file_path = os.path.join(db_dir_path, DB_FILE)


# Создание файла базы данных sqlite и создание таблицы orders
def check():
    db_is_new = not os.path.exists(db_file_path)
    if db_is_new:
        with sqlite3.connect(db_file_path) as conn:
            cursor = conn.cursor()
            cursor.executescript(sqlite_queries.create_tables)


# Привести ответ БД к словарю {имя_поля: значение, }
def normalize_result(curs):
    # Все поля
    fields = tuple(i[0] for i in curs.description)
    # Результаты запроса об активном ордере
    row = curs.fetchone()
    if row:
        return dict(zip(fields, row))
    return row


# Получить активный ордер
def get_active_order():
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()

        # Получить активный ордер
        db_response = curs.execute('SELECT * FROM active;')

        # Привести ответ БД к виду {имя_поля: значение, }
        return normalize_result(db_response)


# Получаем все активные ордера
# def get_active_orders():
#     with sqlite3.connect(db_file_path) as conn:
#         curs = conn.cursor()
#         # Получить все активные ордера
#         query = 'SELECT * FROM active;'
#         curs.execute(query)
#         active_orders = {
#             row[6]: {
#                 'signal': row[0],
#                 'pair': row[1],
#                 'type': row[2],
#                 'best_bid': row[3],
#                 'best_ask': row[4],
#                 'spread': row[5],
#                 'created': row[7],
#                 'amount': row[8],
#                 'price': row[9],
#                 'notional': row[10],
#                 'cancel_price': row[11],
#                 'filled': row[12],
#                 'actual_amount': row[13],
#                 'tp_order_id': row[14],
#                 'tp_price': row[15],
#                 'sl_order_id': row[16],
#                 'sl_price': row[17]
#             }
#             for row in curs.fetchall()
#         }
#     return active_orders


# Запись успешно выставленного превого ордера в цикле
def db_write_first_order(new_order, notional, cancel_price, best_price, spread):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        # TODO: [REPAIR] Дописать поля добавленные по ходу разработки
        curs.execute(
            '''
            INSERT INTO active (signal, pair, type, best_bid, best_ask, spread, order_id, created, amount, price, notional, cancel_price)
            VALUES (:side, :symbol, :type, :best_bid, :best_ask, :spread, :order_id, datetime(:created, 'unixepoch', 'localtime'), :amount, :price, :notional, :cancel_price);''',
            {
                'side': new_order['side'],
                'symbol': new_order['symbol'],
                'type': new_order['type'],
                'best_bid': float(best_price['bidPrice']),
                'best_ask': float(best_price['askPrice']),
                'spread': spread,
                'order_id': int(new_order['orderId']),
                'created': new_order['transactTime'] / 1000,
                'amount': float(new_order['origQty']),
                'price': float(new_order['price']),
                'notional': float(notional),
                'cancel_price': float(cancel_price)
            }
        )
        conn.commit()


def write_waiting_data(signal, pair, wait_price, wait_cancel):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute('INSERT  INTO active(signal, pair, wait_price, wait_cancel) VALUES (?, ?, ?, ?)', (signal, pair, wait_price, wait_cancel))
        conn.commit()


def clear_active_orders():
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute('DELETE FROM active;')
        conn.commit()


def update_active_order(*data_for_update):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute(
            'UPDATE active SET type=?, best_bid=?, best_ask=?, spread=?, '
            'start_created=datetime(?, "unixepoch", "localtime"), start_price=?, order_id=?,'
            'created=datetime(?, "unixepoch", "localtime"), amount=?, price=?, notional=?, status=?', data_for_update)
        conn.commit()


def update_active_re_order(*data_for_update):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute(
            'UPDATE active SET order_id=?, created=datetime(?, "unixepoch", "localtime"), amount=?, '
            'price=?, notional=?, status=?', data_for_update)
        conn.commit()


def update_active_order_tp_sl(*data_for_update):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute(
            'UPDATE active SET actual_amount=?, tp_order_id=?, tp_price=?, tp_amount=?,'
            'sl_order_id=?, sl_price=?, sl_amount=?', data_for_update)
        conn.commit()



# Добавление времени исполнения ордера
def update_active_order_filled(status, ts):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute('UPDATE active SET status=?, filled=datetime(?, "unixepoch", "localtime")', (status, ts))
        conn.commit()


def write_close_cycle_to_history(data_to_write):
    with sqlite3.connect(db_file_path) as conn:
        curs = conn.cursor()
        curs.execute(
            'INSERT INTO history (signal, pair, type, best_bid, best_ask, spread, start_created, start_price, '
            'order_id, created, amount, price, notional, status, filled, actual_amount, tp_order_id, tp_price, '
            'tp_amount, sl_order_id, sl_price, sl_amount, wait_price, wait_cancel, close, finished)'
            'VALUES (:signal, :pair, :type, :best_bid, :best_ask, :spread, :start_created, :start_price, :order_id, '
            ':created, :amount, :price, :notional, :status, :filled, :actual_amount, :tp_order_id, :tp_price,'
            ':tp_amount, :sl_order_id, :sl_price, :sl_amount, :wait_price, :wait_cancel, '
            ':close, datetime(:finished, "unixepoch", "localtime"));', data_to_write)
        conn.commit()


# update_active_order('STOP_LIMIT', 1, 2, 3, 4444444, 1528227482622/1000, 66, 7, 8, 9, 'NEW')

# new_order = {
#     'clientOrderId': 'gnQjFiVBrZdZQ8OxGfkidX',
#     'executedQty': '0.00000000',
#     'orderId': 30666254,
#     'origQty': '0.10000000',
#     'price': '88.98000000',
#     'side': 'BUY',
#     'status': 'NEW',
#     'stopPrice': '120.00000000',
#     'symbol': 'NEOUSDT',
#     'timeInForce': 'GTC',
#     'transactTime': 152822801690,
#     'type': 'STOP_LOSS_LIMIT'
# }
#
# cancel_price = 74.56
# notional = 11.0000793
# best_price = {
#     'symbol': 'LTCUSDT',
#     'bidPrice': '96.47000000', 'bidQty': '4.21764000',
#     'askPrice': '96.61000000', 'askQty': '0.61605000'
# }
# spread = 0.23
# db_write_first_order(new_order, notional, cancel_price, best_price, spread)


res = get_active_order()
import time
res.update({'close': None, 'finished': time.time()})
write_close_cycle_to_history(res)
