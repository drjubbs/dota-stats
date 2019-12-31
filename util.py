"""Utility functions and shared configuration between elements
"""
import logging
import sys

# Binary hero encoding (local DB mode)
def encode_heroes(hero_list):
    low_mask=0
    high_mask=0

    for t in [hero-1 for hero in hero_list]:
        if t<=63:
            low_mask=low_mask | 2**t
        else:
            t=t-63
            high_mask=high_mask | 2**t

    return(low_mask, high_mask)

def decode_heroes(low_mask, high_mask):

    hero_list=[]
    for i in range(64):
        if 2**i & low_mask:
            hero_list.append(i+1)

    for i in range(64):
        if 2**i & high_mask:
            hero_list.append(i+64)

    return(hero_list)

