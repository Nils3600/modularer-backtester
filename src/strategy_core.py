import pandas as pd
import re
import indicators
import triggers


def _resolve_indicator(df, spec):
    name = spec["indicator"]
    params = spec.get("params", {})
    output_key = spec.get("output")          # z. B. "UpperBand"
    column_name = spec.get("column")         # optional: benutzerdefinierter Spaltenname

    func = getattr(indicators, name)
    result = func(df, **params)

    if isinstance(result, dict):
        if output_key is None:
            raise ValueError(f"Indikator '{name}' liefert mehrere Werte – bitte 'output' angeben")
        if output_key not in result:
            raise ValueError(f"'{output_key}' nicht gefunden in Ergebnis von '{name}'")

        col = column_name or f"{name}_{output_key}_{'_'.join(str(p) for p in params.values())}"
        df[col] = result[output_key]
        return df[col]

    # Einzelwert (z. B. EMA)
    col = column_name or f"{name}_{'_'.join(str(p) for p in params.values())}"
    df[col] = result
    return df[col]



def _resolve_trigger(name):
    return getattr(triggers, name)



def evaluate_rules(df, rules):
    """
    Liefert ein Dict: Regel-ID → pd.Series[bool]
    """
    rule_results = {}
    for rule in rules:
        rule_id = rule["id"]
        left = _resolve_indicator(df, rule["left"])
        right = (
            _resolve_indicator(df, rule["right"]) if isinstance(rule["right"], dict)
            else rule["right"]
        )
        cond = _resolve_trigger(rule["trigger"])(left, right)
        rule_results[rule_id] = cond
    return rule_results



class StrategyLogicParser:
    def __init__(self, rule_results: dict[str, pd.Series]):
        self.rule_results = rule_results

    def parse_expression(self, expr: str) -> pd.Series:
        allowed = re.compile(r"^[A-Za-z0-9_~&|() \t]+$")
        if not allowed.match(expr.replace(" ", "")):
            raise ValueError("Ungültige Zeichen im Logikausdruck")

        def replace_rule_id(match):
            rule_id = match.group(0)
            if rule_id not in self.rule_results:
                raise ValueError(f"Unbekannte Regel-ID: {rule_id}")
            return f'self.rule_results["{rule_id}"]'

        rule_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        python_expr = rule_pattern.sub(replace_rule_id, expr)
        python_expr = python_expr.replace("&", " & ").replace("|", " | ").replace("~", "~")

        result = eval(python_expr)
        if not isinstance(result, pd.Series):
            raise ValueError("Ausdruck ergibt kein gültiges Ergebnis")
        return result



def resolve_signal_conflicts(signal_frames):
    """
    Erkennt Konflikte zwischen beliebigen Logikpfaden.
    Gibt ein DataFrame mit resolveden Signalen pro Tick zurück.
    Eintrag nur, wenn exakt eine Logikregel aktiv ist.
    """
    import pandas as pd

    logic_ids = list(signal_frames.keys())
    index = next(iter(signal_frames.values())).index
    resolved_df = pd.DataFrame(index=index, columns=["logic_id", "signal", "sl", "tp"])

    for time in index:
        active_entries = []

        for logic_id in logic_ids:
            row = signal_frames[logic_id].loc[time]
            if row["active"]:
                active_entries.append({
                    "logic_id": logic_id,
                    "signal": row["signal"],
                    "sl": row["sl"],
                    "tp": row["tp"]
                })

        # ✅ Nur wenn exakt eine Logik aktiv ist
        if len(active_entries) == 1:
            entry = active_entries[0]
            resolved_df.loc[time] = [
                entry["logic_id"],
                entry["signal"],
                entry["sl"],
                entry["tp"]
            ]
        else:
            resolved_df.loc[time] = [None, None, None, None]

    return resolved_df




