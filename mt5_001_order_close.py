#保有ポジションを取得し、条件に応じて決済
import pandas as pd
from datetime import datetime,time
import datetime
import time
import MetaTrader5 as mt5

# MetaTrader 5パッケージについてのデータを表示
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)
# 指定された取引口座へのMetaTrader 5接続を確立

if not mt5.initialize(login=900013481, server="OANDA-Japan MT5 Live",password="Camar0924600"):
  print("initialize() failed, error code =",mt5.last_error())
  quit()

#注文用関数
def post_market_order(symbol, type, volume, price, deviation, sl=None, tp=None, position=None):
  #注文を送信
  request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol,
    'volume': volume,  #oanda-MT5は最低0.1
    'price': price,
    'deviation': deviation,   # float型じゃだめ
    'magic': 234000,
    'comment': "python script order",    # 何でもOK
    'type_time': mt5.ORDER_TIME_GTC,
    'type': type,
    'type_filling': mt5.ORDER_FILLING_IOC, # ブローカーにより異なる(OANDAはIOCのみ)
  }
  if sl is not None:
     request.update({"sl": sl,})
  if tp is not None:
    request.update({"tp": tp,})
  if position is not None:
    request.update({"position": position})
  #オーダーリクエスト
  print(request)
  result = mt5.order_send(request)
  print("order_send(): by {} {} lots at {} with deviation={} points".format(symbol,vol,price,dev));
  if result.retcode == mt5.TRADE_RETCODE_DONE:
    print("order_send done, ", result)
    print("   opened position with POSITION_TICKET={}".format(result.order))
  else:
    print("order_send failed, retcode={}".format(result.retcode))
    # 結果をディクショナリとしてリクエストし、要素ごとに表示
    result_dict=result._asdict()
    for field in result_dict.keys():
      print("   {}={}".format(field,result_dict[field]))
      # これが取引リクエスト構造体の場合は要素ごとに表示
      if field=="request":
          traderequest_dict=result_dict[field]._asdict()
          for tradereq_filed in traderequest_dict:
              print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
  return result

#取得する通貨のリスト
instdata=["USDJPY","EURJPY","GBPJPY"]
instruments = ",".join(instdata) #一つの文字列に結合する

#DataFrameの価格処理のためのastype用パラメータ
astype = {}
for txt in instdata:
    astype[txt] = "float" # {"USDJPY":"float","EURJPY":"float"...

#メイン処理
#処理インターバル
interval_sec = 5 #秒
j = 1 #最初に追加するindex値
s = 1 #DataFrameをdropする先頭のindex
profit_target = 1000 # 利益目標 
#メインループ
##########テスト用##########
#n=5
while 1: #無限ループ
  #### ポジションの確認###########################################

  buy_position = 0 # buyポジション数の初期化
  sell_position = 0 # sellポジション数の初期化
  buy_profit = 0 # buy_profitの初期化
  sell_profit = 0 # sell_profitの初期化
  current_buy_lot = 0 # 最新のbuyポジションのlot数の初期化
  current_sell_lot = 0 # 最新のsellポジションのlot数の初期化

  positions=mt5.positions_get(group = instruments) # ポジション情報を取得
  print(positions)
  for i in range(len(positions)): # 全てのポジションを確認
    order_type = positions[i]["type"] # buyかsellか取得
    profit = positions[i]["profit"] # ポジションの含み損益を取得
    
    if order_type == mt5.ORDER_TYPE_BUY: # buyポジションの場合
      buy_position += 1 # buyポジションのカウント
      buy_profit += profit # buyポジションの含み損益に加算
      current_buy_lot = positions[i]["volume"] # 最新のbuyポジションのlot数
      current_buy_price = positions[i]["price_open"] # 最新のbuyポジションの取得価格

    if order_type == mt5.ORDER_TYPE_SELL: # sellポジションの場合
      sell_position += 1 # sellポジションのカウント
      sell_profit += profit # sellポジションの含み損益に加算
      current_sell_lot = positions[i]["volume"] # 最新のsellポジションのlot数
      current_sell_price = positions[i]["price_open"] # 最新のsellポジションの取得価格

  #ポジションリストを取得
  #positions=mt5.positions_get()
  #if positions is None:
  #  print("No positions, error code={}".format(mt5.last_error()))
  #elif len(positions) > 0:
  #  #print("positions_get()={}".format(len(positions)))
  #  # pandas.DataFrameを使用してこれらのポジションを取得
  #  df_s=pd.DataFrame(list(positions),columns=positions[0]._asdict().keys())
  #  df_s['time'] = pd.to_datetime(df_s['time'], unit='s')
  #  #不要な列をdropし元のdataframeを更新するinplace=true
  #  df_s.drop(['time_update', 'time_msc', 'time_update_msc', 'external_id'], axis=1, inplace=True)
  #  #dataframeから利益が出ているポジションを決済
  #  for index,data in df_s.query("profit >= 1000").iterrows():
  #    ticket = data["TICKET"] #TICKETを取得

  #### buyクローズ##################################################
  if buy_position > 0 and buy_profit > profit_target:
    for i in range(len(positions)):
      if positions[i]["type"] == mt5.ORDER_TYPE_BUY: # buyポジションをクローズ
        symbol = positions[i]["symbol"]
        type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
        position = positions[i]["ticket"] # チケットナンバーを取得
        volume = positions[i]["volume"] # lot数を取得
        result = post_market_order(symbol,order_type,volume,price,20)
        if result is None:
          print("close oder send no result")
  
  #### sellクローズ#################################################
  if sell_position > 0 and sell_profit > profit_target:
    for i in range(len(positions)):
      if positions[i]["type"] == mt5.ORDER_TYPE_SELL: # sellポジションをクローズ
        symbol = positions[i]["symbol"]
        type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
        position = positions[i]["ticket"] # チケットナンバーを取得
        volume = positions[i]["volume"] # lot数を取得
        result = post_market_order(symbol,order_type,volume,price,20)
        if result is None:
          print("close oder send no result")
  j = j + 1
  time.sleep(interval_sec)

# MetaTrader 5ターミナルへの接続をシャットダウン
mt5.shutdown()
