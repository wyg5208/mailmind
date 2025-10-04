#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志过滤器 - 过滤不需要的日志消息
"""

import logging
import re

class ExternalRequestFilter(logging.Filter):
    """过滤外部应用的404请求日志"""
    
    def __init__(self):
        super().__init__()
        # 定义需要过滤的路径模式
        self.filter_patterns = [
            r'/study-guide/',
            r'/wp',
            r'/wordpress',
            r'/backup',
            r'/home',
            r'/bk',
            r'/new',
            r'/bc',
            r'/old',
            r'/main',
            r'\.env',
            r'\.php',
            r'/admin',
            r'/phpmyadmin',
            r'/mysql',
            r'/api/v1/(?!emails|user|digests|stats)',  # 只保留我们的API
            r'/device\.rsp',
            r'Sakura\.sh',
            r'/mahu/',
        ]
        
        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern) for pattern in self.filter_patterns]
    
    def filter(self, record):
        """
        过滤日志记录
        返回True表示保留日志，False表示过滤掉
        """
        if not hasattr(record, 'getMessage'):
            return True
            
        message = record.getMessage()
        
        # 只过滤404错误的外部请求
        if '404' not in message:
            return True
        
        # 检查是否匹配过滤模式
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False  # 过滤掉这条日志
        
        return True  # 保留日志

class SecurityRequestFilter(logging.Filter):
    """过滤安全扫描和恶意请求日志"""
    
    def __init__(self):
        super().__init__()
        # 定义安全威胁相关的模式
        self.security_patterns = [
            r'wget.*\.sh',
            r'chmod.*777',
            r'uname\s*-a',
            r'/tmp/',
            r'/var/run/',
            r'/mnt/',
            r'/root/',
            r'history\s*-c',
            r'\.\./',
            r'<script',
            r'javascript:',
            r'eval\(',
            r'base64',
            r'php://input',
            r'data://text',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.security_patterns]
    
    def filter(self, record):
        """过滤安全威胁相关的日志"""
        if not hasattr(record, 'getMessage'):
            return True
            
        message = record.getMessage()
        
        # 检查是否包含安全威胁模式
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False  # 过滤掉安全威胁日志
        
        return True

def setup_log_filters(logger):
    """为日志记录器设置过滤器"""
    # 添加外部请求过滤器
    external_filter = ExternalRequestFilter()
    logger.addFilter(external_filter)
    
    # 添加安全请求过滤器
    security_filter = SecurityRequestFilter()
    logger.addFilter(security_filter)
    
    return logger
