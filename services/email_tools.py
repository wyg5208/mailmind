#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件工具函数定义
用于GLM-4 Function Call功能
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from models.database import Database

logger = logging.getLogger(__name__)


# ============================================================================
# Function Call 工具定义（JSON Schema格式）
# ============================================================================

EMAIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "搜索和筛选邮件。支持按时间、发件人、分类、关键词、重要性等多种条件搜索邮件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": [
                            "today",           # 今天
                            "yesterday",       # 昨天
                            "this_week",       # 本周
                            "last_week",       # 上周
                            "this_month",      # 本月
                            "last_month",      # 上月
                            "recent_3_days",   # 近3天
                            "recent_7_days",   # 近7天
                            "recent_30_days"   # 近30天
                        ],
                        "description": "时间范围。例如：今天用today，近7天用recent_7_days"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["工作", "财务", "社交", "购物", "新闻", "教育", "旅行", "健康", "系统", "广告", "垃圾", "通用"],
                        "description": "邮件分类。包括：工作、财务、社交、购物、新闻、教育、旅行、健康、系统、广告、垃圾、通用等12种分类"
                    },
                    "importance": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5],
                        "description": "重要性等级。1=不重要，2=一般，3=重要，4=很重要，5=非常重要。查询'重要邮件'时使用3或更高"
                    },
                    "sender": {
                        "type": "string",
                        "description": "发件人名称或邮箱地址。支持模糊匹配，例如：'张三'或'zhangsan@example.com'"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索关键词数组。会在主题和正文中搜索这些关键词，例如：['会议', '项目']"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制。默认1000，最大1000。适合统计和分析所有邮件",
                        "default": 1000
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_email_statistics",
            "description": "获取邮件统计信息。可以统计指定时间范围内的邮件数量、分类分布、发件人分布等",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "this_week", "this_month", "recent_7_days", "recent_30_days"],
                        "description": "统计的时间范围"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["category", "sender", "date", "importance"],
                        "description": "分组统计方式。category=按分类统计，sender=按发件人统计，date=按日期统计，importance=按重要性统计",
                        "default": "category"
                    }
                },
                "required": []
            }
        }
    },
]


# ============================================================================
# 工具执行函数
# ============================================================================

def execute_tool(tool_name: str, arguments: Dict, user_id: int) -> Dict:
    """
    执行工具函数
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        user_id: 用户ID
        
    Returns:
        工具执行结果
    """
    logger.info(f"执行工具: {tool_name}, 参数: {arguments}, 用户: {user_id}")
    
    try:
        if tool_name == "search_emails":
            return search_emails(user_id, arguments)
        elif tool_name == "get_email_statistics":
            return get_email_statistics(user_id, arguments)
        else:
            logger.error(f"未知的工具: {tool_name}")
            return {
                'success': False,
                'error': f'未知的工具: {tool_name}'
            }
    except Exception as e:
        logger.error(f"工具执行失败: {tool_name}, 错误: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'工具执行失败: {str(e)}'
        }


