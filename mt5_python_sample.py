import pandas as pd
import mt5

def main():
    print('')

def get_rates(symbol, frame, count):
    """ 一定の期間の時系列データを取得
    """
    rates = mt5.copy_rates_from_pos(symbol, frame, 0, count)
    df_rates = pd.DataFrame(rates)
    df_rates['time'] = pd.to_datetime(df_rates['time'], unit='s')
    df_rates = df_rates.set_index('time')
    df_rates.columns = [
        'Open', 'High', 'Low', 'Close', 'tick_volume', 'spread', 'real_volume',
    ]
    return df_rates

def post_market_order(symbol, type, vol, price, dev, sl=None, tp=None, position=None):
    """ 注文を送信
    """
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': vol,
        'price': price,
        'deviation': dev,   # float型じゃだめ
        'magic': 234000,
        'comment': "python script open",    # 何でもOK
        'type_time': mt5.ORDER_TIME_GTC,
        'type': type,
        'type_filling': mt5.ORDER_FILLING_IOC, # ブローカーにより異なる
    }
    if sl is not None:
        request.update({"sl": sl,})
    if tp is not None:
        request.update({"tp": tp,})
    if position is not None:
        request.update({"position": position})

    result = mt5.order_send(request)
    return result

if __name__ == '__main__':
    main()