def evaluate_signals(rule_results, logic_list):
    """
    Bewertet Entry-Logiken aus der Strategie-Definition:
    - erstellt pro Signal eine Matrix mit 'active', 'sl', 'tp'
    - erkennt Konflikte (mehrere Signale gleichzeitig)
    - erstellt Regelmasken (dict + DataFrame)
    - erstellt Logikmasken pro Logik-ID
    - erstellt Regel-Signal-Matrix pro Kombination 'Lx:Rx'
    """
    parser = StrategyLogicParser(rule_results)
    signals = {}
    signal_frames = {}
    tracked_rules = {}
    index = next(iter(rule_results.values())).index

    # 📦 Regelmasken vorbereiten (dict + DataFrame)
    rule_mask_df = pd.DataFrame(index=index)
    for rule_id, mask in rule_results.items():
        bool_mask = mask.astype(bool)
        tracked_rules[rule_id] = bool_mask
        rule_mask_df[rule_id] = bool_mask

    # 📦 Logikmasken vorbereiten
    logic_mask_df = pd.DataFrame(index=index)

    # 📦 Regel-Signal-Matrix vorbereiten
    rule_signal_df = pd.DataFrame(index=index)

    # 📦 Signal-Matrix pro Signaltyp
    for entry in logic_list:
        signal = entry["signal"]
        expr = entry["when"]
        sl = entry.get("sl")
        tp = entry.get("tp")
        logic_id = entry.get("ID", f"{signal}_anonymous")

        # Bewertung des Logikausdrucks
        try:
            mask = parser.parse_expression(expr)
        except Exception as e:
            print(f"❌ Fehler bei Logikregel '{logic_id}': {e}")
            continue

        # Signal-Matrix pro Tick mit SL/TP
        signal_df = pd.DataFrame(index=index)
        signal_df["signal"] = signal
        signal_df["active"] = mask
        signal_df["sl"] = sl
        signal_df["tp"] = tp
        signal_frames[logic_id] = signal_df

        # Logik-Matrix pro Logik-ID
        logic_mask_df[logic_id] = mask.astype(bool)

        # Regeln extrahieren (z. B. aus "R1 & ~R2")
        rule_ids = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr))
        for rule_id in rule_ids:
            if rule_id in rule_results:
                col_name = f"{logic_id}:{rule_id}"
                rule_signal_df[col_name] = rule_results[rule_id].astype(bool)
    
    resolved = resolve_signal_conflicts(signal_frames)

    

    

    # ✅ Rückgabe
    return {
        "signals": resolved,           # Signal-DFs mit SL/TP
        "rule_masks": tracked_rules,        # Regel-Masken pro ID
        "rule_mask_df": rule_mask_df,       # Regel-Matrix
        "rule_signal_df": rule_signal_df,   # "Lx:Rx"-Matrix
        "logic_mask_df": logic_mask_df,     # "Lx"-Matrix
    }









import pandas as pd

def evaluate_live_row(df, rules, logic_list):
    """
    Für LiveTrading: bewertet die letzte Zeile der Regeln und gibt ggf. ein Signal zurück.
    Unterstützt Trigger mit .shift()-Logik (z. B. crosses_above).
    """
    if df.empty:
        print("⚠️ Leerer DataFrame – keine Bewertung möglich")
        return None

    rule_results = {}

    # Regeln bewerten
    for rule in rules:
        rule_id = rule["id"]

        # Indikatoren berechnen → Series zurückgeben
        left_series = _resolve_indicator(df, rule["left"])
        right_series = (
            _resolve_indicator(df, rule["right"])
            if isinstance(rule["right"], dict)
            else pd.Series([rule["right"]] * len(df), index=df.index)  # Konstante als Series
        )

        try:
            trigger_func = _resolve_trigger(rule["trigger"])
            cond_series = trigger_func(left_series, right_series)
            cond = cond_series.iloc[-1]  # Nur letzte Zeile bewerten
        except Exception as e:
            print(f"❌ Fehler bei Regel '{rule_id}': {e}")
            cond = False

        rule_results[rule_id] = cond

    # Logik-Expressions evaluieren
    valid_signals = []

    for entry in logic_list:
        expr = entry["when"]
        expr_python = expr.replace("~", " not ").replace("&", " and ").replace("|", " or")

        for k, v in rule_results.items():
            expr_python = expr_python.replace(k, str(v))

        try:
            if eval(expr_python):
                valid_signals.append({
                    "signal": entry["signal"],
                    "sl": entry.get("sl"),
                    "tp": entry.get("tp")
                })
        except Exception as e:
            print(f"⚠️ Fehler beim Auswerten von Logik '{expr}': {e}")
            continue

    # Konfliktprüfung
    if not valid_signals:
        return None

    unique_signals = set(s["signal"] for s in valid_signals)
    if len(unique_signals) > 1:
        print(f"⚠️ Signalkonflikt erkannt: {unique_signals}")
        return None

    # Erstes gültiges Signal zurückgeben
    return valid_signals[0]


