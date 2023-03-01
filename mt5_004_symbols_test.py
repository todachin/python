import pandas as pd
from datetime import datetime,time
import datetime
import time
import MetaTrader5 as mt5

# MetaTrader 5パッケージについてのデータを表示する
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)
# 指定された取引口座へのMetaTrader 5接続を確立する

if not mt5.initialize(login=900013481, server="OANDA-Japan MT5 Live",password="Camar0924600"):
   print("initialize() failed, error code =",mt5.last_error())
   quit()
 
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
rw1 = {} #複数通貨の価格を保存する辞書ワーク {"USDJPY":128.000,"EURJPY":148.000,...}

#DataFrameのカラム
sdt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
cols = ["no","datetime"] + instdata
rw0 = {'no':[0],'datetime':[sdt]}
df_w = pd.DataFrame(rw0)
df_p = df_w.set_index('no') #indexを指定

#ファイルを保存
sdt = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
csv_name = "c:/backup/price_" + sdt + ".csv"

#メイン処理
#処理インターバル
interval_sec = 5 #秒
j = 1 #最初に追加するindex値
s = 0 #DataFrameをdropする先頭のindex
sr = 0 #出力する先頭行（1回目だけ0行目から出力）
n = j + 4320 #ループ回数
hdr = True #ヘッダ出力
#メインループ
#テスト用
#n=70
while j < n:
  #現在の時刻とnoを辞書にセット
  sdt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  rw0 = {"no":j,"datetime":sdt}
  #指定通貨の最新価格を取得
  symbols_get1=mt5.symbols_get(group=instruments)
  if symbols_get1!=None:
    #現在の時刻とnoを辞書にセット
    dt = datetime.datetime.now()
    sdt = dt.strftime('%Y-%m-%d %H:%M:%S')
    rw0 = {'no':j,'datetime':sdt}
    retlen = len(symbols_get1)
    #SymbolInfo型を全件抽出
    for symbol_info1 in symbols_get1:
      info_dic = symbol_info1._asdict() #dict型に変換する
      #print(info_dic)
      rw1[info_dic["name"]] = info_dic["ask"] #askの値を辞書に追加 "USDJPY":128.000
    #rw1["ujreq"] = ""
    #売買判断
    #今回の価格と前回の価格の差を計算
    #差が+-0.1より大きかったらリクエスト
    #保存用データフレームの最終行を取得
    #if j > 1 :
    #  usdjpy = df_p.loc[len(df_p) - 1,"USDJPY"] #最終行のUSDJPY
    #  diff_uj = usdjpy - rw1["USDJPY"]
    #  if diff_uj > 0.1 or diff_uj < -0.1 :
    #    rw1["ujreq"] = "Y"

    rw0.update(rw1) #辞書型同志を結合
    #DataFrameに辞書型のデータを行データとして登録
    df_w = pd.DataFrame.from_dict(rw0,orient = "index").T
    #price用DataFrameの最終行に結合
    df_x = df_w.set_index("no") #indexを指定
    df_i = pd.concat([df_p,df_x],axis = "index")
    df_p = df_i #元のDataFrameに書き戻す

    #最新の5行処理（売買判断）
    df_5 = df_p[len(df_p)-6:] #10行あったら10-6=4（5行目の次6行目から7,8,9,10行目）
    #print(df_p)
    #各通貨の前の行との差を計算する
    df_7 = df_5[instdata]#（日付を除く）すべての通貨カラムを抽出
    df_8 = df_7.astype(astype)  #colums属性をfloatに変更（パラメータは作成済）
    df_d = df_8.diff() #各行の差を計算
    #60行を超えたら50行をcsvファイルに出力し削除する
    if len(df_p) > 59: #60行ごとの処理
        df_5 = df_p[:50] #50行（0～49行まで）抽出
        #1-50行目までを出力　0行目は計算結果がNaNだから
        #CSVファイルに出力'a':追加モード,ヘッダhdr=True or False,インデックスなし
        df_5[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)
        df_p = df_p.drop(index=list(range(s, s + 49)))#先頭から49行削除（次のdiff用に50行目を残す）
        print(j,'rows output',datetime.datetime.now())
        s = s + 49
        hdr = False #ヘッダ出力しない
        sr = 1 #2行名以降を出力
    j = j + 1
  time.sleep(interval_sec)

#CSVファイルに出力'a':追加モード,ヘッダを出力しない,インデックスなし
df_p[sr:].to_csv(csv_name,mode='a',header=hdr,index=True)

# MetaTrader 5ターミナルへの接続をシャットダウンする
mt5.shutdown()
