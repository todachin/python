#5秒間隔でオーダーするテスト

import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
#from oandapyV20.endpoints.pricing import PricingInfo
#from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints import orders,trades
from linebot import LineBotApi
from linebot.models import TextSendMessage
import datetime
import time
import json

#API認証
account_id = '101-009-23770133-001'
access_token = 'f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842'

client = API(access_token=access_token, environment="practice")
#evironment="live" は本番環境
#oanda = API(access_token=access_token, environment="live")

# LINE Bot用
user_id = "U687be237a4e8fd28dc6bd0592e159868"
channel_access_token = "GmXfyRoMgpnZoR3pkKiuA84CSpSfDqg5k4HYW0mgHU0/rbglHWtSAkPwkaW62T/hs2BEcOzFLX/Go3Yy+PnOzWQIhJXGdU5psahDKYIatjYzNvnaZBzBhSQUVfcA/6cPme8koEPtuJ6yZRQzW09W0AdB04t89/1O/w1cDnyilFU="

#現在のポジションを取得する
def get_tradeslist():
    r = trades.TradesList(accountID=account_id)
    result = client.request(r)
    return result['trades']

#現在のポジションを確認する
def get_open_positions():
    r = positions.OpenPositions(account_id)
    result = client.request(r)
    print(result["positions"]) 

#ポジションをすべてクローズする
def close_short_positions():
    data =  {"longUnits":"ALL"} #ロングのみ
    r = positions.PositionClose(accountID=account_id, instrument="USD_JPY", data=data)
    result = client.request(r)
    print(result)

def close_long_positions():
    data =  {"shortUnits":"ALL"} #ショートのみ
    r = positions.PositionClose(accountID=account_id, instrument="USD_JPY", data=data)
    result = client.request(r)
    print(result)

params = {
    "granularity": "S5",  # ローソク足の間隔
    "count": 5,         # 取得する足数
    "price": "M",        # B: Bid, A:Ask, M:Mid
}

#何秒ごとにデータ観測＆売買判断を行うか
interval_sec = 5

#移動平均の計測期間
duration = 3

i=0
n=1
#メインループをn回繰り返す
while i < n:
    
    #為替データを取得
    r = instruments.InstrumentsCandles(instrument="USD_JPY", params=params)
    client.request(r)

    candle_data = []
    candle_columns = ['time','volume','o','h','l','c']

    for candle in r.response["candles"]:
        #completeがTrueのレコードの最終行をlast_dataに格納
        if candle["complete"]:
            candle_data.append([candle['time'],candle['volume'],
                candle['mid']['o'],candle['mid']['h'],
                candle['mid']['l'],candle['mid']['c']])
    candledf=pd.DataFrame(data=candle_data,columns=candle_columns)
    #移動平均を計算
    candledf['MSE']=candledf['c'].rolling(window=duration).mean()
    #print(candledf)

    #売買判断（ロングorショート）
    order = 0
    data = {
        'order': {
            'instrument': 'USD_JPY',
            'units': 0,
            'type': 'MARKET',
            'positionFill': 'DEFAULT',
        }
    }
    #        "timeInForce": "GTC",
    #        "distance": "0.5",
    #        "type": "TRAILING_STOP_LOSS"
    data['order']['units']=1
    #オーダー
    if order != 0:
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        #レスポンスjsonからIDを取得する
        print(json.dumps(rsp, indent=2))
        print(['rsp']['orderFillTransactioin'])
    
    #指定時間停止する
    time.sleep(interval_sec)
    i=i+1

    #現在のポジションを確認する
    #print(get_tradeslist())
    df = pd.DataFrame(data=get_tradeslist())
    print(df.loc[:,['id','instrument','price','openTime','currentUnits','unrealizedPL']])