def search_emails(user_id: int, params: Dict) -> Dict:
    """
    搜索邮件
    
    Args:
        user_id: 用户ID
        params: 搜索参数
            - time_range: 时间范围（today, yesterday, this_week等）
            - category: 分类
            - importance: 重要性
            - sender: 发件人
            - keywords: 关键词列表
            - is_read: 是否已读
            - limit: 数量限制
    
    Returns:
        搜索结果
    """
    db = Database()
    
    # 构建查询条件
    conditions = ["user_id = ?", "deleted = 0"]
    values = [user_id]
    
    # 1. 时间范围
    time_range = params.get('time_range')
    if time_range:
        time_filter = _build_time_filter(time_range)
        if time_filter:
            conditions.append(time_filter['sql'])
            values.extend(time_filter['params'])
            logger.info(f"时间过滤: {time_range} -> {time_filter['sql']}")
    
    # 2. 分类（支持中英文）
    category = params.get('category')
    if category:
        # 中文到英文的映射（完整的12种分类）
        category_mapping = {
            '工作': 'work',
            '财务': 'finance',
            '社交': 'social',
            '购物': 'shopping',
            '新闻': 'news',
            '教育': 'education',
            '旅行': 'travel',
            '健康': 'health',
            '系统': 'system',
            '广告': 'advertising',
            '垃圾': 'spam',
            '通用': 'general'
        }
        # 如果是中文，转换为英文；如果已经是英文，保持不变
        db_category = category_mapping.get(category, category)
        conditions.append("category = ?")
        values.append(db_category)
        logger.info(f"分类过滤: {category} -> {db_category}")
    
    # 3. 重要性
    importance = params.get('importance')
    if importance:
        conditions.append("importance >= ?")
        values.append(importance)
        logger.info(f"重要性过滤: >= {importance}")
    
    # 4. 发件人
    sender = params.get('sender')
    if sender:
        conditions.append("sender LIKE ?")
        values.append(f"%{sender}%")
        logger.info(f"发件人过滤: {sender}")
    
    # 5. 关键词
    keywords = params.get('keywords')
    if keywords and len(keywords) > 0:
        keyword_conditions = []
        for keyword in keywords:
            keyword_conditions.append("(subject LIKE ? OR body LIKE ?)")
            values.extend([f"%{keyword}%", f"%{keyword}%"])
        conditions.append(f"({' OR '.join(keyword_conditions)})")
        logger.info(f"关键词过滤: {keywords}")
    
    # 6. 数量限制
    limit = params.get('limit', 1000)  # 默认1000，适合统计需求
    limit = min(limit, 1000)  # 最大1000
    
    # 构建SQL
    sql = f"""
        SELECT id, subject, sender, date, category, importance, 
               substr(body, 1, 200) as body_preview
        FROM emails
        WHERE {' AND '.join(conditions)}
        ORDER BY date DESC
        LIMIT ?
    """
    values.append(limit)
    
    logger.info(f"执行SQL: {sql}")
    logger.info(f"参数: {values}")
    
    # 执行查询
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            rows = cursor.fetchall()
            
            emails = []
            for row in rows:
                email = dict(row)
                emails.append({
                    'id': email['id'],
                    'subject': email['subject'],
                    'sender': email['sender'],
                    'date': email['date'],
                    'category': email.get('category', '通用'),
                    'importance': email.get('importance', 2),
                    'body_preview': email.get('body_preview', '')[:200]
                })
            
            logger.info(f"搜索完成，找到 {len(emails)} 封邮件")
            
            return {
                'success': True,
                'count': len(emails),
                'emails': emails,
                'query_params': params
            }
    
    except Exception as e:
        logger.error(f"数据库查询失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'数据库查询失败: {str(e)}',
            'count': 0,
            'emails': []
        }


