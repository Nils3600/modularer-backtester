import json
from datetime import datetime, time
import pandas as pd

def load_market_hours(file_path="forex_market_hours.json"):
    with open(file_path, "r") as f:
        return json.load(f)

def load_holidays(file_path="holidays.json"):
    with open(file_path, "r") as f:
        return json.load(f)

def is_today_holiday(holiday_dict):
    today_str = datetime.utcnow().date().isoformat()
    return today_str in holiday_dict

def get_today_session(symbol, market_hours):
    now = datetime.utcnow()
    weekday = now.strftime("%A")  # z. B. "Monday"
    market = market_hours.get(symbol)

    if not market:
        return None

    session = market["session"].get(weekday)
    if not session or session == ["closed"]:
        return None
    return session

def is_symbol_open_now(symbol, market_hours):
    now = datetime.utcnow()
    session = get_today_session(symbol, market_hours)
    if not session:
        return False

    start_str, end_str = session
    start = time.fromisoformat(start_str)
    end = time.fromisoformat(end_str)

    return start <= now.time() <= end

def get_next_open_timestamp(symbol, market_hours):
    now = datetime.utcnow()

    for i in range(7):
        next_day = now.date() + pd.Timedelta(days=i)
        weekday = next_day.strftime("%A")
        session = market_hours.get(symbol, {}).get("session", {}).get(weekday)

        if session and session != ["closed"]:
            start_str = session[0]
            start_time = time.fromisoformat(start_str)
            open_datetime = datetime.combine(next_day, start_time)

            # Immer erster zukünftiger Zeitpunkt, sogar heute
            if open_datetime > now:
                return open_datetime
    return None

