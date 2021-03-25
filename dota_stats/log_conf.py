# -*- coding: utf-8 -*-
"""Shared logging routines"""
import os
import sys
import logging


def get_logger(log_name) -> logging.Logger:
    """Setup custom logger for a module."""

    log = logging.getLogger(log_name)
    if int(os.environ['DOTA_LOGGING']) == 0:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.DEBUG)
    streamh = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
    streamh.setFormatter(fmt)
    log.addHandler(streamh)
    return log
