#指値を一定間隔に保つよう定期的にオーダーを更新する

import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
from oandapyV20.endpoints import orders,trades
from linebot import LineBotApi
from linebot.models import TextSendMessage
import datetime
import time
import json

#API認証
account_id = '101-009-23770133-001'
access_token = 'f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842'

client = API(access_token=access_token, environment='practice')
#evironment="live" は本番環境
#oanda = API(access_token=access_token, environment="live")
# LINE Bot用
user_id = 'U687be237a4e8fd28dc6bd0592e159868'
channel_access_token = 'GmXfyRoMgpnZoR3pkKiuA84CSpSfDqg5k4HYW0mgHU0/rbglHWtSAkPwkaW62T/hs2BEcOzFLX/Go3Yy+PnOzWQIhJXGdU5psahDKYIatjYzNvnaZBzBhSQUVfcA/6cPme8koEPtuJ6yZRQzW09W0AdB04t89/1O/w1cDnyilFU='

#現在のポジションを取得する
def get_tradeslist():
    r = trades.TradesList(accountID=account_id)
    result = client.request(r)
    return result['trades']

#指定IDのポジションを変更する
def change_id_position(tradeid):
    r = trades.TradeClose(accountID=account_id, tradeID=tradeid)
    result = client.request(r)
    return result

#何秒ごとにループ処理を行うか
interval_sec = 60

ten=0
i=0
n=60
#メインループをn回繰り返す
while i<n:

    #現在のポジションを確認する
    now = datetime.datetime.now().strftime('%H:%M')
    print(now)
    df = pd.DataFrame(data=get_tradeslist())
    ten=ten+1 #10回ごとにリセット
    #ポジションがなければポジションをとる
    if ten > 9 or df.empty:
        #オーダーの判定
        data={'order': {
            'instrument': 'USD_JPY',
            'units': open,
            'type': 'MARKET',
            'positionFill': 'DEFAULT',
        }}
        #オーダー
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        #レスポンスjsonからIDを取得する
        print(json.dumps(rsp, indent=2))
        ten = 0
    if df.empty == False:
        #unrealizedPLをfloat型に変換
        df['unrealizedPL']=df['unrealizedPL'].astype(float)
        #現在のポジションを表示
        print(df.loc[:,['id','instrument','price','openTime','currentUnits','unrealizedPL']])
    #指定時間停止する
    time.sleep(interval_sec)
    i=i+1
