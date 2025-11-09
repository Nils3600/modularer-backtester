# backtester.py
import pandas as pd
import numpy as np
from tqdm import tqdm
from strategy_core import _resolve_indicator,_resolve_trigger, evaluate_rules, evaluate_signals
from strategy_logic import StrategyLogicParser
from entry_manager import EntryManager


class Backtester:
    
    def __init__(self, df, strategy):
        self.df = df
        self.strategy = strategy
        self.rules = strategy["rules"]
        self.logic = strategy["entry_logic"]
        self.rule_results = {}
        self.signal_masks = {}
        self.signals = pd.Series(index=df.index, dtype=object)
    
    
    
    def evaluate_performance(self, trades):
        """
        Berechnet Backtest-Metriken inkl. Equity-Kurve & Risk-Reward Ratio.
        Unterstützt mehrere gleichzeitige Trades.
        """
        import numpy as np
        df = self.df

        equity_series = pd.Series(index=df.index, dtype=float)
        active_trades = []
        balance = self.strategy["start balance"]
        rpt = self.strategy["rpt"]
        lever = self.strategy["lever"]
        
    
        for time in df.index:
            price = df.loc[time, "Close"]
            
            expo = balance * rpt * lever
    
            # ⏱ Trades aktivieren
            for t in trades:
                if t["entry_time"] == time:
                    active_trades.append(t)
    
            # 📤 Trades schließen
            closed_this_tick = []
            for trade in active_trades[:]:  # Kopie zum sicheren Entfernen
                if time == trade["exit_time"]:
                    pnl = (
                        trade["exit_price"] - trade["entry_price"]
                        if trade["type"] == "buy"
                        else trade["entry_price"] - trade["exit_price"]
                    ) * expo
                    trade["pnl"] = pnl
                    trade["duration"] = trade["exit_time"] - trade["entry_time"]
                    trade["exit_reason"] = trade.get("exit_reason", "unknown")
                
                    # prozentualer Return
                    raw_return = (trade["exit_price"] - trade["entry_price"]) if trade["type"] == "buy" else (trade["entry_price"] - trade["exit_price"])
                    trade["return_pct"] = round((raw_return / trade["entry_price"]) * 100, 4)
                
                    # Preisverlauf während Trade aktiv war
                    sub_prices = df.loc[trade["entry_time"]:trade["exit_time"], "Close"]
                    entry_price = trade["entry_price"]
                    if trade["type"] == "buy":
                        trade["max_favorable"] = ((sub_prices.max() - entry_price) / entry_price) * expo
                        trade["max_adverse"]   = ((sub_prices.min() - entry_price) / entry_price) * expo
                    else:
                        trade["max_favorable"] = ((entry_price - sub_prices.min()) / entry_price) * expo
                        trade["max_adverse"]   = ((entry_price - sub_prices.max()) / entry_price) * expo
                
                    balance += pnl
                    active_trades.remove(trade)

                    closed_this_tick.append(trade)
    
            equity_series[time] = balance
    
        # 🧹 Lücken füllen
        equity_series.ffill(inplace=True)
    
        # 📊 Metriken berechnen
        closed_trades = [t for t in trades if t.get("exit_time")]
        total_trades = len(closed_trades)
        wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
        losses = [t for t in closed_trades if t.get("pnl", 0) <= 0]
        total_profit = sum(t["pnl"] for t in closed_trades)
        avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
        avg_loss = np.mean([t["pnl"] for t in losses]) if losses else 0
        win_rate = len(wins) / total_trades if total_trades else 0
    
        # 📐 Risk-Reward Ratio
        rrr_list = []
        for t in closed_trades:
            risk = abs(t["entry_price"] - t["sl"])
            reward = abs(t["tp"] - t["entry_price"])
            rrr = reward / risk if risk > 0 else None
            t["rrr"] = round(rrr, 2) if rrr else None
            if rrr:
                rrr_list.append(rrr)
    
        avg_rrr = np.mean(rrr_list) if rrr_list else 0
    
        # ✅ Output
        metrics = {
            "Total Trades": total_trades,
            "Wins": len(wins),
            "Losses": len(losses),
            "Win Rate (%)": round(win_rate * 100, 2),
            "Total Profit": round(total_profit, 2),
            "Average Win": round(avg_win, 2),
            "Average Loss": round(avg_loss, 2),
            "Final Balance": round(balance, 2),
            "Average RRR": round(avg_rrr, 2),
            "Equity Curve": equity_series,
            "Trades": closed_trades
        }
    
        return metrics


    
    
    
    def run_backtest(self, strategy):
        df = self.df
        rule_results = {}
        trade_id = 1
        balance = strategy["start balance"]
        rpt = strategy["rpt"]
    
        # 1. Regeln auswerten
        for rule in tqdm(strategy["rules"],desc="🔄 Regeln auswerten"):
            rule_id = rule["id"]
            left_series = _resolve_indicator(df, rule["left"])
            right_series = (
                _resolve_indicator(df, rule["right"])
                if isinstance(rule["right"], dict)
                else pd.Series([rule["right"]] * len(df), index=df.index)
            )
            cond_series = _resolve_trigger(rule["trigger"])(left_series, right_series)
            rule_results[rule_id] = cond_series
    
        # 2. Signale auswerten
        signal_data = evaluate_signals(rule_results, strategy["entry_logic"])
        resolved_df = signal_data["signals"]
        
    
        # 3. Backtest-Schleife
        trades = []
        active_trade = None
    
        
        entry_manager = EntryManager(mode="pyramiding", 
                                     cooldown=15, 
                                     max_open_trades=5,
                                     exit_config=strategy.get("exit_config")
                                     )
        
        trades = []
        active_trades = []
        
        
        
        for time in tqdm(df.index, desc="🔄 Backtesting"):
            row = resolved_df.loc[time]
            bid = df.loc[time, "Close"]
            spread = df.loc[time, "Spread"] / 100000#13 if pd.isna(df.loc[time, "Spread"]) else df.loc[time, "Spread"] / 100000
            ask = bid + spread
            price = ask if row["signal"] == "sell" else bid
        
            # 🔁 Exit-Prüfung für alle offenen Trades
            for trade in active_trades[:]:
                exit_now = entry_manager.should_exit(
                    position=trade,
                    current_signal=row["signal"],
                    rule_results=rule_results,
                    price=price,
                    market_close=df.loc[time, "Close"]
                )

                if exit_now:
                    trade["exit_time"] = time
                    active_trades.remove(trade)



        
            # 🧩 Einstieg prüfen
            if pd.notnull(row["signal"]):
                if entry_manager.allow_entry(time, row["signal"], active_trades):
                    trade = {
                        "id": f"T{trade_id:03}",
                        "logic_id": row["logic_id"],
                        "type": row["signal"],
                        "entry_time": time,
                        "entry_price": price,
                        "sl": row["sl"],
                        "tp": row["tp"],
                        "exit_time": None,
                        "exit_price": None
                    }
                    trades.append(trade)
                    active_trades.append(trade)
                    entry_manager.register_trade(trade)
                    trade_id += 1
                #else:
                    #print(f"❌ Entry abgelehnt um {time} für {row['signal']}", flush=True)
        
        # 🔚 Sauber abschließen
        final_time = df.index[-1]
        final_price = df.loc[final_time, "Close"]
        spread_value = df.loc[final_time, "Spread"]
        spread = 13 / 100000 if pd.isna(spread_value) else spread_value / 100000
        
        for trade in active_trades:
            exit_price = final_price if trade["type"] == "sell" else final_price + spread

            trade["exit_time"] = final_time
            trade["exit_price"] = exit_price


    
        metrics = self.evaluate_performance(trades)
        
        self.trades = trades
        self.entry_mgr = entry_manager
        
            
            
        return trades, rule_results, signal_data, metrics, resolved_df

            
            




