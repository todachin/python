import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
#from oandapyV20.endpoints.pricing import PricingInfo
#from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints import orders,trades
from linebot import LineBotApi
from linebot.models import TextSendMessage
import datetime
import time
import json

#何秒ごとにデータ観測＆売買判断を行うか
interval_sec = 60

#移動平均の計測期間
duration = 26

#API認証
account_id = '101-009-23770133-001'
access_token = 'f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842'

client = API(access_token=access_token, environment="practice")

#evironment="live" は本番環境
#oanda = API(access_token=access_token, environment="live")

#現在のポジションを取得する
def get_all_position():
    r = trades.TradesList(accountID=account_id)
    client.request(r)
    

params = {
    "granularity": "M1",  # ローソク足の間隔
    "count": 5,         # 取得する足数
    "price": "M",        # B: Bid, A:Ask, M:Mid
}

#メインループ
while True:
    
    #為替データを取得
    r = instruments.InstrumentsCandles(instrument="USD_JPY", params=params)
    client.request(r)

    for candle in r.response["candles"]:
        #completeがTrueのレコードの最終行をlast_dataに格納
        if candle["complete"]:
            last_data = candle
    #最新のローソクのhigh-loの差を取得
    diff = float(last_data["mid"]["h"]) - float(last_data["mid"]["l"])

    order = 0

    if diff >= 0.1:
        # define message
        now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        #text = "[{}]\nドル円 1分足: 10pips以上の変動が発生しました。".format(now)
        text = "USD/JPY" + " " + last_data["mid"]["h"] + " -> " + last_data["mid"]["l"]
        #messages = TextSendMessage(text=text)

        # LINEにメッセージを送る
        #line_bot_api = LineBotApi(channel_access_token)
        #line_bot_api.push_message(user_id, messages=messages)
        
        #open<closeはロングopen>closeはショート
        if float(last_data["mid"]["o"]) < float(last_data["mid"]["c"]):
            order = 1
        else:
            order = 2

    #最新の値段がσ区間を超えているか判定
    if order == 1:
        print("買い注文(ロングポジション)を実行します。")
        data = {
            "order": {
                "instrument": "USD_JPY",
                "units": 100,
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        print(json.dumps(rsp, indent=2))

    if order == 2:

        print("売り注文(ショートポジション)を実行します。")
        data = {
            "order": {
            "instrument": "USD_JPY",
            "units": -100,
            "type": "MARKET",
            "positionFill": "DEFAULT"
            }
        }
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        print(json.dumps(rsp, indent=2))
    time.sleep(interval_sec)