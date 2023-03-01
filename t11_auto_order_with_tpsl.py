#ポジションがないときTP、SL付きでオーダーをリクエストする
import pandas as pd
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
from oandapyV20.endpoints.pricing import PricingInfo
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

#指定IDのポジションをクローズする
def close_id_position(tradeid):
    r = trades.TradeClose(accountID=account_id, tradeID=tradeid)
    result = client.request(r)
    return result

#レート桁数
DECIMALS = 3 

#履歴データcandlesを取得してDataFrameに変換する
def get_candles_to_df():
    params = {
        "granularity": "S5",  # ローソク足の間隔
        "count": 5,         # 取得する足数
        "price": "M",        # B: Bid, A:Ask, M:Mid
    }
    #為替データを取得
    r = instruments.InstrumentsCandles(instrument="USD_JPY", params=params)
    rv = client.request(r)

    #データフレームへの変換
    df = pd.json_normalize(rv, record_path='candles', meta=['instrument', 'granularity'], sep='_')
    #コラム名の変更
    df.columns = ['complete', 'volume', 'time_UTC', 'open', 'high', 'low', 'close', 'pair', 'ashi']
    
    #完成形のろうそく足を最後から3本分のみ取得
    df = df[df['complete'] == True].tail(3)

    return df

#何秒ごとにデータ観測＆売買判断を行うか
interval_sec = 60

i=0
n=60
#メインループをn回繰り返す
while i<n:
    
    #現在のポジションを確認する
    #print(get_tradeslist())
    lng = 0
    srt = 0
    df = pd.DataFrame(data=get_tradeslist())
    if df.empty == False:
        for data in df.itertuples():
            if int(data.currentUnits) > 0:
                lng = 1
            else:
                srt = 1
    #計算用に属性を変更
    dfh = get_candles_to_df()
    dfh = dfh.astype({'open': float, 'close': float, 'high': float, 'low': float})
    #3本分のろうそく足毎のトレンドの判定
    dfh.loc[round(dfh['close'] - dfh['open'],DECIMALS) > 0, 'trend'] = 1  #陽線（赤）
    dfh.loc[round(dfh['close'] - dfh['open'],DECIMALS) < 0, 'trend'] = -1 #陰線（黒）
    dfh.loc[round(dfh['close'] - dfh['open'],DECIMALS) == 0, 'trend'] = 0  #同じ
    #売買シグナルの判定
    if dfh.trend.sum() == 3: #すべて陽線（上昇）
        signal = 1
        #print("買シグナル!")
    elif dfh.trend.sum() == -3: #すべて陰線（下降）
        signal = -1
        #print("売シグナル!")
    else:
        signal = 0
        #print("シグナルなし")
    print(dfh)

    #現在の価格を取得する
    r = PricingInfo(accountID=account_id, params={'instruments': 'USD_JPY'})
    rsp = client.request(r)
    nowask = rsp['prices'][0]['closeoutAsk']
    nowbid = rsp['prices'][0]['closeoutBid']
    #takeprofitとstoplossのpips設定
    tp = '0.3'
    sl = '0.5'

    #発注データのセット      
    data = {
        "order": {
            "type": "MARKET",
            "instrument": "USD_JPY",
            "units": 1,
            "takeProfitOnFill": {
                "distance": tp
            },
            "stopLossOnFill": {
                "distance": sl
            },
        }
    }
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if lng == 0:
        data['order']['units'] = 1
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        print(now,'long order')
    if srt == 0:
        data['order']['units'] = -1
        ep = orders.OrderCreate(accountID=account_id, data=data)
        rsp = client.request(ep)
        print(now,'short order')

    #レスポンスjsonからIDを取得する
    #print(json.dumps(rsp, indent=2))

    #unrealizedPLをfloat型に変換
    if df.empty == False:
        df['unrealizedPL']=df['unrealizedPL'].astype(float)
    #df['openTime']=pd.to_datetime(df['openTime'])
#    for data in df.itertuples():
    for index, data in df.iterrows():
        #isoフォーマットの部分を切り出す　yyyy-mm-ddThh:nn:ss
        isotime=data['openTime']
        #時間差を計算するdatetime型に変換 NY時間に9時間の時間差を足す
        ot=datetime.datetime.fromisoformat(isotime[:19]) + datetime.timedelta(hours=9)
        #現在時刻との差を計算
        td = datetime.datetime.now() - ot
        df.loc[index,'openTime'] = ot
        df.loc[index,'minutes'] = round(td.seconds/60)
        #print(round(td.seconds/60))


    print(df.loc[:,['id','instrument','price','openTime','minutes','currentUnits','unrealizedPL']])

    #指定時間停止する
    time.sleep(interval_sec)
    i=i+1
