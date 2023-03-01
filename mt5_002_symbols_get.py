import MetaTrader5 as mt5
# MetaTrader 5パッケージについてのデータを表示する
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)
 
# MetaTrader 5ターミナルとの接続を確立する
if not mt5.initialize():
   print("initialize() failed, error code =",mt5.last_error())
   quit()
 
# すべての銘柄を取得する
symbols=mt5.symbols_get()
#print('Symbols: ', len(symbols))
count=0
# 初めの5銘柄を表示する
#for s in symbols:
   #count+=1
   #print("{}. {}".format(count,s.name))
   #if count==5: break
#print()
 
# 名前にRUを含む銘柄を取得する
ru_symbols=mt5.symbols_get("*RU*")
print('len(*RU*): ', len(ru_symbols))
#for s in ru_symbols:
  #print(s.name)
#print()
 
# 名前にUSD、EUR、JPY、GBPを含まない銘柄を取得する
group_symbols=mt5.symbols_get(group="*,!*USD*,!*EUR*,!*JPY*,!*GBP*")
# 名前にJPYを含む銘柄を取得する
group_symbols=mt5.symbols_get(group="*JPY*")
print('len(*,!*USD*,!*EUR*,!*JPY*,!*GBP*):', len(group_symbols))
for s in group_symbols:
  print(s.name,":",s)
 
# MetaTrader 5ターミナルへの接続をシャットダウンする
mt5.shutdown()
 