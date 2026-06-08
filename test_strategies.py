import data, backtest, agent
import log_capture; log_capture.install()
all_data = data.get_top5_ohlcv()
results_summary = {}
for coin in all_data:
    subset = {coin: all_data[coin]}
    for idx, strat in enumerate(agent.FALLBACK_STRATEGIES):
        try:
            r = backtest.run_backtest(strat, subset)
            good, _ = backtest.is_strategy_good(r)
            if coin in good:
                print(">>> PASS: {} with strategy {}".format(coin, idx+1))
                if coin not in results_summary:
                    results_summary[coin] = idx+1
        except Exception as e:
            print("Error {} s{}: {}".format(coin, idx+1, e))
print()
for coin in ['BTC','ETH','BNB','SOL','XRP']:
    s = results_summary.get(coin)
    if s:
        print("{}: strategy {} PASS".format(coin, s))
    else:
        print("{}: NO PASS".format(coin))