def get_email_statistics(user_id: int, params: Dict) -> Dict:
    """
    获取邮件统计信息
    
    Args:
        user_id: 用户ID
        params: 统计参数
            - time_range: 时间范围
            - group_by: 分组方式（category, sender, date, importance）
    
    Returns:
        统计结果
    """
    db = Database()
    
    # 构建基础条件
    conditions = ["user_id = ?", "deleted = 0"]
    values = [user_id]
    
    # 时间范围
    time_range = params.get('time_range')
    if time_range:
        time_filter = _build_time_filter(time_range)
        if time_filter:
            conditions.append(time_filter['sql'])
            values.extend(time_filter['params'])
    
    group_by = params.get('group_by', 'category')
    
    # 根据分组方式构建SQL
    if group_by == 'category':
        sql = f"""
            SELECT category, COUNT(*) as count
            FROM emails
            WHERE {' AND '.join(conditions)}
            GROUP BY category
            ORDER BY count DESC
        """
    elif group_by == 'sender':
        sql = f"""
            SELECT sender, COUNT(*) as count
            FROM emails
            WHERE {' AND '.join(conditions)}
            GROUP BY sender
            ORDER BY count DESC
            LIMIT 20
        """
    elif group_by == 'date':
        sql = f"""
            SELECT DATE(date) as date, COUNT(*) as count
            FROM emails
            WHERE {' AND '.join(conditions)}
            GROUP BY DATE(date)
            ORDER BY date DESC
            LIMIT 30
        """
    elif group_by == 'importance':
        sql = f"""
            SELECT importance, COUNT(*) as count
            FROM emails
            WHERE {' AND '.join(conditions)}
            GROUP BY importance
            ORDER BY importance DESC
        """
    else:
        return {
            'success': False,
            'error': f'不支持的分组方式: {group_by}'
        }
    
    # 英文到中文的映射（用于返回结果，完整的12种分类）
    category_names = {
        'work': '工作',
        'finance': '财务',
        'social': '社交',
        'shopping': '购物',
        'news': '新闻',
        'education': '教育',
        'travel': '旅行',
        'health': '健康',
        'system': '系统',
        'advertising': '广告',
        'spam': '垃圾',
        'general': '通用'
    }
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            rows = cursor.fetchall()
            
            statistics = []
            total = 0
            for row in rows:
                item = dict(row)
                # 如果按分类分组，将英文分类转换为中文
                if group_by == 'category' and 'category' in item:
                    eng_category = item['category']
                    item['category'] = category_names.get(eng_category, eng_category)
                    logger.info(f"分类映射: {eng_category} -> {item['category']}")
                statistics.append(item)
                total += item['count']
            
            logger.info(f"统计完成: {group_by}, 总数: {total}")
            
            return {
                'success': True,
                'group_by': group_by,
                'time_range': time_range,
                'total': total,
                'statistics': statistics
            }
    
    except Exception as e:
        logger.error(f"统计查询失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'统计查询失败: {str(e)}'
        }




# ============================================================================
# 辅助函数
# ============================================================================

def _build_time_filter(time_range: str) -> Optional[Dict]:
    """
    构建时间过滤条件
    
    Args:
        time_range: 时间范围字符串（today, yesterday, this_week等）
    
    Returns:
        SQL过滤条件和参数
    """
    now = datetime.now()
    
    if time_range == "today":
        # 今天00:00:00开始
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    elif time_range == "yesterday":
        # 昨天00:00:00到今天00:00:00
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        return {
            'sql': "(date >= ? AND date < ?)",
            'params': [
                yesterday_start.strftime('%Y-%m-%d %H:%M:%S'),
                today_start.strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
    
    elif time_range == "this_week":
        # 本周一00:00:00开始
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [week_start.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    elif time_range == "last_week":
        # 上周一到本周一
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_start = this_week_start - timedelta(days=7)
        return {
            'sql': "(date >= ? AND date < ?)",
            'params': [
                last_week_start.strftime('%Y-%m-%d %H:%M:%S'),
                this_week_start.strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
    
    elif time_range == "this_month":
        # 本月1号00:00:00开始
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [month_start.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    elif time_range == "last_month":
        # 上月1号到本月1号
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 计算上月
        if now.month == 1:
            last_month_start = this_month_start.replace(year=now.year-1, month=12)
        else:
            last_month_start = this_month_start.replace(month=now.month-1)
        return {
            'sql': "(date >= ? AND date < ?)",
            'params': [
                last_month_start.strftime('%Y-%m-%d %H:%M:%S'),
                this_month_start.strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
    
    elif time_range == "recent_3_days":
        # 近3天（包括今天）
        start_time = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    elif time_range == "recent_7_days":
        # 近7天（包括今天）
        start_time = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    elif time_range == "recent_30_days":
        # 近30天（包括今天）
        start_time = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            'sql': "date >= ?",
            'params': [start_time.strftime('%Y-%m-%d %H:%M:%S')]
        }
    
    else:
        logger.warning(f"未知的时间范围: {time_range}")
        return None

