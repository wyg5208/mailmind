#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 配置文件
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    # 应用基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', '6006'))
    
    # Celery异步任务队列配置
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    
    # AI服务配置
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'glm')  # glm, openai, claude
    
    # GLM配置
    GLM_API_KEY = os.getenv('GLM_API_KEY')
    GLM_MODEL = os.getenv('GLM_MODEL', 'glm-4-plus')
    GLM_BASE_URL = os.getenv('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    
    # OpenAI配置（备选）
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    # 邮件服务配置
    EMAIL_PROVIDERS = {
        'gmail': {
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_ssl': True
        },
        '126': {
            'imap_host': 'imap.126.com',
            'imap_port': 993,
            'smtp_host': 'smtp.126.com',
            'smtp_port': 465,  # 126邮箱使用465端口
            'use_ssl': True
        },
        '163': {
            'imap_host': 'imap.163.com',
            'imap_port': 993,
            'smtp_host': 'smtp.163.com',
            'smtp_port': 465,  # 163邮箱使用465端口（与126一致）
            'use_ssl': True
        },
        'qq': {
            'imap_host': 'imap.qq.com',
            'imap_port': 993,
            'smtp_host': 'smtp.qq.com',
            'smtp_port': 587,
            'use_ssl': True
        },
        'hotmail': {
            'imap_host': 'imap-mail.outlook.com',
            'imap_port': 993,
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'use_ssl': True
        },
        'outlook': {
            'imap_host': 'imap-mail.outlook.com',
            'imap_port': 993,
            'smtp_host': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'use_ssl': True
        },
        'yahoo': {
            'imap_host': 'imap.mail.yahoo.com',
            'imap_port': 993,
            'smtp_host': 'smtp.mail.yahoo.com',
            'smtp_port': 587,
            'use_ssl': True
        },
        # 新浪邮箱 - 4种域名后缀
        'sina.com': {
            'imap_host': 'imap.sina.com',
            'imap_port': 993,
            'smtp_host': 'smtp.sina.com',
            'smtp_port': 465,  # SSL端口
            'use_ssl': True
        },
        'sina.cn': {
            'imap_host': 'imap.sina.cn',
            'imap_port': 993,
            'smtp_host': 'smtp.sina.cn',
            'smtp_port': 465,
            'use_ssl': True
        },
        'vip.sina.com': {
            'imap_host': 'imap.vip.sina.com',
            'imap_port': 993,
            'smtp_host': 'smtp.vip.sina.com',
            'smtp_port': 465,
            'use_ssl': True
        },
        'vip.sina.cn': {
            'imap_host': 'imap.vip.sina.cn',
            'imap_port': 993,
            'smtp_host': 'smtp.vip.sina.cn',
            'smtp_port': 465,
            'use_ssl': True
        }
    }
    
    # 调度配置
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '30'))
    MAX_EMAILS_PER_RUN = int(os.getenv('MAX_EMAILS_PER_RUN', '50'))
    MAX_EMAILS_PER_ACCOUNT = int(os.getenv('MAX_EMAILS_PER_ACCOUNT', '30'))
    
    # 数据库配置
    DATABASE_PATH = BASE_DIR / 'data' / 'emails.db'
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'
    LOG_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOG_DIR / 'email_digest.log'
    
    # 安全配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 去重配置
    DUPLICATE_CHECK_DAYS = int(os.getenv('DUPLICATE_CHECK_DAYS', '7'))  # 检查最近7天的邮件去重
    
    # AI摘要配置
    SUMMARY_MAX_LENGTH = int(os.getenv('SUMMARY_MAX_LENGTH', '800'))  # 扩大到800字符，支持智能摘要
    SUMMARY_TEMPERATURE = float(os.getenv('SUMMARY_TEMPERATURE', '0.3'))
    
    # 邮件内容限制
    EMAIL_BODY_MAX_LENGTH = int(os.getenv('EMAIL_BODY_MAX_LENGTH', '20000'))
    EMAIL_SUBJECT_MAX_LENGTH = int(os.getenv('EMAIL_SUBJECT_MAX_LENGTH', '200'))
    
    # Redis缓存配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DECODE_RESPONSES = True
    
    # 缓存配置
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '3600'))  # 1小时
    
    # 缓存TTL配置（秒）
    CACHE_TTL = {
        'email_list': int(os.getenv('CACHE_TTL_EMAIL_LIST', '300')),      # 5分钟
        'user_stats': int(os.getenv('CACHE_TTL_USER_STATS', '600')),      # 10分钟
        'email_detail': int(os.getenv('CACHE_TTL_EMAIL_DETAIL', '3600')), # 1小时
        'digest_list': int(os.getenv('CACHE_TTL_DIGEST_LIST', '1800')),   # 30分钟
        'user_config': int(os.getenv('CACHE_TTL_USER_CONFIG', '7200'))    # 2小时
    }
    
    @classmethod
    def get_email_provider_config(cls, provider_name):
        """获取邮件服务商配置"""
        return cls.EMAIL_PROVIDERS.get(provider_name.lower())
    
    @classmethod
    def detect_email_provider(cls, email_address):
        """根据邮箱地址自动检测服务商"""
        if not email_address or '@' not in email_address:
            return None
            
        domain = email_address.split('@')[1].lower()
        
        # 域名到服务商的映射
        domain_mapping = {
            'gmail.com': 'gmail',
            '126.com': '126',
            '163.com': '163',
            'qq.com': 'qq',
            'hotmail.com': 'hotmail',
            'outlook.com': 'outlook',
            'live.com': 'hotmail',
            'yahoo.com': 'yahoo',
            'yahoo.com.cn': 'yahoo',
            # 新浪邮箱 - 4种域名
            'sina.com': 'sina.com',
            'sina.cn': 'sina.cn',
            'vip.sina.com': 'vip.sina.com',
            'vip.sina.cn': 'vip.sina.cn'
        }
        
        return domain_mapping.get(domain)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    CHECK_INTERVAL_MINUTES = 5  # 开发环境更频繁检查

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    CHECK_INTERVAL_MINUTES = 30

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DATABASE_PATH = BASE_DIR / 'data' / 'test_emails.db'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
