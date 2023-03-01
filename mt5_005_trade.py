import pandas as pd
from datetime import datetime,time
import datetime
import time
import MetaTrader5 as mt5
#Pythonで「REST API」を利用して1分足で10pips変動したらLINEでアラート通知する方法
#https://www.oanda.jp/lab-education/api/usage5/python_rest_api_ten_pips_linealert/
from linebot import LineBotApi
from linebot.models import TextSendMessage

# LINE Bot用
user_id = "U687be237a4e8fd28dc6bd0592e159868"
channel_access_token = "GmXfyRoMgpnZoR3pkKiuA84CSpSfDqg5k4HYW0mgHU0/rbglHWtSAkPwkaW62T/hs2BEcOzFLX/Go3Yy+PnOzWQIhJXGdU5psahDKYIatjYzNvnaZBzBhSQUVfcA/6cPme8koEPtuJ6yZRQzW09W0AdB04t89/1O/w1cDnyilFU="

# LINEにメッセージを送る
text = "mt5_005_trade.py started"
messages = TextSendMessage(text=text)
line_bot_api = LineBotApi(channel_access_token)
line_bot_api.push_message(user_id, messages=messages)

# MetaTrader 5パッケージについてのデータを表示する
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)

# 指定された取引口座へのMetaTrader 5接続を確立
if not mt5.initialize(login=900013481, server="OANDA-Japan MT5 Live",password="Camar0924600"):
  print("initialize() failed, error code =",mt5.last_error())
  quit()

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
  ##########テスト用##########
  #return "order_send" #本番では不要
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
    messages = TextSendMessage(text=text)
    line_bot_api = LineBotApi(channel_access_token)
    line_bot_api.push_message(user_id, messages=messages)
  else:
    #オーダー失敗
    print("order_send failed, retcode={}".format(result.retcode))
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

#テストサーバー用 MetaTrader 5ターミナルとの接続を確立する
#if not mt5.initialize():
#   print("initialize() failed, error code =",mt5.last_error())
#   quit()

#取得する通貨のリスト
instdata=["USDJPY","EURJPY","GBPJPY"]
instruments = ",".join(instdata) #一つの文字列に結合する

#DataFrameの価格処理のためのastype用パラメータ
astype = {}
for txt in instdata:
    astype[txt] = "float" # {"USDJPY":"float","EURJPY":"float"...

#ファイルを保存
sdt = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
csv_name = "c:/backup/price_" + sdt + ".csv"

