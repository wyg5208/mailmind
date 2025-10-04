#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 日志工具
"""

import logging
import logging.handlers
import os
import re
import sys
from pathlib import Path
from datetime import datetime
import threading

from config import Config

# 全局文件处理器单例
_file_handler = None
_handler_lock = threading.Lock()

def get_shared_file_handler():
    """获取共享的文件处理器单例"""
    global _file_handler
    
    if _file_handler is not None:
        return _file_handler
    
    with _handler_lock:
        # 双重检查锁定
        if _file_handler is not None:
            return _file_handler
        
        try:
            # 确保日志目录存在
            Config.LOG_DIR.mkdir(exist_ok=True)
            
            # 文件日志格式化器（移除ANSI/ESC转义序列）
            ANSI_ESCAPE_RE = re.compile(r'(?:\x1B[@-Z\\-_]|\x1B\[[0-?]*[ -/]*[@-~])')
            class CleanFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    message = super().format(record)
                    # 移除ANSI颜色转义及ESC字符，避免日志中出现 "ESC[" 等内容
                    message = ANSI_ESCAPE_RE.sub('', message)
                    # 额外兜底去除孤立ESC字符
                    message = message.replace('\x1b', '')
                    return message
            
            file_formatter = CleanFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 基于本地时间在午夜轮转，保留最近30天
            _file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(Config.LOG_FILE),
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8',
                utc=False
            )

            # 自定义命名：email_digest_YYYY_MM_DD.log（将默认的 .YYYY-MM-DD 改写为 _YYYY_MM_DD.log）
            _file_handler.suffix = "%Y-%m-%d"
            base_name = Config.LOG_FILE.stem  # e.g. 'email_digest'
            def _namer(default_name: str) -> str:
                # default_name 示例：logs/email_digest.log.2025-10-01
                directory = os.path.dirname(default_name)
                date_part = default_name.rsplit('.', 1)[-1].replace('-', '_')
                return os.path.join(directory, f"{base_name}_{date_part}.log")
            _file_handler.namer = _namer

            _file_handler.setLevel(logging.DEBUG)
            _file_handler.setFormatter(file_formatter)
            
            print(f"[日志系统] 创建共享文件处理器: {Config.LOG_FILE}")
            
        except Exception as e:
            print(f"[日志系统] 创建文件日志处理器失败: {e}")
            _file_handler = None
        
        return _file_handler

def setup_logger(name: str) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建控制台格式化器
    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 添加共享的文件处理器
    shared_file_handler = get_shared_file_handler()
    if shared_file_handler:
        logger.addHandler(shared_file_handler)
        print(f"[日志系统] Logger '{name}' 已连接到共享文件处理器")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return setup_logger(name)

def add_handler_to_logger(logger, handler_name="shared_file"):
    """为现有logger添加共享文件处理器"""
    shared_handler = get_shared_file_handler()
    if shared_handler and not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in logger.handlers):
        logger.addHandler(shared_handler)
        print(f"[日志系统] 为现有Logger '{logger.name}' 添加了共享文件处理器")
