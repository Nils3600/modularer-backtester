# live_trader.py
import pandas as pd
import MetaTrader5 as mt5
from strategy_core import _resolve_indicator, evaluate_live_row
from datetime import datetime, time, timedelta
import time
from entry_manager import EntryManager
import json

from market_time_utils import (
    load_market_hours,
    load_holidays,
    is_today_holiday,
    is_symbol_open_now,
    get_next_open_timestamp
)

 
class LiveTrader:
    def __init__(self, strategy, symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1, history_size=250):
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.history_size = history_size
        self.df = pd.DataFrame()
        self.connected = False
        self.last_signal = None
        self.position_id = None
        
        self.market_hours = load_market_hours()
        self.holidays = load_holidays()
        
        self.entry_mgr = EntryManager(
            mode="pyramiding",           
            cooldown=15,                 
            max_open_trades=3            
        )
        
        self.timeframe_secounds = {
            
            mt5.TIMEFRAME_M1: 60,
            mt5.TIMEFRAME_M5: 5 * 60,
            mt5.TIMEFRAME_M15: 15 * 60,
            mt5.TIMEFRAME_M30: 30 * 60,
            mt5.TIMEFRAME_H1: 60 * 60,
            mt5.TIMEFRAME_H4: 4 * 60 * 60,
            mt5.TIMEFRAME_D1: 24 * 60 * 60
        }
    
    def timeframe_to_timedelta(self):
        mapping = {
            mt5.TIMEFRAME_M1: timedelta(minutes=1),
            mt5.TIMEFRAME_M2: timedelta(minutes=2),
            mt5.TIMEFRAME_M3: timedelta(minutes=3),
            mt5.TIMEFRAME_M4: timedelta(minutes=4),
            mt5.TIMEFRAME_M5: timedelta(minutes=5),
            mt5.TIMEFRAME_M6: timedelta(minutes=6),
            mt5.TIMEFRAME_M10: timedelta(minutes=10),
            mt5.TIMEFRAME_M12: timedelta(minutes=12),
            mt5.TIMEFRAME_M15: timedelta(minutes=15),
            mt5.TIMEFRAME_M20: timedelta(minutes=20),
            mt5.TIMEFRAME_M30: timedelta(minutes=30),
            mt5.TIMEFRAME_H1: timedelta(hours=1),
            mt5.TIMEFRAME_H2: timedelta(hours=2),
            mt5.TIMEFRAME_H3: timedelta(hours=3),
            mt5.TIMEFRAME_H4: timedelta(hours=4),
            mt5.TIMEFRAME_H6: timedelta(hours=6),
            mt5.TIMEFRAME_H8: timedelta(hours=8),
            mt5.TIMEFRAME_H12: timedelta(hours=12),
            mt5.TIMEFRAME_D1: timedelta(days=1),
            mt5.TIMEFRAME_W1: timedelta(weeks=1),
            mt5.TIMEFRAME_MN1: timedelta(days=30),  # Approximation für einen Monat
        }
        
        
        return mapping.get(self.timeframe, timedelta(minutes=1))  # Standardwert von 1 Minute

        
        
    def is_market_tradable(self):
        if is_today_holiday(self.holidays):
            print("⛔ Heute ist Feiertag")
            return False
    
        if not is_symbol_open_now(self.symbol, self.market_hours):
            print("⏸️ Markt ist außerhalb der Handelszeiten")
            return False

        return True
        
        
    def connect(self):
        self.connected = mt5.initialize()
        if not self.connected:
            raise ConnectionError("MetaTrader 5 konnte nicht gestartet werden")

        account_info = mt5.account_info()
        if account_info is None:
            raise RuntimeError("Keine Verbindung zum MetaTrader-Konto")
        print(f"🔌 Verbunden mit Konto {account_info.login}, Balance: {account_info.balance}")
    
    
    def get_active_positions(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        return list(positions)

    

    def fetch_data(self):
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, self.history_size)
        if rates is None or len(rates) == 0:
            raise ValueError("Konnte keine historischen Daten abrufen")

        df = pd.DataFrame(rates)
        df.columns = [col.capitalize() for col in df.columns]  # Wandelt z. B. 'close' → 'Close'
        df["Time"] = pd.to_datetime(df["Time"], unit="s")
        df.set_index("Time", inplace=True)
        self.df = df
        

    def compute_indicators(self):
        for rule in self.strategy["rules"]:
            for side in ["left", "right"]:
                spec = rule.get(side)
                
                if isinstance(spec, dict):
                    _resolve_indicator(self.df, spec)


    def evaluate_signal(self):
        return evaluate_live_row(self.df, self.strategy["rules"], self.strategy["entry_logic"])


    def place_order(self, signal_info):
        signal = signal_info["signal"]
        sl = signal_info.get("sl")
        tp = signal_info.get("tp")

        # Preise und Orderrichtung
        price = mt5.symbol_info_tick(self.symbol).ask if signal == "buy" else mt5.symbol_info_tick(self.symbol).bid
        order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL
        volume = 0.1  # z. B. 0.1 Lot

        # SL/TP Berechnung (in Punkten)
        sl_price = price - sl / 100000 if signal == "buy" else price + sl / 100000
        tp_price = price + tp / 100000 if signal == "buy" else price - tp / 100000

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": round(sl_price, 5),
            "tp": round(tp_price, 5),
            "deviation": 10,
            "magic": 123456,
            "comment": f"{signal.upper()} via LiveTrader",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"⚠️ Orderfehler: {result.retcode}, Kommentar: {result.comment}")
        else:
            print(f"✅ {signal.upper()} Order platziert @ {price}")
            self.position_id = result.order
            self.last_signal = signal
        
        
    def close_position(self, position):
        opposite_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(self.symbol).bid if opposite_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(self.symbol).ask
    
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": opposite_type,
            "position": position.ticket,
            "price": price,
            "deviation": 10,
            "magic": position.magic,
            "comment": 'Auto-Close via LiveTrader',
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
    
        result = mt5.order_send(close_request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Schließen fehlgeschlagen für Position {position.ticket}: {result.retcode}")
        else:
            print(f"✅ Position {position.ticket} geschlossen @ {price}")


    def run_once(self):
        if not self.is_market_tradable():
            print("⛔ Markt geschlossen – Warte auf Öffnung...")
            return
    
        self.fetch_data()
        
        if self.df.empty or "Close" not in self.df.columns:          
            print("⚠️ Ungültige oder leere Marktdaten")
            return
        
        self.compute_indicators()
        
        
        signal_info = self.evaluate_signal()
        if signal_info:
            
            active_positions = self.get_active_positions()
            now = datetime.utcnow()
            
            if not self.entry_mgr.allow_entry(now, signal_info["signal"], active_positions):
                print(f"🚫 Entry abgelehnt laut EntryManager ({signal_info['signal']})")
                return


            self.place_order(signal_info)
            self.entry_mgr.register_trade({
                "type": signal_info["signal"],
                "entry_time": now,
                "exit_time": None  
            })


            for pos in active_positions:
                if self.entry_mgr.should_exit(
                    position=pos,
                    current_signal=signal_info["signal"],                   # zum Vergleich
                    exit_logic=self.strategy.get("exit_logic"),             # optional
                    rule_results=self.rule_results                          # nur nötig für exit_logic2
                ):
                    self.close_position(pos)
                    pos["exit_time"] = now
                    print(f"🚪 Position {pos['type']} geschlossen (Exit-Kriterium erfüllt)")

        else:
            print("🧘 Kein aktives Signal – abwarten...")


    def start_loop(self):
        interval = self.timeframe_secounds.get(self.timeframe)
        
        print(f"🚀 Starte LiveTrader für {self.symbol} – Intervall: {interval}s")
        while True:
            try:
                if not self.is_market_tradable():
                    next_open = get_next_open_timestamp(self.symbol, self.market_hours)
                    print(f'Next Open Time:{next_open}',flush=True)
                    if next_open:
                        wait = (next_open - datetime.utcnow()).total_seconds()
                        print(f'Wait: {wait}')
                        print(f"🕒 Markt öffnet am {next_open} UTC – Warte {int(wait)} Sekunden...")
                        time.sleep(wait)
                    continue
                
                self.run_once()
            except Exception as e:
                print(f"❌ Fehler im Zyklus: {e}")
            time.sleep(interval) 
