# Modularer Backtester: Python-Toolkit für Trading-Strategien

<image-card alt="Python" src="https://img.shields.io/badge/Python-3.12-blue" ></image-card> <image-card alt="Pandas" src="https://img.shields.io/badge/Pandas-2.0-green" ></image-card> <image-card alt="MetaTrader5" src="https://img.shields.io/badge/MetaTrader5-Live-orange" ></image-card>

## Über mich
Hallo! Ich bin Nils, angehender Data Scientist/FinTech-Entwickler. Dieses Projekt ist mein Portfolio-Highlight: Ein flexibler Backtester, 
den ich von Grund auf gebaut habe, um Strategien zu testen und live zu handeln. 
Es demonstriert meine Skills in Python, Datenanalyse und modularer Software-Architektur.

## Projektbeschreibung
Ein modulares Framework für Trading-Backtests und Live-Trading. Kernfeatures:
- **Indikatoren:** RSI, MACD, Bollinger Bands (erweiterbar via `indicators.py`).
- **Strategie-Parser:** JSON-basierte Regeln (z. B. "RSI > 70 & MACD cross") mit Konfliktlösung.
- **Backtesting:** Simuliert Trades mit Entry/Exit-Manager (Cooldowns, Trailing Stops).
- **Live-Support:** Integration mit MetaTrader5 für Echtzeit-Daten.
- **Visualisierung:** Plotly-Charts für Equity-Kurven und Trade-Performance.

**Herausforderung & Lernerfahrung:** Konflikte bei multiplen Signalen lösen (via `resolve_signal_conflicts` in `strategy_core.py`) – hat mir gezeigt, wie wichtig robuste Logik in Finanztools ist.

## Installation & Demo
1. Klone: `git clone https://github.com/Nils3600/modularer-backtester.git`
2. Installiere: `pip install -r requirements.txt`
3. Teste: Siehe `src/backtester.py` – lade CSV-Daten und starte `run_backtest()`.

## Tech-Stack
- **Core:** Python, Pandas, NumPy
- **Trading:** MetaTrader5
- **Plots:** Plotly



**Lizenz:** MIT .