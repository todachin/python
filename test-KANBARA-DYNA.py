#　最新の価格を取得しdataframeに追加するだけ
#　複数の通貨を取得する
import pandas as pd
import oandapyV20
from oandapyV20 import API
from oandapyV20.endpoints.pricing import PricingInfo
import oandapyV20.endpoints.instruments as instruments
#from oandapyV20.endpoints.orders import OrderCreate
from datetime import datetime,timedelta,timezone
import datetime
import time
import json

#API認証
account_id = "101-009-23770133-001"
access_token = "f98bf979d013f7775db89f84edd7f2c9-ed0a298fd59d5090f45471641b6d9842"

client = API(access_token=access_token, environment="practice")

#取得する通貨のリスト
#PricingInfoで取得できる通貨は3個まで
instruments1 = ['USD_JPY','EUR_JPY','GBP_JPY']
instruments2 = ['EUR_USD','GBP_USD','EUR_GBP']
#3個ごとのリストを結合
instruments_all = instruments1 + instruments2

#DataFrameのカラム
cols = ['no','datetime'] + instruments1 + instruments2

#DataFrameの価格処理のためのastype用パラメータ
astype = {}
cols_dif = {} #diffの結果を格納する列名パラメータ作成{'USD_JPY':'USD_JPY_d'...}
dt = datetime.datetime.now()
sdt = dt.strftime('%Y-%m-%d %H:%M:%S')
rw0 = {'no':[0,1],'datetime':[sdt,sdt]}
rw1 = {} 
paramsc = {
    "granularity": "H8",  # ローソク足の間隔
    "count": 2,         # 取得する足数
    "price": "M",        # B: Bid, A:Ask, M:Mid
}
for txt in instruments_all:
    astype[txt] = 'float'
    cols_dif[txt] = txt + '_d' #元の列名 + '_d'
    #CSVに保存するDataFrame
    #為替データを取得
    r = instruments.InstrumentsCandles(instrument=txt, params=paramsc)
    client.request(r)
    for candle in r.response["candles"]:
        #completeがTrueのレコードを1行ずつcandle_dataに格納
        if candle["complete"]:
            rw0[txt] = [candle['mid']['h'],candle['mid']['l']]
#直前のCandle値からHIとLOをDataFrameに登録

df_w = pd.DataFrame(rw0)
df_p = df_w.set_index('no') #indexを指定
print(df_p)
#ファイルを保存
sdt = dt.strftime('%Y-%m-%d-%H-%M')
csv_name = 'c:/backup/price_' + sdt + '.csv'

#複数通貨の価格データ取得
def price_data_collecting(params):
    txt = ",".join(params) #一つの文字列に結合する
    params1 = {'instruments': txt}
    #価格取得1回目
    r = PricingInfo(accountID=account_id, params=params1)
    rsp = client.request(r)
    #print(json.dumps(rsp, indent=2))
    ret_dict = {} #戻り値用辞書
    i = 0
    while i < 3:
        #辞書に通貨ごとの値をセット
        ret_dict[rsp['prices'][i]['instrument']] = rsp['prices'][i]['closeoutAsk']
        i = i + 1
    return ret_dict #通貨と価格を辞書で返す{'USD_JPY':138.000...}

#処理インターバル
interval_sec = 5 #1秒
j = 2 #最初に追加するindex値
s = 0 #DataFrameをdropする先頭のindex
sr = 0 #出力する先頭行（1回目だけ0行目から出力）
n = j + 4320 #ループ回数
hdr = True #ヘッダ出力
while j < n:
    #現在の時刻とnoを辞書にセット
    dt = datetime.datetime.now()
    sdt = dt.strftime('%Y-%m-%d %H:%M:%S')
    rw0 = {'no':j,'datetime':sdt}
    #指定通貨の現在価格を取得
    rw1 = price_data_collecting(instruments1)
    rw2 = price_data_collecting(instruments2)
    rw0.update(rw1) #辞書型同志を結合
    rw0.update(rw2) #辞書型同志を結合
    #DataFrameに辞書型のデータを行データとして登録
    df_w = pd.DataFrame.from_dict(rw0,orient = 'index').T
    #price用DataFrameの最終行に結合
    df_x = df_w.set_index('no') #indexを指定
    df_i = pd.concat([df_p,df_x],axis = 'index')
    df_p = df_i #元のDataFrameに書き戻す

    #最新の5行処理（売買判断）
    df_5 = df_p[len(df_p)-6:] #10行あったら10-6=4（5行目の次6行目から7,8,9,10行目）
    df_7 = df_5[instruments_all]#（日付を除く）すべての通貨カラムを抽出
    df_8 = df_7.astype(astype)  #colums属性をfloatに変更（パラメータは作成済）
    df_d = df_8.diff() #各行の差を計算
    #print('df_p',df_p)
    #60行を超えたら50行をcsvファイルに出力し削除する
    if len(df_p) > 59: #60行ごとの処理
        df_5 = df_p[:50] #50行（0～49行まで）抽出
        df_7 = df_5[instruments_all]#（日付を除く）すべての通貨カラムを抽出
        #差の計算用DataFrameの列名を'_d'に変更（元のDataFrameを上書き）
        df_8 = df_7.astype(astype)  #colums属性をfloatに変更（パラメータは作成済）
        df_8.rename(columns=cols_dif,inplace=True) #列名変更、元のDataFrame置き換えinplace=True
        df_d = round(df_8.diff(),5) #各行の差を計算 少数第5桁を丸め
        #df_d = df_8.diff() #各行の差を計算 丸めなし
        #元のDataFrameに差を計算したDataFrameを横方向axis=1に結合する
        df_n = pd.concat([df_5,df_d],axis = 1)
        #1-50行目までを出力　0行目は計算結果がNaNだから
        #CSVファイルに出力'a':追加モード,ヘッダhdr=True or False,インデックスなし
        df_n[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)
        df_p = df_p.drop(index=list(range(s, s + 49)))#先頭から49行削除（次のdiff用に50行目を残す）
        print(j,'rows output',datetime.datetime.now())
        s = s + 49
        hdr = False #ヘッダ出力しない
        sr = 1 #2行名以降を出力
    j = j + 1
    time.sleep(interval_sec)

#残った行の差を計算する
df_7 = df_p[instruments_all]#（日付を除く）すべての通貨カラムを抽出
df_8 = df_7.astype(astype)  #colums属性をfloatに変更（パラメータは作成済）
#差の計算用DataFrameの列名を'_d'に変更（元のDataFrameを上書き）
df_8.rename(columns=cols_dif,inplace=True)
df_d = round(df_8.diff(),5) #各行の差を計算 少数第5桁を丸め
#df_d = df_8.diff() #各行の差を計算 丸めなし
#元のDataFrameに差を計算したDataFrameを横方向axis=1に結合する
df_n = pd.concat([df_p,df_d],axis = 1)
#CSVファイルに出力'a':追加モード,ヘッダを出力しない,インデックスなし
df_n[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)