#メイン処理
#処理インターバル
interval_sec = 5 #秒
j = 1 #最初に追加するindex値
s = 1 #DataFrameをdropする先頭のindex
n = j + 4320 #ループ回数
hdr = True #ヘッダ出力
#メインループ
##########テスト用##########
#n=5
csv_name = "c:/backup/test_" + sdt + ".csv"
while j < n:
  #ポジションリストを取得する
  positions=mt5.positions_get()
  if positions is None:
    print("No positions, error code={}".format(mt5.last_error()))
  elif len(positions) > 0:
    #print("positions_get()={}".format(len(positions)))
    # pandas.DataFrameを使用してこれらのポジションを表として表示する
    df=pd.DataFrame(list(positions),columns=positions[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.drop(['time_update', 'time_msc', 'time_update_msc', 'external_id'], axis=1, inplace=True)
    #print(df)
  #現在の時刻を取得
  sdt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  #指定通貨の最新価格を取得
  symbols_get1=mt5.symbols_get(group=instruments)
  if symbols_get1 is not None:
    #現在の時刻とnoを辞書にセット
    dt = datetime.datetime.now()
    sdt = dt.strftime('%Y-%m-%d %H:%M:%S')
    rw_0 = {'no':j,'datetime':sdt}
    retlen = len(symbols_get1)
    #SymbolInfo型を全件抽出
    for symbol_info1 in symbols_get1:
      info_dic = symbol_info1._asdict() #dict型に変換する
      #print(info_dic)
      rw_0[info_dic["name"]] = info_dic["ask"] #askの値を辞書に追加 "USDJPY":128.000
    rw_0["order"] = 0
    #DataFrameに辞書型のデータを行データとして登録
    df_w = pd.DataFrame.from_dict(rw_0,orient = "index").T
    #最初の1行目の処理（新規データフレームを作成）
    if j == 1:
      #price用DataFrameを作成
      df_p = df_w.set_index("no") #indexを指定
    else:
      df_x = df_w.set_index("no") #indexを指定
      #price用DataFrameの最終行に結合
      df_i = pd.concat([df_p,df_x],axis = "index")
      df_p = df_i.copy() #元のDataFrameに書き戻す

    #判断
    if j > 1 :
      #print(df_p.loc[[j]])
      uj_0 = df_p.loc[j - 1,"USDJPY"]
      uj_1 = df_p.loc[j,"USDJPY"]
      ej_0 = df_p.loc[j - 1,"EURJPY"]
      ej_1 = df_p.loc[j,"EURJPY"]
      gj_0 = df_p.loc[j - 1,"GBPJPY"]
      gj_1 = df_p.loc[j,"GBPJPY"]
      #前回との差を計算（少数第4位丸め）
      uj_sa = round(uj_1 - uj_0,3)
      ej_sa = round(ej_1 - ej_0,3)
      gj_sa = round(gj_1 - gj_0,3)
      ##########テスト用##########
      #if j==2:
      #  uj_sa = 0.1
      #3種類のうちどれかが+-0.1以上動いたとき
      #どの種類かを判定する
      if gj_sa >= 0.1 or gj_sa <= -0.1:
        symbol = "GBPJPY"
      elif ej_sa >= 0.1 or ej_sa <= -0.1:
        symbol = "EURJPY"
      elif uj_sa >= 0.1 or uj_sa <= -0.1:
        symbol = "USDJPY"
      #方向directionを決定
      di = 0 #direction BUYは1　SELLは-1
      if uj_sa <= -0.1 or ej_sa <= -0.1 or gj_sa <= -0.1:
        order_type = mt5.ORDER_TYPE_SELL
        di = -1
        price = mt5.symbol_info_tick(symbol).bid  #symbolの現在bid
      elif uj_sa >= 0.1 or ej_sa >= 0.1 or gj_sa >= 0.1:
        order_type = mt5.ORDER_TYPE_BUY
        di = 1
        price = mt5.symbol_info_tick(symbol).ask  #symbolの現在ask
      df_p.loc[j,"order"] = di
 
      #print("positions = {},order_type = {},sa = {}".format(len(positions),order_type,uj_sa))
      #保有ポジションがないこと
      if len(positions) == 0 and di != 0:
        volume = 0.1 #オーダー数 0.1 : $10000
        point = mt5.symbol_info(symbol).point #symbolのポイント係数を取得
        tp = price + 300 * point * di #BUYならプラスSELLならマイナス 100p=0.1円
        sl = price - 300 * point * di #BUYならマイナスSELLならプラス
        result = post_market_order(symbol,order_type,volume,price,20,sl,tp,None)
        if result is None:
          print("oder send no result")

    #最新の5行処理（トレンド判断）
    plen = len(df_p)
    if j > 5:
      df_5 = df_p[plen - 6:] #10行あったら10-6=4（5行目の次6行目から7,8,9,10行目）
      #各通貨の前の行との差を計算する
      #df_7 = df_5[instdata]#（日付を除く）すべての通貨カラムを抽出
      #df_8 = df_7.astype(astype)  #colums属性をfloatに変更（パラメータは作成済）
      #df_d = df_8.diff() #各行の差を計算
    
    #60行を超えたら50行を削除する
    if plen > 59: #60行ごとの処理
        df_5 = df_p[:50] #50行（0～49行まで）抽出
        #1-50行目までを出力　0行目は計算結果がNaNだから
        #CSVファイルに出力'a':追加モード,ヘッダhdr=True or False,インデックスなし
        df_5[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)
        df_p.drop(index=list(range(s, s + 50)) ,inplace=True)#先頭から50行削除
        #print(df_p)
        print("{} {}rows output".format(datetime.datetime.now(),s))
        s = s + 50
        hdr = False #ヘッダ出力しない
        sr = 1 #2行名以降を出力
    j = j + 1
  time.sleep(interval_sec)

#CSVファイルに出力'a':追加モード,ヘッダを出力しない,インデックスなし
df_p[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)

# MetaTrader 5ターミナルへの接続をシャットダウンする
mt5.shutdown()
