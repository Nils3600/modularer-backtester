# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 13:55:41 2025

@author: hjzfuz
"""

def crosses_above(a, b):
    return (a.shift(1) < b.shift(1)) & (a >= b)

def crosses_below(a, b):
    return (a.shift(1) > b.shift(1)) & (a <= b)

def above(a, b):
    return a > b

def below(a, b):
    return a < b
