# -*- coding: utf-8 -*-
"""
Backtest Runner: Interaktives Script zum Ausführen von Backtests.
Scant ./src/strategies/ nach JSON-Strategien, fragt CSV-Pfad ab und führt Backtest durch.
"""

import os
import json
import pandas as pd
from pathlib import Path
from backtester import Backtester
from load_mt5_data import load_data
from visualizer import ChartPlotter
import sys

def load_strategies_from_dir(dir_path="./strategies"):
    """Scant Verzeichnis nach .json-Dateien und lädt 'strategy'-Dicts."""
    strategies = {}
    if not os.path.exists(dir_path):
        print(f"⚠️ Verzeichnis {dir_path} existiert nicht. Erstelle es und füge JSON-Strategie-Dateien hinzu.")
        return strategies
    
    for file_path in Path(dir_path).glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "strategy" in data:
                    strategy = data["strategy"]
                    name = strategy.get("name", file_path.stem)
                    strategies[name] = strategy
                    print(f"✅ Geladene Strategie: {name} aus {file_path.name}")
                else:
                    print(f"⚠️ Kein 'strategy'-Schlüssel in {file_path.name} gefunden.")
        except json.JSONDecodeError as e:
            print(f"❌ JSON-Fehler in {file_path.name}: {e}")
        except Exception as e:
            print(f"❌ Fehler beim Laden von {file_path.name}: {e}")
    
    return strategies

def main():
    print("Backtest Runner gestartet!")
    
    # 1. CSV-Pfad abfragen
    csv_path = input("📁 Pfad zur CSV-Datei (z.B. 'C:\\Stockapp\\EURUSD_H1_1525.csv'): ").strip()
    if not os.path.exists(csv_path):
        print("❌ CSV-Datei nicht gefunden. Beende.")
        sys.exit(1)
    
    # Daten laden
    print("📊 Lade Daten...")
    df = load_data.metatrader_csv(csv_path)
    print(f"✅ Geladen: {len(df)} Zeilen von {df.index[0]} bis {df.index[-1]}")
    
    # 2. Strategien laden und auswählen
    strategies = load_strategies_from_dir()
    if not strategies:
        print("❌ Keine Strategien gefunden. Füge .json-Dateien in ./src/strategies/ hinzu (mit 'strategy'-Schlüssel).")
        sys.exit(1)
    
    print("\nVerfügbare Strategien:")
    for i, (name, strat) in enumerate(strategies.items(), 1):
        desc = strat.get("description", "Keine Beschreibung")
        print(f"{i}. {name}: {desc}")
    
    try:
        choice = int(input("\n🔢 Welche Strategie ausführen? (Nummer): ")) - 1
        selected_name = list(strategies.keys())[choice]
        strategy = strategies[selected_name]
        print(f"✅ Ausgewählte Strategie: {selected_name}")
    except (ValueError, IndexError):
        print("❌ Ungültige Auswahl. Beende.")
        sys.exit(1)
    
    # 3. Backtest durchführen
    print("🔄 Starte Backtest...")
    bt = Backtester(df, strategy)
    trades, rule_results, signal_data, metrics, resolved_df = bt.run_backtest(strategy)
    
    # 4. Ergebnisse ausgeben
    print("\n📈 Backtest-Ergebnisse:")
    for k, v in metrics.items():
        if k in ["Trades", "Equity Curve"]:
            continue
        if isinstance(v, float):
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")
    
    # Detaillierte Trades (erste 5)
    print("\n💼 Erste 5 Trades:")
    trades_df = pd.DataFrame([t for t in trades if t.get("exit_time")])  # Nur abgeschlossene
    if not trades_df.empty:
        print(trades_df[['id', 'type', 'entry_time', 'exit_time', 'pnl', 'exit_reason']].head().to_string(index=False))
    else:
        print("Keine abgeschlossenen Trades.")
    
    # 5. Plot erstellen
    print("📊 Erstelle Plot...")
    plotter = ChartPlotter(bt.df, trades)
    plotter.plot_trades_2(entry_mgr=bt.entry_mgr, show_equity=True)
    print("✅ Plot gespeichert als 'trade2_plot.html' und geöffnet.")
    
    print("\n🎉 Backtest abgeschlossen!")

if __name__ == "__main__":
    main()