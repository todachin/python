# コマンドライン引数を受取る
import sys
args = sys.argv
print(args[0])

import pandas as pd
import numpy as np
from datetime import datetime,time, timedelta
#import datetime
#import time
import MetaTrader5 as mt5
#Pythonで「REST API」を利用して1分足で10pips変動したらLINEでアラート通知する方法
#https://www.oanda.jp/lab-education/api/usage5/python_rest_api_ten_pips_linealert/
from linebot import LineBotApi
from linebot.models import TextSendMessage

# バックテスト用
import tqdm
import talib
import numba
import os

# LINE Bot用
user_id = "U687be237a4e8fd28dc6bd0592e159868"
channel_access_token = "GmXfyRoMgpnZoR3pkKiuA84CSpSfDqg5k4HYW0mgHU0/rbglHWtSAkPwkaW62T/hs2BEcOzFLX/Go3Yy+PnOzWQIhJXGdU5psahDKYIatjYzNvnaZBzBhSQUVfcA/6cPme8koEPtuJ6yZRQzW09W0AdB04t89/1O/w1cDnyilFU="

# MT5バックテスト共通
cols = [
       'time',
       'bid',
       'ask',
       'type', # 注文タイプ
       'profit', # 実現損益
       'buy_position', # buyポジション数
       'buy_lot', # buyポジションのlot数合計
       'buy_price', # buyポジションの平均価格
       'buy_profit', # buyポジションの含み損益
       'sell_position', # sellポジション数
       'sell_lot', # sellポジションのlot数合計
       'sell_price', # sellポジションの平均価格
       'sell_profit' # sellポジションの含み損益
       ]

df_orders = pd.DataFrame(index=[], columns=cols)
first_lot = 0.1 # 初期ロット
point = 0.01 # 価格の最小単位
spread_limit = 15 # 許容スプレッド
position_limit = 18 # 最大ポジション数
martin_factor = 2.0 # マーチン倍率
nanpin_range = 30 # ナンピン幅
tp_range = 3000 # 利確幅(円)
lc_range = 5000 # ロスカット幅(円)

def sendLine(text):

    # LINEにメッセージを送る
    messages = TextSendMessage(text=text)
    line_bot_api = LineBotApi(channel_access_token)
    line_bot_api.push_message(user_id, messages=messages)

# MT5初期化用
def initializeMT5():
    # MetaTrader 5パッケージについてのデータを表示する
    print("MetaTrader5 package author: ",mt5.__author__)
    print("MetaTrader5 package version: ",mt5.__version__)

    # 指定された取引口座へのMetaTrader 5接続を確立
    if not mt5.initialize(login=900013481, server="OANDA-Japan MT5 Live",password="Camar0924600"):
      print("initialize() failed, error code =",mt5.last_error())
      quit()

# 一定の期間の時系列データを取得
def get_rates(symbol, frame, count):
    rates = mt5.copy_rates_from_pos(symbol, frame, 0, count)
    df_rates = pd.DataFrame(rates)
    df_rates['time'] = pd.to_datetime(df_rates['time'], unit='s')
    df_rates = df_rates.set_index('time')
    #print(df_rates)
    #df_rates.columns = [
    #    'Open', 'High', 'Low', 'Close', 'tick_volume', 'spread', 'real_volume',
    #]
    return df_rates

#注文用関数
def post_market_order(symbol, type, vol, price, dev, sl=None, tp=None, position=None):
  #注文を送信
  request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol, #通貨
    'volume': vol,    #oanda-MT5は最低0.1
    'price': price,   #価格
    'deviation': dev, # float型じゃだめ
    'magic': 234000,  #マジックナンバー
    'comment': "python script open",  # 何でもOK
    'type_time': mt5.ORDER_TIME_GTC,
    'type': type,     #タイプ　BUY | SELL
    'type_filling': mt5.ORDER_FILLING_IOC, # ブローカーにより異なる OANDA = IOC
  }
  # STOP LOSS
  if sl is not None:
     request.update({"sl": sl,})
  # TAKE PROFIT
  if tp is not None:
    request.update({"tp": tp,})
  # TICKET NO
  if position is not None:
    request.update({"position": position})
  print(request) #パラメータ表示

  #オーダーリクエスト
  result = mt5.order_send(request) #オーダー関数呼び出し
  print("order_send(): by {} {} lots at {} with deviation={} points".format(symbol,vol,price,dev));
  #オーダー結果判定
  if result.retcode == mt5.TRADE_RETCODE_DONE:
    #オーダー成功
    print("order_send done, ", result)
    print("   opened position with POSITION_TICKET={}".format(result.order))
    # LINEにメッセージを送る
    text = "order_send done {}".format(result)
    sendLine(text)
  else:
    #オーダー失敗
    print("order_send failed, retcode={}".format(result.retcode))
    # LINEにメッセージを送る
    text = "order_send failed {}".format(result)
    sendLine(text)
    # 結果をディクショナリとしてリクエストし、要素ごとに表示
    result_dict=result._asdict()
    for field in result_dict.keys():
      #辞書のキーと値を出力
      print("   {}={}".format(field,result_dict[field]))
      #値が取引リクエスト構造体の場合は要素ごとに表示
      if field=="request":
          traderequest_dict=result_dict[field]._asdict()
          for tradereq_filed in traderequest_dict:
              print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
  return result

