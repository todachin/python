#Pythonで「REST API」を利用して1分足で10pips変動したらLINEでアラート通知する方法
#https://www.oanda.jp/lab-education/api/usage5/python_rest_api_ten_pips_linealert/

import oandapyV20.endpoints.instruments as instruments
from oandapyV20.endpoints.pricing import PricingInfo
from oandapyV20.endpoints import orders,trades
from oandapyV20 import API
from linebot import LineBotApi
from linebot.models import TextSendMessage
import datetime
import time

# LINE Bot用
user_id = "U687be237a4e8fd28dc6bd0592e159868"
channel_access_token = "GmXfyRoMgpnZoR3pkKiuA84CSpSfDqg5k4HYW0mgHU0/rbglHWtSAkPwkaW62T/hs2BEcOzFLX/Go3Yy+PnOzWQIhJXGdU5psahDKYIatjYzNvnaZBzBhSQUVfcA/6cPme8koEPtuJ6yZRQzW09W0AdB04t89/1O/w1cDnyilFU="

#API認証
account_id = '101-009-23770133-001'
api_token = "f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842"

# 通貨ペアの設定
instrument = "USD_JPY" #

# API用のクラスを定義
client = API(access_token=api_token, environment="practice")

# 為替データを取得

#急な変動を察知する
#5秒間隔で連続3回で0.05以上の差があった場合アラート
interval_sec = 5
first_ask = 0
last_ask = 0
last_bid = 0
cntp = 0
cntm = 0
tp = '0.3'
sl = '0.5'
i = 0
n = 540
sec = 0
while i < n:
    
    #現在の価格を取得する
    r = PricingInfo(accountID=account_id, params={'instruments': instrument})
    rsp = client.request(r)
    ask = rsp['prices'][0]['closeoutAsk']
    bid = rsp['prices'][0]['closeoutBid']
    #前回価格との差を計算
    difask = float(ask) - last_ask
    #最初の1回（last_ask = 0）のときは処理しない
    if last_ask > 0:
        #前回との差が0.05以上だったら連続カウンタcntをプラス
        if  difask > 0.05:
            #最初のaskを保存
            if cntp == 0 : first_ask = round(float(last_ask),3)
            cntp = cntp + 1 #プラス連続カウンタを加算
            cntm = 0    #マイナス連続カウンタを初期化
        else:
            if difask < -0.05:
                if cntm == 0 : first_ask = round(float(last_ask),3)
                cntm = cntm + 1
                cntp = 0
            else:
                first_ask = round(float(last_ask),3)
                cntp = 0
                cntm = 0
    #前回価格を保存
    last_ask = round(float(ask),3)
    units = 0
    #連続判定　0.5以上3連続のプラスまたはマイナスで同方向へ売買
    if cntp == 3:
        units = 1
        cntp = 0
    if cntm == 3:
        units = -1
        cntm = 0
    #発注データのセット指値、逆指値をpipsでセット
    data = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": units,
            "takeProfitOnFill": {
                "distance": tp
            },
            "stopLossOnFill": {
                "distance": sl
            }
        }
    }
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #unit（数量）が0でなければオーダー
    if units != 0:
        r = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(r)
        print(now,'unit:',units,round(float(first_ask),3),' > ',round(float(last_ask),3))

    #指定時間停止する
    time.sleep(interval_sec)
    i = i + 1
    sec = sec + 1
    if sec > 11:
        print(now,first_ask,' - ',last_ask)
        sec = 0