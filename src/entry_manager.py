from collections import namedtuple
from datetime import timedelta
from strategy_core import StrategyLogicParser

BlockedSignal = namedtuple("BlockedSignal", ["time", "signal", "reason"])

class EntryManager:
    """
    Reagiert auf Signale.
    Verwalten des Einstiegsverhaltens mit optionalem Cooldown, parallelen Trades und Exit-Steuerung.
    """
    def __init__(self, mode="flat", cooldown=None, max_open_trades=None, exit_config=None):
        self.mode = mode
        self.cooldown = timedelta(minutes=cooldown) if cooldown else None
        self.max_open_trades = max_open_trades
        self.active_trades = []          # intern registrierte Trades
        self.last_entry_time = None
        self.blocked_signals = []
        self.exit_config = exit_config or {}


    def allow_entry(self, time, signal, active_positions):
        if self.mode == "flat":
            if active_positions:
                self._log_blocked(time, signal, "Flat-Modus: Position offen")
                return False

        elif self.mode == "pyramiding":
            if self.max_open_trades is not None and len(active_positions) >= self.max_open_trades:
                self._log_blocked(time, signal, f"{len(active_positions)} offene Trades (max: {self.max_open_trades})")
                return False

        if self.cooldown and self.last_entry_time:
            if time <= self.last_entry_time + self.cooldown:
                self._log_blocked(time, signal, f"Cooldown aktiv bis {self.last_entry_time + self.cooldown}")
                return False

        return True



    def register_trade(self, trade):
        self.active_trades.append(trade)
        self.last_entry_time = trade["entry_time"]
        
        
    def deregister_trade(self, trade):
        self.active_trades.remove(trade)



    def should_exit(self, position, current_signal=None, rule_results=None, price=None, market_close=None):
        entry = position["entry_price"]
        sl_pips = position["sl"]
        tp_pips = position["tp"]
        type_ = position["type"]
    
        trailing = self.exit_config.get("trailing", None)
        trigger_mode = trailing.get("trigger") if trailing else None
        trail_active = trailing is not None
    
        tp_price = entry + tp_pips / 100000 if type_ == "buy" else entry - tp_pips / 100000
        price_direction_positive = price > entry if type_ == "buy" else price < entry
    
    
    
        # 🚧 Trailing-Stop Logik
        if trail_active:
            trail_value = trailing.get("distance", 50) / 100000
            current_trailing_sl = position.get("sl_trailing")
            skip_update = False
    
            if trigger_mode == "after_profit" and not price_direction_positive:
                skip_update = True
    
            elif trigger_mode == "custom":
                custom_logic = trailing.get("when")
                if custom_logic and rule_results:
                    parser = StrategyLogicParser(rule_results)
                    mask = parser.parse_expression(custom_logic) # Maske zwischenspeichern nicht neu berechnen jedes mal
                    if not mask.iloc[-1]:
                        skip_update = True
    
            elif trigger_mode == "stepwise":
                last_sl = current_trailing_sl or (entry - trail_value if type_ == "buy" else entry + trail_value)
                movement = abs(price - last_sl)
                min_step = trailing.get("step_size", trail_value)
                if movement < min_step:
                    skip_update = True
    
            if not skip_update:
                new_sl = (
                    max(current_trailing_sl or entry - trail_value, price - trail_value)
                    if type_ == "buy"
                    else min(current_trailing_sl or entry + trail_value, price + trail_value)
                )
                position["sl_trailing"] = new_sl
    
            # ⛔ SL verletzt?
            effective_sl = position.get("sl_trailing")
            if (type_ == "buy" and price <= effective_sl) or (type_ == "sell" and price >= effective_sl):
                position["exit_reason"] = "trailing_stop"
                position["exit_price"] = market_close or price
                return True
    
    
        else:
            # 🧱 Klassischer SL
            sl_price = entry - sl_pips / 100000 if type_ == "buy" else entry + sl_pips / 100000
            if (type_ == "buy" and price <= sl_price) or (type_ == "sell" and price >= sl_price):
                position["exit_reason"] = "stop_loss"
                position["exit_price"] = market_close or price
                return True
    
    
    
        # 🎯 TP
        if (type_ == "buy" and price >= tp_price) or (type_ == "sell" and price <= tp_price):
            position["exit_reason"] = "take_profit"
            position["exit_price"] = market_close or price
            return True
    
    
    
        # ⚔️ Gegensignal
        if self.exit_config.get("use_opposite_signal") and current_signal:
            is_opposite = (type_ == "buy" and current_signal == "sell") or (type_ == "sell" and current_signal == "buy")
            if is_opposite:
                position["exit_reason"] = "opposite_signal"
                position["exit_price"] = price
                return True
    
    
    
        # 📘 Logikmasken
        for logic in self.exit_config.get("logic", []):
            parser = StrategyLogicParser(rule_results)
            mask = parser.parse_expression(logic["when"])
            if mask.iloc[-1]:
                position["exit_reason"] = logic.get("ID", "custom_exit")
                position["exit_price"] = price
                return True
    
        return False





    def _log_blocked(self, time, signal, reason):
        self.blocked_signals.append(BlockedSignal(time, signal, reason))

    def get_blocked_signals(self):
        return self.blocked_signals

    def to_plotly_markers(self, y_level=None):
        import plotly.graph_objects as go

        if not self.blocked_signals:
            return []

        times = [b.time for b in self.blocked_signals]
        labels = [f"{b.signal.upper()} blockiert<br>{b.reason}" for b in self.blocked_signals]

        y = [None] * len(times) if y_level is None else y_level

        return [go.Scatter(
            x=times,
            y=y,
            mode="markers+text",
            marker=dict(symbol="x-thin-open", size=10, color="gray"),
            text=labels,
            textposition="top center",
            name="BLOCKIERT",
            showlegend=True,
            hoverinfo="text"
        )]
