#外部モジュール
from oandapyV20 import API
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions   
import oandapyV20.endpoints.instruments as instruments 
import oandapyV20.endpoints.orders as orders   
from oandapyV20.exceptions import V20Error
    
import json
import time
import datetime
import pandas as pd
import requests
    
#口座情報（自分の情報を入力）
ID = '101-009-23770133-001'
TOKEN = 'f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842'

#取引通貨  
INSTRUMENT = "USD_JPY"
#レート桁数
DECIMALS = 3 
#Pip桁数
PIP_LOCATION = -2 
    
#最大許容スプレッド  
MAX_SPREAD_PIPS = 2 #Pips
        
#ループ回数
LOOP = 10000 #回
#待機時間
WAIT = 60 #秒
      
#ろうそく足取得用
COUNT = 10 #ろうそく足の取得本数
GRANULARITY = "M5" #時間足(5分)
      
UNITS = 1
N = 2 #Pips
    
def Discord(event_type, exception_type, code, contents):
    
  #Webhook
  DISCORD_URL =  ''  #自分で取得したwebhookにおきかえ
      
  #メッセージの編集
  message = '''\
  エンドポイント種類: %s
  例外種類: %s 
  コード: %s 
  内容: %s 
  時間(UTC): %s 
  ''' %(event_type, exception_type, code, contents, \
  f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S}")
    
  data = {'content' :  message}
    
  try:
          #メッセージの送信
          response_body = requests.post(DISCORD_URL, data=data)
          response_body.raise_for_status() #Discordの呼び出しでエラーが出た場合  
  
  except Exception as e:
          print(e)
          raise #ボットを停止させる
    
def Endpoint(ep_type, **kwargs):     #👈
  
  #リトライ条件
  RETRY_LOOP = 3 #回
  RETRY_WAIT = 1 #秒
  RETRY_ERROR = [104, 502, 503]
  
  for i in range(RETRY_LOOP): 
    
    try:
      #エンドポイントの呼び出し判定
      if ep_type == "pricing":  #👈最新レート
        r = pricing.PricingInfo(accountID=kwargs["id"], params=kwargs["params"])  
      elif ep_type == "positions":  #👈ポジション保有
        r = positions.PositionDetails(accountID=kwargs["id"], instrument=kwargs["instrument"])
      elif ep_type == "candles":  #👈ろうそく足
        r = instruments.InstrumentsCandles(instrument=kwargs["instrument"], params=kwargs["params"])
      elif ep_type == "orders":  #👈注文
        r = orders.OrderCreate(accountID=kwargs["id"], data=kwargs["data"])
      else:
        message = "Endpoint type error!"
        print(message)
        raise Exception(message)
  
      #エンドポイント呼び出し
      rv = api.request(r)
      return rv
          
    except V20Error as e:
      err_type = "V20Error"
      status = e.code
      contents = e
  
    except Exception as e:
      err_type = "Exception"
      if hasattr(e, 'code'):
        status = e.code
      else:
        status = 999
      contents = e
    
    #リトライ判定
    if status in RETRY_ERROR:
      time.sleep(RETRY_WAIT)
      message = "リトライ" + str(i+1) + "回目 " + str(status)
      print(message)
      Discord(ep_type, err_type, message, contents)
      
    else:
      Discord(ep_type, err_type, str(status), contents)
      message = "エラー！: %s %s %s %s" %(ep_type,err_type,str(status),contents)
      raise Exception(message)
  
  #リトライ失敗
  message = "Endpoint: %s リトライに失敗! (%d)" %(ep_type, status) 
  #message = "Endpoint: " + ep_type + " リトライに失敗! (" + str(status) + ")" 
  raise Exception(message)
    
def CurrentRate():
          
  #最新レートの取得
  params = {
          "instruments": INSTRUMENT
        }
        
  rv = Endpoint("pricing", id=ID, params=params)  #👈
  
  #スプレッドの計算
  bid = rv['prices'][0]['closeoutBid']
  ask = rv['prices'][0]['closeoutAsk']
  spread = round(float(ask) - float(bid), DECIMALS)
    
  #トレード可能?
  if rv['prices'][0]['tradeable'] == True:
    max_spread = MAX_SPREAD_PIPS * (10 ** PIP_LOCATION)
    if spread < max_spread:
      status = "GO"
    else: #スプレッド拡大中
      status = "SKIP"
  #クローズ/メンテ中
  else:
    status = "CLOSED" #original "STOP" 
    #Discord("CurentRate", status, "", "マーケットクローズ") 
        
  #戻り値  
  return {'status': status, 'bid': bid, 'ask': ask, 'spread': spread}
  
        
def Position():  
        
  #ポジションの確認処理追加
  rv = Endpoint("positions", id=ID, instrument=INSTRUMENT)  #👈
        
  if rv['position']['long']['units'] != "0" or rv['position']['short']['units'] != "0": 
    print("ポジあり。待機")
    status = "SKIP"
  else:
    print("ポジなし。 継続")
    status =  "GO"
      
  return {'status': status}
      
      
