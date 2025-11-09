# -*- coding: utf-8 -*-
"""
Überarbeitete Indikatoren für den modularen Backtester.
Einzel-Output: pd.Series
Multi-Output: dict mit pd.Series
"""

import pandas as pd
import numpy as np


def price(df: pd.DataFrame, field: str = "Close") -> pd.Series:
    """
    Gibt die angegebene Spalte des DataFrames zurück.
    """
    return df[field]


def sma(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Simple Moving Average (SMA)
    """
    return df["Close"].rolling(window=period).mean()


def rsi(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Relative Strength Index (RSI)
    """
    delta = df["Close"].diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Exponential Moving Average (EMA)
    """
    return df["Close"].ewm(span=period, adjust=False).mean()


def macd(df: pd.DataFrame,
         fast: int = 12,
         slow: int = 26,
         signal: int = 9) -> dict:
    """
    MACD (Moving Average Convergence/Divergence)
    Gibt dict mit keys: 'macd', 'signal', 'histogram'
    """
    ema_fast = ema(df, fast)
    ema_slow = ema(df, slow)
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist        = macd_line - signal_line
    return {
        "macd":      macd_line,
        "signal":    signal_line,
        "histogram": hist
    }


def bollinger_bands(df: pd.DataFrame,
                    period: int = 20,
                    std_dev: float = 2.0) -> dict:
    """
    Bollinger-Bänder
    Gibt dict mit keys: 'upper', 'middle', 'lower'
    """
    mid   = df["Close"].rolling(window=period).mean()
    sd    = df["Close"].rolling(window=period).std()
    upper = mid + std_dev * sd
    lower = mid - std_dev * sd
    return {
        "upper":  upper,
        "middle": mid,
        "lower":  lower
    }


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR)
    """
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Commodity Channel Index (CCI)
    """
    tp     = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad    = tp.rolling(window=period) \
               .apply(lambda x: np.fabs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad)


def stochastic_oscillator(df: pd.DataFrame,
                          k_period: int = 14,
                          d_period: int = 3) -> dict:
    """
    Stochastischer Oszillator
    Gibt dict mit keys: 'percent_k', 'percent_d'
    """
    low_min  = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    percent_k = 100 * ((df["Close"] - low_min) / (high_max - low_min))
    percent_d = percent_k.rolling(window=d_period).mean()
    return {
        "percent_k": percent_k,
        "percent_d": percent_d
    }


def obv(df: pd.DataFrame) -> pd.Series:
    """
    On-Balance Volume (OBV)
    """
    direction = np.sign(df["Close"].diff()).fillna(0)
    return (direction * df["Volume"]).cumsum()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average Directional Index (ADX)
    """
    up = df["High"].diff()
    dn = df["Low"].shift() - df["Low"]
    plus_dm  = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)

    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_series = true_range.rolling(window=period).mean()

    plus_di  = 100 * (plus_dm.rolling(window=period).mean()  / atr_series)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_series)
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100

    return dx.rolling(window=period).mean()
