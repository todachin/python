#60秒間隔でポジションをチェックし条件を満たしたポジションをクローズする

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

def get_SMA():
    params = {'granularity': 'M1',  # ローソク足の間隔
        "count": 5,         # 取得する足数
        "price": 'M'}        # B: Bid, A:Ask, M:Mid
    #為替データを取得
    r = instruments.InstrumentsCandles(instrument='USD_JPY', params=params)
    client.request(r)
    candle_data = []
    candle_columns = ['time','volume','o','h','l','c']
    for candle in r.response['candles']:
        #completeがTrueのレコードを1行ずつcandle_dataに格納append
        if candle['complete']:
            candle_data.append([candle['time'],candle['volume'],candle['mid']['o'],
            candle['mid']['h'],candle['mid']['l'],candle['mid']['c']])
    #リストをDataFrame化し列名columnsをセット
    candledf=pd.DataFrame(data=candle_data,columns=candle_columns)
    #移動平均を計算
    #新しい列MSEにcloseの値の移動平均値をセットする
    duration = 3 #移動平均でをとるcandleの本数
    candledf['MSE']=candledf['c'].rolling(window=duration).mean()
    return candledf

#現在のポジションを取得する
def get_tradeslist():
    r = trades.TradesList(accountID=account_id)
    result = client.request(r)
    return result['trades']

#指定IDのポジションをクローズする
def close_id_position(tradeid):
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
    #ポジションがないか10分おきにポジションをとる
    if ten > 9 or df.empty:
        #オーダーの判定
        #直近の移動平均線の向きでフォロー
        dfc = get_SMA()
        print(dfc)#MSEの値を確認
        ma1 = round(dfc['MSE'][2],2)
        ma2 = round(dfc['MSE'][3],2)
        #上昇でロング下降でショート
        if ma1 < ma2:
            open = 1
        else:
            open = -1
        data = {
            'order': {
                'instrument': 'USD_JPY',
                'units': open,
                'type': 'MARKET',
                'positionFill': 'DEFAULT',
            }
        }
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
    for data in df.itertuples():
        #isoフォーマットの部分を切り出す　yyyy-mm-ddThh:nn:ss
        isotime=data.openTime[:19]
        #時間差 を計算するdatetime型に変換 NY時間に9時間の時間差を足す
        ot=datetime.datetime.fromisoformat(isotime) + datetime.timedelta(hours=9)
        #現在時刻との差を計算
        td = datetime.datetime.now() - ot
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #オープンして60分経過したポジションはクローズする
        #プラス0.3のポジションをクローズ
        if (td.seconds/60) >= 60 or data.unrealizedPL > 0.3:
            print(now,data.id,'close',td.seconds/60,data.unrealizedPL)
            #クローズ
            r = close_id_position(data.id)


    #print(i,' ',now,' ',round(candledf['MSE'][2],2),' > ',round(candledf['MSE'][3],2))
    #指定時間停止する
    time.sleep(interval_sec)
    i=i+1
