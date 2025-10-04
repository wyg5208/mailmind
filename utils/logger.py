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
            
            # 使用WatchedFileHandler替代TimedRotatingFileHandler
            # 避免多进程环境下的文件轮转冲突(Windows PermissionError)
            # 日志轮转由外部工具(如logrotate或任务计划)处理
            if sys.platform == 'win32':
                # Windows下使用普通FileHandler,避免多进程轮转冲突
                # 可以通过任务计划器配合PowerShell脚本实现日志轮转
                _file_handler = logging.FileHandler(
                    filename=str(Config.LOG_FILE),
                    encoding='utf-8',
                    mode='a'  # 追加模式
                )
            else:
                # Linux/Unix下使用WatchedFileHandler,支持外部日志轮转工具
                _file_handler = logging.handlers.WatchedFileHandler(
                    filename=str(Config.LOG_FILE),
                    encoding='utf-8',
                    mode='a'
                )
            
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
