#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - Celery异步任务配置
"""

from celery import Celery
from config import Config
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery_app = Celery(
    'email_digest',
    broker=Config.CELERY_BROKER_URL,  # Redis消息队列
    backend=Config.CELERY_RESULT_BACKEND,  # Redis结果存储
    include=['services.async_tasks']  # 导入任务定义模块
)

# Celery配置
celery_app.conf.update(
    # 序列化配置
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # 时区配置
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 任务配置
    task_track_started=True,  # 跟踪任务开始状态
    task_time_limit=300,  # 5分钟超时
    task_soft_time_limit=270,  # 4.5分钟软超时(警告)
    
    # Worker配置
    worker_prefetch_multiplier=1,  # 每次只取1个任务(避免阻塞)
    worker_max_tasks_per_child=50,  # 每个worker处理50个任务后重启(防止内存泄漏)
    
    # 结果配置
    result_expires=3600,  # 结果保存1小时后过期
    
    # 重试配置
    task_acks_late=True,  # 任务完成后才确认(防止任务丢失)
    task_reject_on_worker_lost=True,  # Worker崩溃时重新排队任务
    
    # Broker连接重试配置 (解决Celery 6.0兼容性警告)
    broker_connection_retry_on_startup=True,  # 启动时自动重试连接
    
    # 日志配置
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# 配置Celery日志
def setup_celery_logging():
    """配置Celery日志输出到文件"""
    try:
        # 确保日志目录存在
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 获取Celery日志记录器
        celery_logger = logging.getLogger('celery')
        celery_logger.setLevel(logging.INFO)
        
        # 创建日志文件处理器
        today = datetime.now().strftime('%Y_%m_%d')
        log_file = os.path.join(log_dir, f'celery_{today}.log')
        
        # 文件处理器 - 所有日志
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 日志格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        if not celery_logger.handlers:  # 避免重复添加
            celery_logger.addHandler(file_handler)
        
        # 任务日志
        task_logger = logging.getLogger('celery.task')
        if not task_logger.handlers:
            task_logger.addHandler(file_handler)
        
        # Worker日志
        worker_logger = logging.getLogger('celery.worker')
        if not worker_logger.handlers:
            worker_logger.addHandler(file_handler)
        
        logger.info(f"✅ Celery日志已配置: {log_file}")
        
    except Exception as e:
        logger.error(f"❌ 配置Celery日志失败: {e}")

# 初始化日志
setup_celery_logging()

logger.info("Celery应用初始化完成")

