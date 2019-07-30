create_tables = '''
CREATE TABLE IF NOT EXISTS active (
  signal TEXT,                    -- сигнал BUY / SELL
  pair TEXT,                      -- пара LTCUSDT
  type TEXT,                      -- тип открывающего ордера
  best_bid REAL,                  -- лучщая цена покупки
  best_ask REAL,                  -- лучшая цена продажи
  spread REAL,                    -- спред в %
  start_created DATETIME,         -- стартовое время выставления открывающего ордера
  start_price REAL,               -- стартовая цена открывающего ордера
  order_id NUMERIC,               -- номер открывающего ордера
  created DATETIME,               -- время выставления открывающего ордера
  amount REAL,                    -- обьем открывающего ордера
  price REAL,                     -- цена открывающего ордера
  notional REAL,                  -- сумма ордера в квотируемой валюте
  status TEXT,                    -- статус первого ордера
  filled DATETIME NULL,           -- время срабатывания открывающего ордера в цикле
  actual_amount REAL,             -- реальный обьем купленнй/проданной монеты за вычетом комиссий биржи
  tp_order_id NUMERIC,            -- TAKE PROFIT номер закрывающего ордера
  tp_price REAL,                  -- TAKE PROFIT цена закрывающего ордера
  tp_amount REAL,                 -- TAKE PROFIT количество закрывающего ордера
  sl_order_id NUMERIC,            -- STOP LOSS номер закрывающего ордера
  sl_price REAL,                  -- STOP LOSS цена закрывающего ордера
  sl_amount REAL,                 -- STOP LOSS количество закрывающего ордера
  wait_price REAL,                -- цена которую ждем перед открытием первого ордера
  wait_cancel REAL                -- цена при которой перестаем ждать
);

CREATE TABLE IF NOT EXISTS history (
  signal TEXT,                    -- сигнал BUY / SELL
  pair TEXT,                      -- пара LTCUSDT
  type TEXT,                      -- тип открывающего ордера
  best_bid REAL,                  -- лучщая цена покупки
  best_ask REAL,                  -- лучшая цена продажи
  spread REAL,                    -- спред в %
  order_id NUMERIC,               -- номер открывающего ордера в цикле
  created DATETIME,               -- время выставления открывающего ордера
  amount REAL,                    -- обьем открывающего ордера
  price REAL,                     -- цена открывающего ордера
  notional REAL,                  -- сумма ордера в квотируемой валюте
  filled DATETIME NULL,           -- время срабатывания открывающего ордера
  actual_amount REAL,             -- реальный обьем купленнй/проданной монеты за вычетом комиссий биржи
  tp_order_id NUMERIC,            -- TAKE PROFIT номер закрывающего ордера
  tp_price REAL,                  -- TAKE PROFIT цена закрывающего ордера  
  sl_order_id NUMERIC,            -- STOP LOSS номер закрывающего ордера
  sl_price REAL,                  -- STOP LOSS цена закрывающего ордера
  finished DATETIME NULL,         -- время закрытия цикла (TAKE PROFIT, STOP_LOSS, CANCEL)
  cancel_price REAL,              -- цена отмены открывающего ордера
  canceled INTEGER DEFAULT 0      -- был ли ордер отменен
);
'''