# 売買判断、実行関数
@numba.njit
def calc_orders(
        first_lot,
        current_buy_lot,
        current_buy_price,
        current_sell_lot,
        current_sell_price,
        buy_position,
        buy_lot,
        buy_position_value,
        buy_profit,
        sell_position,
        sell_lot,
        sell_position_value,
        sell_profit,
        point,
        spread_limit,
        tick_len,
        tick_bid,
        tick_ask,
        ):

    orders_time = tick_bid.copy()
    orders_time[:] = np.nan

    orders_bid = tick_bid.copy()
    orders_bid[:] = np.nan

    orders_ask = tick_bid.copy()
    orders_ask[:] = np.nan

    orders_type = tick_bid.copy()
    orders_type[:] = np.nan

    orders_buy_position = tick_bid.copy()
    orders_buy_position[:] = np.nan

    orders_sell_position = tick_bid.copy()
    orders_sell_position[:] = np.nan

    orders_profit = tick_bid.copy()
    orders_profit[:] = np.nan

    orders_buy_profit = tick_bid.copy()
    orders_buy_profit[:] = np.nan

    orders_sell_profit = tick_bid.copy()
    orders_sell_profit[:] = np.nan

    orders_buy_lot = tick_bid.copy()
    orders_buy_lot[:] = np.nan

    orders_sell_lot = tick_bid.copy()
    orders_sell_lot[:] = np.nan

    orders_buy_position_value = tick_bid.copy()
    orders_buy_position_value[:] = np.nan

    orders_sell_position_value = tick_bid.copy()
    orders_sell_position_value[:] = np.nan

    if tick_len > 0:
        for i in range(tick_len):

            ##現在価格の取得
            bid = tick_bid[i]
            ask = tick_ask[i]
            #spread = ask - bid

            ###entry_flgロジック
            #if spread < spread_limit * point:
            #    entry_flg = 1
            #else:
            #    entry_flg = 0
            entry_flg = 1

            ##ポジションの含み損益の確認
            if buy_lot == 0:
                buy_profit = 0
            else:
                buy_profit = round(ask * buy_lot - buy_position_value,0)
            if sell_lot == 0:
                sell_profit = 0
            else:
                sell_profit = round(-(bid * sell_lot) + sell_position_value, 0)

            ##ordersに出力
            orders_bid[i] = bid
            orders_ask[i] = ask
            orders_buy_position[i] = buy_position
            orders_buy_lot[i] = buy_lot
            orders_buy_position_value[i] = buy_position_value
            orders_buy_profit[i] = buy_profit
            orders_sell_position[i] = sell_position
            orders_sell_lot[i] = sell_lot
            orders_sell_position_value[i] = sell_position_value
            orders_sell_profit[i] = sell_profit
            #####

            ##新規buyエントリー
            if buy_position == 0 and entry_flg == 1:
                buy_position = 1 # buyポジション数
                current_buy_price = ask # 最新のbuyポジション価格
                current_buy_lot = first_lot # 最新のbuyポジションのlot数
                buy_lot = first_lot # buyポジションのlot数合計
                buy_position_value = round(ask * first_lot,0) # buyポジションの価値

                ##ordersに出力
                orders_type[i] = 1
                orders_buy_position[i] = buy_position
                orders_profit[i] = 0
                orders_buy_lot[i] = current_buy_lot
                orders_buy_position_value[i] = buy_position_value

            ##新規sellエントリー
            # ------------------------------------------
            # ここにSELLエントリーを記述する

            ##追加buyエントリー
            # 保有ポジションがある
            # 保有ポジション数が上限未満
            # スプレッドが許容内 <- 無効
            # 現在価格が前回BUY価格-ナンピン幅を下回った
            if (
                buy_position > 0 and
                buy_position < position_limit and
                #entry_flg == 1 and
                ask < current_buy_price - nanpin_range * point
                ):

                buy_position += 1 # buyポジション数
                current_buy_lot = buy_lot * martin_factor # 最新のbuylot数
                buy_lot += current_buy_lot # buyポジションのlot数合計
                current_buy_price = ask # 最新のbuy価格
                buy_position_value += current_buy_lot * ask #追加ポジションの価値

                ##ordersに出力
                orders_type[i] = 3
                orders_buy_position[i] = buy_position
                orders_profit[i] = 0
                orders_buy_lot[i] = current_buy_lot
                orders_buy_position_value[i] = buy_position_value

            ##追加sellエントリー
            # 保有ポジションがある
            # 保有ポジション数が上限未満
            # スプレッドが許容内 <- 無効
            # 現在価格が前回SELL価格+ナンピン幅を上回った
            # ------------------------------------------
            # ここにSELLエントリーを記述する

            ##buyクローズTakeProfit
            if (
               buy_position >= 1 and
               buy_profit >= tp_range
                ):

                ##ordersに出力
                orders_type[i] = 5
                orders_profit[i] = buy_profit
                #####

                buy_position = 0 # buyポジション数の初期化
                buy_profit = 0 # buy_profitの初期化
                current_buy_lot = 0 # 最新のbuyポジションのlot数の初期化
                buy_lot = 0 # buyポジションのlot数合計の初期化
                current_buy_price = 0 # 最新のbuyポジション価格の初期化
                buy_position_value = 0 # 最新のbuyポジションの価値を初期化

            ##sellクローズtp
            # ------------------------------------------
            # ここにSELLクローズTakeProfitを記述する

            ##buyクローズLossCut
            if (
                buy_position >= position_limit and
                buy_profit <= lc_range * -1
                ):

                ##ordersに出力
                orders_type[i] = 7
                orders_profit[i] = buy_profit
                #####

                buy_position = 0 # buyポジション数の初期化
                buy_profit = 0 # buy_profitの初期化
                current_buy_lot = 0 # 最新のbuyポジションのlot数の初期化
                buy_lot = 0 # buyポジションのlot数合計の初期化
                current_buy_price = 0 # 最新のbuyポジション価格の初期化
                buy_position_value = 0 # 最新のbuyポジションの価値を初期化

            ##sellクローズLossCut
            # ------------------------------------------
            # ここにSELLクローズLossCutを記述する

    return (orders_bid,
            orders_ask,
            orders_type,
            orders_profit,
            orders_buy_position,
            orders_buy_lot,
            orders_buy_position_value,
            orders_buy_profit,
            orders_sell_position,
            orders_sell_lot,
            orders_sell_position_value,
            orders_sell_profit,
            current_buy_lot,
            current_buy_price,
            current_sell_lot,
            current_sell_price,
            buy_position,
            buy_lot,
            buy_profit,
            sell_position,
            sell_lot,
            sell_profit)

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# --------------------ここからメイン処理--------------------
def main():

  initializeMT5()

  # バックテスト用
  symbol = 'USDJPY'
  # 日別テストループ
  current_buy_lot=0.00
  current_buy_price=0.00
  current_sell_lot=0.00
  current_sell_price=0.00
  buy_position=0
  buy_lot=0.00
  buy_position_value = 0
  buy_profit=0
  sell_position=0
  sell_lot=0.00
  sell_profit=0
  sell_position_value = 0

  #過去データ取得
  df=get_rates(symbol,frame=mt5.TIMEFRAME_H1,count=100)
  df_tick = df.reset_index() #indexを初期化　0,1,2…

  #print(df_tick)
 
  if(len(df_tick)>0):
      df = pd.DataFrame(index=[], columns=cols)
      (
      df['bid'], df['ask'], df['type'], df['profit'],
      df['buy_position'], df['buy_lot'], df['buy_position_value'], df['buy_profit'],
      df['sell_position'], df['sell_lot'], df['sell_position_value'], df['sell_profit'],
      current_buy_lot, current_buy_price,
      current_sell_lot, current_sell_price,
      buy_position, buy_lot, buy_position_value, buy_profit,
      sell_position, sell_lot, sell_position_value, sell_profit
      )= calc_orders(
          first_lot = first_lot,
          current_buy_lot = current_buy_lot,
          current_buy_price = current_buy_price,
          current_sell_lot = current_sell_lot,
          current_sell_price = current_sell_price,
          buy_position = buy_position,
          buy_lot = buy_lot,
          buy_position_value = buy_position_value,
          buy_profit = buy_profit,
          sell_position = sell_position,
          sell_lot = sell_lot,
          sell_position_value = sell_position_value,
          sell_profit = sell_profit,
          point = point,
          spread_limit = spread_limit,
          tick_len = len(df_tick),
          tick_bid = df_tick['open'].values,
          #tick_ask = df_tick['ask'].values,
          tick_ask = df_tick['open'].values
          )

      df['time'] = df_tick['time']
      df['spread'] = df_tick['spread']

      #df = df.dropna( )
      #df.to_pickle('/content/drive/My Drive/backup/outputs/df_orders_'+AC_date+'.pkl')
      df.to_csv('c:/backup/df_orders_'+df.loc[0]['time'].strftime('%y%m%d%H%M')+'.csv')
  # MetaTrader 5ターミナルへの接続をシャットダウンする
  mt5.shutdown()

if __name__ == '__main__':
    main()
