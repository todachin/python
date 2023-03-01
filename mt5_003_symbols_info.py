import MetaTrader5 as mt5
# MetaTrader 5パッケージについてのデータを表示する
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)
 
# MetaTrader 5ターミナルとの接続を確立する
if not mt5.initialize():
   print("initialize() failed, error code =",mt5.last_error())
   quit()
 
# 気配値表示でEURJPY銘柄の表示を有効にする試み
selected=mt5.symbol_select("EURJPY",True)
if not selected:
  print("Failed to select EURJPY")
  mt5.shutdown()
  quit()
 
# EURJPY銘柄プロパティを表示する
symbol_info=mt5.symbol_info("EURJPY")
if symbol_info!=None:
  # ターミナルデータを「そのまま」表示する    
  print(symbol_info)
  print("EURJPY: spread =",symbol_info.spread,"  digits =",symbol_info.digits)
  # 銘柄のプロパティをリストとして表示する
  print("Show symbol_info(\"EURJPY\")._asdict():")
  symbol_info_dict = mt5.symbol_info("EURJPY")._asdict()
  for prop in symbol_info_dict:
    print("  {}={}".format(prop, symbol_info_dict[prop]))
 
# MetaTrader 5ターミナルへの接続をシャットダウンする
mt5.shutdown()