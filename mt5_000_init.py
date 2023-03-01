import MetaTrader5 as mt5
# MetaTrader 5パッケージについてのデータを表示する
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)
 
# 指定された取引口座へのMetaTrader 5接続を確立する
if not mt5.initialize(login=900013481, server="OANDA-Japan MT5 Live",password="Camar0924600"):
   print("initialize() failed, error code =",mt5.last_error())
   quit()
 
# 接続状態、サーバ名、取引口座に関するデータを表示する
print(mt5.terminal_info())
# MetaTrader 5バージョンについてのデータを表示する
print(mt5.version())
 
# MetaTrader 5ターミナルへの接続をシャットダウンする
mt5.shutdown()