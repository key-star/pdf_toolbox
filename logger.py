#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF工具箱 - 日志模块
记录用户操作行为和程序运行过程，便于问题排查
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

if getattr(sys, 'frozen', False):
    _LOG_DIR = os.path.dirname(sys.executable)
else:
    _LOG_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_LOG_DIR, 'app.log')
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 1

_logger = None


def get_logger():
    global _logger
    if _logger is not None:
        return _logger

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    _logger = logging.getLogger('PDF_Toolbox')
    _logger.setLevel(logging.DEBUG)

    try:
        fh = RotatingFileHandler(
            _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding='utf-8'
        )
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(fmt)
        _logger.addHandler(fh)
    except Exception:
        pass

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    _logger.addHandler(ch)

    return _logger
