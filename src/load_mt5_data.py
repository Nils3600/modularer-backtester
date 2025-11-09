# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 14:46:22 2025

@author: hjzfuz
"""
import pandas as pd

class load_data():
    
    def __init__(self):
        self.filepath = ''
    
    def metatrader_csv(filepath):
        df = pd.read_csv(
            filepath,
            sep="\t",
            names=["Date", "Time", "Open", "High", "Low", "Close", "TickVol", "Vol", "Spread"],
            header=None,
            skiprows=1,
            engine='python'
        )
        
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df.set_index("DateTime", inplace=True)
        df.drop(['Date', 'Time'], axis=1, inplace=True)  # Aufräumen
        return df[["Open", "High", "Low", "Close", "TickVol", "Vol", "Spread"]]
        
        