def Signal():  #シグナル判定（赤３黒３）
        
  #ろうそく足の取得
  #引数セット
  params = {
          "count": COUNT,
          "granularity": GRANULARITY
        }
    
  rv = Endpoint("candles", instrument=INSTRUMENT, params=params)   #👈
        
  #データフレームへの変換
  df = pd.json_normalize(rv, record_path='candles', meta=['instrument', 'granularity'], sep='_')
  #コラム名の変更
  df.columns = ['complete', 'volume', 'time_UTC', 'open', 'high', 'low', 'close', 'pair', 'ashi']
          
  #完成形のろうそく足を最後から3本分のみ取得
  df = df[df['complete'] == True].tail(3)
      
  #計算用に属性を変更
  df = df.astype({'open': float, 'close': float, 'high': float, 'low': float})
        
  #3本分のろうそく足毎のトレンドの判定
  df.loc[round(df['close'] - df['open'],DECIMALS) > 0, 'trend'] = 1  #陽線（赤）
  df.loc[round(df['close'] - df['open'],DECIMALS) < 0, 'trend'] = -1 #陰線（黒）
  df.loc[round(df['close'] - df['open'],DECIMALS) == 0, 'trend'] = 0  #同じ
        
  #売買シグナルの判定
  if df.trend.sum() == 3: #すべて陽線（上昇）
    signal = 1
    print("買シグナル!")
  elif df.trend.sum() == -3: #すべて陰線（下降）
    signal = -1
    print("売シグナル!")
  else:
    signal = 0
    print("シグナルなし")
      
  print(df)
        
  #戻り値のセット
  return {'signal': signal, 'df': df}
      
    
def Order(r_rate, r_signal): 
    
  #発注処理
  #最後のローソク足の終値の取得
  xclose = r_signal['df']['close'].iat[-1]
      
  #区間内の最高値と最安値の取得
  xmin = r_signal['df']['low'].min()
  xmax = r_signal['df']['high'].max()
  
  print("終値: %s 最高値: %s 最安値: %s" %(xclose, xmax, xmin))
      
  #Risk(Spread)の計算
  if r_signal['signal'] == 1:
    #買：区間の最安値と直前の足の終値の差にN Pips足す
    distance = round(xclose - xmin, DECIMALS)
  elif r_signal['signal'] == -1:
    #売：区間の最高値と直前の足の終値の差にN Pips足す
    distance = round(xmax - xclose, DECIMALS)
    
  #計算した値幅に一定の値を加える  
  distance2 = round(distance + N * (10 ** PIP_LOCATION), DECIMALS)
      
  print("値幅: %s 値幅＋N: %s スプレッド: %s" %(distance, distance2, r_rate['spread']))
    
  #計算結果より現在のスプレッドと比較
  if distance2 < r_rate['spread']:
    print("値幅が足りません。")
    return {'status': 'SKIP'}
    
      
  #発注データのセット      
  data = {
        "order": {
            "type": "MARKET",
            "instrument": INSTRUMENT,
            "units": str(UNITS * r_signal['signal']),
            "takeProfitOnFill": {
                "distance": str(distance2)
            },
            "stopLossOnFill": {
                "distance": str(distance2)
            },
        }
    }
        
  #発注
  rv = Endpoint("orders", id=ID, data=data)   #👈
  
  #結果確認
  print(json.dumps(rv, indent=2))
  
  if "orderFillTransaction" in rv.keys():
    status = "FILLED"
    result = rv['orderFillTransaction']['id']
    contents = rv['orderFillTransaction']
  elif 'orderCancelTransaction' in rv.keys():  
    status = "STOP"
    result = rv['orderCancelTransaction']['reason']
    contents = rv['orderCancelTransaction']  
  else:
    status = "STOP"  
    result = "予期せぬエラー(Status = 201)"
    contents = rv
  
  type="New Order"
  Discord(type, status, result, contents)
  print(status, " : " ,result)  
  
  #戻り値のセット
  return {'status': status}
  
                
if __name__ == "__main__":
          
  try:
         
    api = API(access_token= TOKEN)
    message = ""
    for i in range(LOOP):
          
      #最新レート確認  
      r_rate = CurrentRate()  
      print(r_rate)
      #次の処理
      if r_rate['status'] == "GO":
        print("継続-トレード可能")
        
       #保有ポジションの確認
        r_pos = Position()             
        #ポジション無しの時
        if r_pos['status'] == "GO":   
          #売買シグナルの判定
          r_signal = Signal()
          if r_signal['signal'] != 0: #売買シグナルがでたら注文処理へ
            #注文処理
            r_order = Order(r_rate, r_signal)
            if r_order['status'] != "FILLED" and r_order['status'] != "SKIP":
              raise Exception("停止ー発注エラー") #ボット終了
                                        
      #スプレッドが広すぎる
      elif r_rate['status'] == "SKIP":
        print("スキップ-スプレッド拡大中")    
        
      #マーケットがクローズ（またはメンテ中）
      elif r_rate['status'] == "CLOSED":
        print("スキップーマーケットクローズ中")    
        #break #ボット終了
              
      else:
        raise Exception("停止ー予期せぬエラー発生") #ボット終了
        
      #次のサイクル
      print("待機中 ", i) 
      time.sleep(WAIT)
    message= "Loop上限到達"
  except Exception as e:
    #print(e)
    message = e  
        
  finally:
    Discord("停止", "", "", message)
    print(message, " によりBotが停止しました。 UTC:", datetime.datetime.now(datetime.timezone.utc))