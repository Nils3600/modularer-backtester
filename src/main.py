# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 14:41:33 2025

@author: hjzfuz
"""

from backtester import Backtester
from load_mt5_data import load_data
from visualizer import ChartPlotter

import pandas as pd

df = load_data.metatrader_csv(r'C:\Stockapp\EURUSD_H1_1525.csv')





strategy = {
  "name": "rsi_bb_combo_mean-reav",
  "description": "Strategie basierend auf RSI-Überkauft/Überverkauft und Bollinger Bänder",
  "start balance": 10000,
  "rpt": 0.02,
  "lever": 300,
  
  "rules": [
    {
      "id": "R1",
      "left": {
        "indicator": "price",
        "params": { "field": "Close" }
      },
      "right": {
        "indicator": "bollinger_bands",
        "params": { "period": 30, "std_dev": 2 },
        "output": "upper"
      },
      "trigger": "above"
    },
    {
      "id": "R2",
      "left": {
        "indicator": "price",
        "params": { "field": "Close" }
      },
      "right": {
        "indicator": "bollinger_bands",
        "params": { "period": 30, "std_dev": 2 },
        "output": "lower"
      },
      "trigger": "below"
    },
    {
      "id": "R3",
      "left": {
        "indicator": "rsi",
        "params": { "period": 14 }
      },
      "right": 25,
      "trigger": "below"
    },
    {
      "id": "R4",
      "left": {
        "indicator": "rsi",
        "params": { "period": 14 }
      },
      "right": 75,
      "trigger": "above"
    }
  ],

  "entry_logic": [
    {
      "ID": "L1",
      "signal": "buy",
      "when": "R2 & R3",
      "sl": 50,
      "tp": 150
    },
    {
      "ID": "L2",
      "signal": "sell",
      "when": "R1 & R4",
      "sl": 50,
      "tp": 150
    },
    # {
    #   "ID": "L3",
    #   "signal": "buy",
    #   "when": "R1",
    #   "sl": 300,
    #   "tp": 700
    # },
    # {
    #   "ID": "L4",
    #   "signal": "buy",
    #   "when": "sell",
    #   "sl": 300,
    #   "tp": 700
    # }
  ],

  "exit_config": {
    "use_opposite_signal": False,
    "logic": [
      # {
      #   "ID": "E1",
      #   "when": "~R1 & ~R2"
      # },
      # {
      #   "ID": "E2",
      #   "when": "R3 & R4"
      # }
    ],
    # "trailing": {
    #   "distance": 60,
    #   "trigger": "always"
    # }
  }
}



bt = Backtester(df, strategy)
#signals = bt.run()





trades, rule_results, signal_data, metrics, resolved_df = bt.run_backtest(strategy)
trades_df = pd.DataFrame(trades)


#trades_old = bt.generate_trades(entry_mode="pyramiding",cooldown=15, max_open_trades=3)
#trades_old_df = pd.DataFrame(trades_old)


# for t in trades:
#     print(f"{t['entry_time']} → {t['exit_time']} | PnL: {t['pnl']:.4f}")
    




for k, v in metrics.items():
    if k == "Trades" or k == "Equity Curve":
        continue
    print(f'{k}: {v}')




plotter = ChartPlotter(bt.df, trades)


plotter.plot_trades_2(
    entry_mgr=bt.entry_mgr,
    show_equity=True
)

#plotter.plot_trades_plotly()

#wins , losses = analyze_trades(trades)

# trades = bt.generate_trades(entry_mode="pyramiding", max_open_trades=3, cooldown=300)



# strategy = {
#                 "rules": [
#                     {
#                       "id":       "R1",
                      
#                       "left": {
#                                   "indicator": "bollinger_bands",
#                                   "params": { "period": 20, "std_dev": 2 },
#                                   "output": "upper",
#                                }   ,
                      
#                       "trigger":  "above",
                      
#                       "right": {
#                                   "indicator": "price",
#                                   "params": { "field": "Close" }
                                  
#                       }
                      
#                     },
                    
#                     {
#                       "id":       "R2",
                      
#                       "left": {
#                                   "indicator": "bollinger_bands",
#                                   "params": { "period": 20, "std_dev": 2 },
#                                   "output": "lower",
#                                }   ,
                      
#                       "trigger":  "below",
                      
#                       "right": {
#                                   "indicator": "price",
#                                   "params": { "field": "Close" }
                                  
#                       }
#                      }
                      
#                     ],
                    
                    
#                 "logic": [
                                
#                     {
#                       "signal": "buy",
#                       "when": "R1 & ~R2",
#                       "sl": 20,
#                       "tp": 60
                    
#                     },
#                     {
#                       "signal": "sell",
#                       "when": "R2 & ~R1",
#                       "sl": 20,
#                       "tp": 60
                    
#                     }
            
#                 ]
            
#             }