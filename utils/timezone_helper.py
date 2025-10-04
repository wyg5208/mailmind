#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 时区处理工具
统一使用东八区（中国标准时间）
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

# 东八区时区定义
CHINA_TZ = timezone(timedelta(hours=8))

def now_china() -> datetime:
    """获取当前中国时间"""
    return datetime.now(CHINA_TZ)

def now_china_naive() -> datetime:
    """获取当前中国时间（naive datetime，用于数据库存储）"""
    return datetime.now(CHINA_TZ).replace(tzinfo=None)

def now_china_iso() -> str:
    """获取当前中国时间的ISO格式字符串"""
    return now_china_naive().isoformat()

def to_china_time(dt: Union[datetime, str]) -> datetime:
    """将datetime或ISO字符串转换为中国时间"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"时间字符串解析失败: {dt}, 错误: {e}")
            return now_china_naive()
    
    if dt.tzinfo is None:
        # 如果是naive datetime，假设它是UTC时间
        dt = dt.replace(tzinfo=timezone.utc)
    
    # 转换为中国时间
    china_time = dt.astimezone(CHINA_TZ)
    return china_time.replace(tzinfo=None)  # 返回naive datetime

def format_china_time(dt: Union[datetime, str], format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化中国时间显示"""
    if isinstance(dt, str):
        dt = to_china_time(dt)
    elif dt.tzinfo is None:
        # 假设数据库中的时间已经是中国时间
        pass
    else:
        dt = to_china_time(dt)
    
    return dt.strftime(format_str)

def format_relative_time(dt: Union[datetime, str]) -> str:
    """格式化相对时间显示（多少分钟前、小时前等）"""
    if isinstance(dt, str):
        dt = to_china_time(dt)
    elif dt.tzinfo is None:
        # 假设数据库中的时间已经是中国时间
        pass
    else:
        dt = to_china_time(dt)
    
    now = now_china_naive()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

def parse_email_date(date_str: str) -> datetime:
    """解析邮件日期并转换为中国时间"""
    if not date_str:
        return now_china_naive()
    
    try:
        import email.utils
        # 解析邮件日期
        dt = email.utils.parsedate_to_datetime(date_str)
        # 转换为中国时间
        return to_china_time(dt)
    except Exception as e:
        logger.warning(f"解析邮件日期失败: {date_str}, 错误: {e}")
        return now_china_naive()

def get_china_date_range(days_back: int) -> tuple:
    """获取中国时间的日期范围"""
    end_time = now_china_naive()
    start_time = end_time - timedelta(days=days_back)
    return start_time, end_time

def format_imap_date(dt: datetime) -> str:
    """格式化IMAP搜索使用的日期格式"""
    # IMAP SINCE命令需要 "DD-MMM-YYYY" 格式
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    if dt.tzinfo is None:
        # 假设是中国时间
        china_dt = dt
    else:
        china_dt = to_china_time(dt)
    
    return f"{china_dt.day:02d}-{months[china_dt.month-1]}-{china_dt.year}"

# 模板过滤器函数
def china_datetime_filter(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Jinja2模板过滤器：格式化中国时间"""
    return format_china_time(dt, format_str)

def china_date_filter(dt):
    """Jinja2模板过滤器：格式化中国日期"""
    return format_china_time(dt, '%Y-%m-%d')

def china_time_filter(dt):
    """Jinja2模板过滤器：格式化中国时间"""
    return format_china_time(dt, '%H:%M:%S')

def relative_time_filter(dt):
    """Jinja2模板过滤器：相对时间"""
    return format_relative_time(dt)
