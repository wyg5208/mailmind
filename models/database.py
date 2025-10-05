#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 数据库模型
"""

import sqlite3
from datetime import datetime, timedelta
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

from config import Config

logger = logging.getLogger(__name__)

# 延迟导入缓存服务，避免循环导入
def get_cache_service():
    """延迟获取缓存服务"""
    try:
        from services.cache_service import cache_service
        return cache_service
    except ImportError:
        return None

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # 支持字典式访问
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.get_connection() as conn:
                conn.execute('SELECT 1')
                return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建邮件表（添加用户关联和附件支持）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS emails (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        email_id TEXT UNIQUE,
                        content_hash TEXT UNIQUE,
                        subject TEXT,
                        sender TEXT,
                        recipients TEXT,
                        date TEXT,
                        body TEXT,
                        body_html TEXT,
                        summary TEXT,
                        ai_summary TEXT,
                        processed BOOLEAN DEFAULT 0,
                        account_email TEXT,
                        provider TEXT,
                        importance INTEGER DEFAULT 1,
                        category TEXT,
                        attachments TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # 创建系统通知表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # 为通知表创建索引
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
                    ON system_notifications(user_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
                    ON system_notifications(created_at DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_notifications_is_read 
                    ON system_notifications(is_read)
                ''')
                
                # 创建简报表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS digests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        title TEXT,
                        content TEXT,
                        email_count INTEGER,
                        summary TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建邮箱账户表（修改为支持用户关联）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS email_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT,
                        provider TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        last_check TEXT,
                        total_emails INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE(user_id, email)
                    )
                ''')
                
                # 创建系统配置表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建用户配置表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE(user_id, key)
                    )
                ''')
                
                # 创建用户表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        full_name TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        is_admin BOOLEAN DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        last_login TEXT
                    )
                ''')
                
                # 创建用户会话表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        expires_at TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(processed)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_content_hash ON emails(content_hash)')
                
                # 数据库迁移：为现有emails表添加attachments字段
                try:
                    cursor.execute('ALTER TABLE emails ADD COLUMN attachments TEXT')
                    logger.info("成功为emails表添加attachments字段")
                except Exception as e:
                    # 字段已存在或其他错误，忽略
                    if "duplicate column name" not in str(e).lower():
                        logger.debug(f"添加attachments字段时的预期错误: {e}")
                    pass
                
                # 数据库迁移：为现有emails表添加转发相关字段
                forward_fields = [
                    ('is_forwarded', 'BOOLEAN DEFAULT 0'),
                    ('forward_level', 'INTEGER DEFAULT 0'),
                    ('original_sender', 'TEXT'),
                    ('original_sender_email', 'TEXT'),
                    ('forwarded_by', 'TEXT'),
                    ('forwarded_by_email', 'TEXT'),
                    ('forward_chain', 'TEXT'),
                ]
                
                for field_name, field_type in forward_fields:
                    try:
                        cursor.execute(f'ALTER TABLE emails ADD COLUMN {field_name} {field_type}')
                        logger.info(f"成功为emails表添加{field_name}字段")
                    except Exception as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.debug(f"添加{field_name}字段时的预期错误: {e}")
                        pass
                
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_account ON emails(account_email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_digests_date ON digests(date)')
                
                # 转发相关索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_is_forwarded ON emails(is_forwarded)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_original_sender_email ON emails(original_sender_email)')
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def generate_content_hash(self, email_data: Dict) -> str:
        """
        生成邮件内容哈希用于去重（增强版）
        
        策略改进:
        1. 增加邮件日期作为区分因素
        2. 扩大正文检查范围到2000字符
        3. 包含收件人信息(防止群发邮件误判)
        4. 对于发票等模板邮件提供更好的区分度
        """
        # 基础内容
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')[:2000]  # 从1000扩展到2000
        
        # 邮件时间戳（精确到秒，提供时间维度的区分）
        email_date = email_data.get('date')
        date_str = ''
        if email_date:
            if hasattr(email_date, 'isoformat'):
                date_str = email_date.isoformat()
            else:
                date_str = str(email_date)
        
        # 收件人信息（防止相同内容发给不同人被误判）
        recipients = email_data.get('recipients', [])
        recipients_str = ','.join(recipients) if isinstance(recipients, list) else str(recipients)
        
        # 组合所有信息生成hash
        content = f"{subject}|{sender}|{date_str}|{recipients_str}|{body}"
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def deduplicate_emails(self, emails: List[Dict], user_id: int = None) -> List[Dict]:
        """
        邮件去重处理（混合策略 - 修复简报重复问题）
        - 短期: content_hash去重(30天窗口,快速)
        - 长期: email_id去重(永久记录,准确)
        """
        if not emails:
            return []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    # 策略1: 获取所有已处理的email_id(永久,精确去重 - 解决简报重复问题)
                    cursor.execute('''
                        SELECT email_id FROM emails 
                        WHERE user_id = ?
                    ''', (user_id,))
                    existing_email_ids = {row['email_id'] for row in cursor.fetchall()}
                    
                    # 策略2: 获取最近N天的content_hash(时间窗口,内容去重)
                    user_configs = self.get_user_configs(user_id)
                    check_days = int(user_configs.get('duplicate_check_days', '30'))  # 增加到30天
                    check_date = (datetime.now() - timedelta(days=check_days)).isoformat()
                    
                    cursor.execute('''
                        SELECT content_hash FROM emails 
                        WHERE user_id = ? AND (created_at > ? OR updated_at > ?)
                    ''', (user_id, check_date, check_date))
                    existing_hashes = {row['content_hash'] for row in cursor.fetchall()}
                    
                    logger.debug(f"用户 {user_id} 去重基准: {len(existing_email_ids)} 个email_id(全部), "
                               f"{len(existing_hashes)} 个content_hash({check_days}天)")
                else:
                    # 管理员或全局去重
                    check_days = Config.DUPLICATE_CHECK_DAYS
                    check_date = (datetime.now() - timedelta(days=check_days)).isoformat()
                    
                    cursor.execute('''
                        SELECT email_id, content_hash FROM emails 
                        WHERE created_at > ? OR updated_at > ?
                    ''', (check_date, check_date))
                    
                    results = cursor.fetchall()
                    existing_email_ids = {row['email_id'] for row in results}
                    existing_hashes = {row['content_hash'] for row in results}
                    logger.debug("全局去重：与所有用户邮件比较")
                
                # 过滤重复邮件
                unique_emails = []
                current_email_ids = set()
                current_hashes = set()
                
                duplicate_count = {'email_id': 0, 'content_hash': 0, 'batch': 0}
                
                for email in emails:
                    email_id = email.get('email_id')
                    content_hash = self.generate_content_hash(email)
                    email['content_hash'] = content_hash
                    
                    # 检查1: email_id重复(最准确 - 防止简报重复)
                    if email_id and (email_id in existing_email_ids or email_id in current_email_ids):
                        duplicate_count['email_id'] += 1
                        logger.debug(f"用户 {user_id} email_id重复: {email.get('subject', '')[:30]}")
                        continue
                    
                    # 检查2: content_hash重复(防止内容重复)
                    if content_hash in existing_hashes or content_hash in current_hashes:
                        duplicate_count['content_hash'] += 1
                        logger.debug(f"用户 {user_id} content_hash重复: {email.get('subject', '')[:30]}")
                        continue
                    
                    unique_emails.append(email)
                    if email_id:
                        current_email_ids.add(email_id)
                    current_hashes.add(content_hash)
                
                if user_id:
                    logger.info(f"用户 {user_id} 去重: {len(emails)} -> {len(unique_emails)} "
                               f"(email_id重复:{duplicate_count['email_id']}, "
                               f"content重复:{duplicate_count['content_hash']})")
                else:
                    logger.info(f"去重处理: {len(emails)} -> {len(unique_emails)}")
                
                return unique_emails
                
        except Exception as e:
            logger.error(f"邮件去重失败: {e}")
            return emails  # 出错时返回原始邮件列表
    
    def _normalize_email_date(self, date_obj) -> str:
        """
        规范化邮件日期为UTC时间字符串(无时区信息)
        
        目的: 
        1. 避免不同时区导致的SQLite字符串排序混乱
        2. 解决转发邮件(UTC)和本地邮件(UTC+8)混合导致的简报重复问题
        
        示例:
        - 输入: 2025-10-01T10:00:00+08:00 → 输出: 2025-10-01T02:00:00
        - 输入: 2025-09-15T10:00:00+00:00 → 输出: 2025-09-15T10:00:00
        """
        if not date_obj:
            return datetime.utcnow().replace(tzinfo=None).isoformat()
        
        try:
            # 如果有时区信息，转换为UTC
            if hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
                from datetime import timezone
                utc_date = date_obj.astimezone(timezone.utc)
                # 移除时区信息，只保留UTC时间
                return utc_date.replace(tzinfo=None).isoformat()
            else:
                # 假设是本地时间，直接使用
                return date_obj.isoformat()
        except Exception as e:
            logger.warning(f"规范化邮件日期失败: {e}")
            return datetime.utcnow().replace(tzinfo=None).isoformat()
    
    def save_email(self, email_data: Dict) -> bool:
        """保存邮件到数据库"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 确保有内容哈希
                if 'content_hash' not in email_data:
                    email_data['content_hash'] = self.generate_content_hash(email_data)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO emails 
                    (user_id, email_id, content_hash, subject, sender, recipients, date, body, body_html, 
                     summary, ai_summary, processed, account_email, provider, importance, 
                     category, attachments, 
                     is_forwarded, forward_level, original_sender, original_sender_email, 
                     forwarded_by, forwarded_by_email, forward_chain, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_data.get('user_id'),
                    email_data.get('email_id'),
                    email_data.get('content_hash'),
                    email_data.get('subject', '')[:Config.EMAIL_SUBJECT_MAX_LENGTH],
                    email_data.get('sender', ''),
                    json.dumps(email_data.get('recipients', [])),
                    self._normalize_email_date(email_data.get('date')),  # ✅ 统一时区保存
                    email_data.get('body', '')[:Config.EMAIL_BODY_MAX_LENGTH],
                    email_data.get('body_html', ''),
                    email_data.get('summary', ''),
                    email_data.get('ai_summary', ''),
                    email_data.get('processed', False),
                    email_data.get('account_email', ''),
                    email_data.get('provider', ''),
                    email_data.get('importance', 1),
                    email_data.get('category', 'general'),
                    json.dumps(email_data.get('attachments', [])),
                    # 转发相关字段
                    email_data.get('is_forwarded', False),
                    email_data.get('forward_level', 0),
                    email_data.get('original_sender'),
                    email_data.get('original_sender_email'),
                    email_data.get('forwarded_by'),
                    email_data.get('forwarded_by_email'),
                    email_data.get('forward_chain'),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
                # 缓存失效
                user_id = email_data.get('user_id')
                if user_id:
                    cache = get_cache_service()
                    if cache and cache.is_connected():
                        cache.invalidate_user_cache(user_id, 'new_email')
                
                return True
                
        except Exception as e:
            logger.error(f"保存邮件失败: {e}")
            return False
    
    def get_processed_email_ids(self, account_email: str = None) -> set:
        """获取已处理的邮件ID集合"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if account_email:
                    cursor.execute('''
                        SELECT email_id FROM emails 
                        WHERE processed = 1 AND account_email = ?
                    ''', (account_email,))
                else:
                    cursor.execute('SELECT email_id FROM emails WHERE processed = 1')
                
                return {row['email_id'] for row in cursor.fetchall()}
                
        except Exception as e:
            logger.error(f"获取已处理邮件ID失败: {e}")
            return set()
    
    def get_latest_digest(self) -> Optional[Dict]:
        """获取最新简报（管理员用）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, date, title, content, email_count, summary, created_at 
                    FROM digests 
                    ORDER BY date DESC, created_at DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result['id'],
                        'date': result['date'],
                        'title': result['title'],
                        'content': json.loads(result['content']) if result['content'] else {},
                        'email_count': result['email_count'],
                        'summary': result['summary'],
                        'created_at': result['created_at']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取最新简报失败: {e}")
            return None
    
    def get_user_latest_digest(self, user_id: int) -> Optional[Dict]:
        """获取用户最新简报"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, date, title, content, email_count, summary, created_at 
                    FROM digests 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (user_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result['id'],
                        'date': result['date'],
                        'title': result['title'],
                        'content': json.loads(result['content']) if result['content'] else {},
                        'email_count': result['email_count'],
                        'summary': result['summary'],
                        'created_at': result['created_at']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户最新简报失败: {e}")
            return None
    
    def save_digest(self, digest_data: Dict, user_id: int = None) -> bool:
        """保存简报到数据库（使用UTC时间）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取或生成UTC时间
                from datetime import timezone
                digest_date = digest_data.get('date')
                if digest_date:
                    # 如果传入的date是datetime对象，确保转换为UTC
                    if hasattr(digest_date, 'isoformat'):
                        if hasattr(digest_date, 'tzinfo') and digest_date.tzinfo is not None:
                            # 有时区信息，转换为UTC
                            digest_date_str = digest_date.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
                        else:
                            # 无时区信息，假设已经是UTC
                            digest_date_str = digest_date.isoformat()
                    else:
                        digest_date_str = str(digest_date)
                else:
                    # 没有date，使用当前UTC时间
                    digest_date_str = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                
                cursor.execute('''
                    INSERT INTO digests (user_id, date, title, content, email_count, summary)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    digest_date_str,
                    digest_data.get('title', f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} 邮件简报"),
                    json.dumps(digest_data.get('content', {}), ensure_ascii=False),
                    digest_data.get('email_count', 0),
                    digest_data.get('summary', '')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存简报失败: {e}")
            return False
    
    def get_emails_paginated(self, page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """分页获取邮件列表（管理员用）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取总数
                cursor.execute('SELECT COUNT(*) as total FROM emails')
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute('''
                    SELECT id, subject, sender, date, summary, ai_summary, processed, 
                           account_email, provider, importance, category, created_at
                    FROM emails
                    ORDER BY date DESC, created_at DESC
                    LIMIT ? OFFSET ?
                ''', (per_page, offset))
                
                emails = []
                for row in cursor.fetchall():
                    emails.append({
                        'id': row['id'],
                        'subject': row['subject'],
                        'sender': row['sender'],
                        'date': row['date'],
                        'summary': row['summary'],
                        'ai_summary': row['ai_summary'],
                        'processed': bool(row['processed']),
                        'account_email': row['account_email'],
                        'provider': row['provider'],
                        'importance': row['importance'],
                        'category': row['category'],
                        'created_at': row['created_at']
                    })
                
                return emails, total
                
        except Exception as e:
            logger.error(f"获取分页邮件失败: {e}")
            return [], 0
    
    def get_user_emails_paginated(self, user_id: int, page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """分页获取用户邮件列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取用户邮件总数
                cursor.execute('SELECT COUNT(*) as total FROM emails WHERE user_id = ?', (user_id,))
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute('''
                    SELECT id, subject, sender, date, summary, ai_summary, processed, 
                           account_email, provider, importance, category, created_at
                    FROM emails
                    WHERE user_id = ?
                    ORDER BY date DESC, created_at DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, per_page, offset))
                
                emails = []
                for row in cursor.fetchall():
                    emails.append({
                        'id': row['id'],
                        'subject': row['subject'],
                        'sender': row['sender'],
                        'date': row['date'],
                        'summary': row['summary'],
                        'ai_summary': row['ai_summary'],
                        'processed': bool(row['processed']),
                        'account_email': row['account_email'],
                        'provider': row['provider'],
                        'importance': row['importance'],
                        'category': row['category'],
                        'created_at': row['created_at']
                    })
                
                return emails, total
                
        except Exception as e:
            logger.error(f"获取用户分页邮件失败: {e}")
            return [], 0
    
    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 邮件统计
                cursor.execute('SELECT COUNT(*) as total FROM emails')
                total_emails = cursor.fetchone()['total']
                
                cursor.execute('SELECT COUNT(*) as processed FROM emails WHERE processed = 1')
                processed_emails = cursor.fetchone()['processed']
                
                cursor.execute('SELECT COUNT(*) as today FROM emails WHERE date(date) = date("now")')
                today_emails = cursor.fetchone()['today']
                
                # 账户统计
                cursor.execute('SELECT COUNT(*) as accounts FROM email_accounts WHERE is_active = 1')
                active_accounts = cursor.fetchone()['accounts']
                
                # 简报统计
                cursor.execute('SELECT COUNT(*) as digests FROM digests')
                total_digests = cursor.fetchone()['digests']
                
                # 最近活动
                cursor.execute('''
                    SELECT date, COUNT(*) as count 
                    FROM emails 
                    WHERE date >= date("now", "-7 days")
                    GROUP BY date(date)
                    ORDER BY date DESC
                    LIMIT 7
                ''')
                recent_activity = [{'date': row['date'], 'count': row['count']} for row in cursor.fetchall()]
                
                return {
                    'total_emails': total_emails,
                    'processed_emails': processed_emails,
                    'today_emails': today_emails,
                    'active_accounts': active_accounts,
                    'total_digests': total_digests,
                    'recent_activity': recent_activity,
                    'processing_rate': round(processed_emails / total_emails * 100, 2) if total_emails > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {
                'total_emails': 0,
                'processed_emails': 0,
                'today_emails': 0,
                'active_accounts': 0,
                'total_digests': 0,
                'recent_activity': [],
                'processing_rate': 0
            }
    
    def save_email_account(self, email: str, password: str, provider: str) -> bool:
        """保存邮箱账户配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO email_accounts 
                    (email, password, provider, is_active, updated_at)
                    VALUES (?, ?, ?, 1, ?)
                ''', (email, password, provider, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存邮箱账户失败: {e}")
            return False
    
    def get_email_accounts(self) -> List[Dict]:
        """获取所有邮箱账户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, email, provider, is_active, last_check, total_emails, created_at
                    FROM email_accounts
                    ORDER BY created_at DESC
                ''')
                
                accounts = []
                for row in cursor.fetchall():
                    accounts.append({
                        'id': row['id'],
                        'email': row['email'],
                        'provider': row['provider'],
                        'is_active': bool(row['is_active']),
                        'last_check': row['last_check'],
                        'total_emails': row['total_emails'],
                        'created_at': row['created_at']
                    })
                
                return accounts
                
        except Exception as e:
            logger.error(f"获取邮箱账户失败: {e}")
            return []
    
    def get_email_by_id(self, email_id: int) -> Optional[Dict]:
        """根据ID获取邮件详情"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, email_id, content_hash, subject, sender, recipients, 
                           date, body, body_html, summary, ai_summary, processed, 
                           account_email, provider, importance, category, attachments,
                           is_forwarded, forward_level, original_sender, original_sender_email,
                           forwarded_by, forwarded_by_email, forward_chain,
                           created_at, updated_at, deleted
                    FROM emails
                    WHERE id = ?
                ''', (email_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'email_id': row['email_id'],
                        'content_hash': row['content_hash'],
                        'subject': row['subject'],
                        'sender': row['sender'],
                        'recipients': json.loads(row['recipients']) if row['recipients'] else [],
                        'date': row['date'],
                        'body': row['body'],
                        'body_html': row['body_html'],
                        'summary': row['summary'],
                        'ai_summary': row['ai_summary'],
                        'processed': bool(row['processed']),
                        'account_email': row['account_email'],
                        'provider': row['provider'],
                        'importance': row['importance'],
                        'category': row['category'],
                        'attachments': json.loads(row['attachments']) if row['attachments'] else [],
                        # 转发相关字段
                        'is_forwarded': bool(row['is_forwarded']) if row['is_forwarded'] is not None else False,
                        'forward_level': row['forward_level'] or 0,
                        'original_sender': row['original_sender'],
                        'original_sender_email': row['original_sender_email'],
                        'forwarded_by': row['forwarded_by'],
                        'forwarded_by_email': row['forwarded_by_email'],
                        'forward_chain': json.loads(row['forward_chain']) if row['forward_chain'] else None,
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'deleted': bool(row['deleted']) if row['deleted'] is not None else False
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取邮件详情失败: {e}")
            return None
    
    def update_email_summary(self, email_id: int, ai_summary: str) -> bool:
        """更新邮件AI摘要"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE emails 
                    SET ai_summary = ?, processed = 1, updated_at = ?
                    WHERE id = ?
                ''', (ai_summary, datetime.now().isoformat(), email_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新邮件摘要失败: {e}")
            return False
    
    def get_email_translation(self, email_id: int, target_language: str) -> Optional[str]:
        """获取邮件翻译结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查翻译字段是否存在
                cursor.execute("PRAGMA table_info(emails)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if target_language == 'chinese':
                    if 'body_chinese_translation' not in columns:
                        return None
                    cursor.execute('SELECT body_chinese_translation FROM emails WHERE id = ?', (email_id,))
                elif target_language == 'english':
                    if 'body_english_translation' not in columns:
                        return None
                    cursor.execute('SELECT body_english_translation FROM emails WHERE id = ?', (email_id,))
                else:
                    return None
                
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
                
        except Exception as e:
            logger.error(f"获取邮件翻译失败: {e}")
            return None
    
    def save_email_translation(self, email_id: int, target_language: str, translated_text: str) -> bool:
        """保存邮件翻译结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查翻译字段是否存在，如果不存在则添加
                cursor.execute("PRAGMA table_info(emails)")
                columns = [row[1] for row in cursor.fetchall()]
                
                translation_columns = {
                    'body_chinese_translation': 'body_chinese_translation TEXT',
                    'body_english_translation': 'body_english_translation TEXT',
                    'translation_updated_at': 'translation_updated_at TEXT'
                }
                
                # 添加缺失的翻译字段
                for col_name, col_def in translation_columns.items():
                    if col_name not in columns:
                        cursor.execute(f'ALTER TABLE emails ADD COLUMN {col_def}')
                        logger.info(f"为emails表添加翻译字段: {col_name}")
                
                # 保存翻译结果
                current_time = datetime.now().isoformat()
                
                if target_language == 'chinese':
                    cursor.execute('''
                        UPDATE emails 
                        SET body_chinese_translation = ?, translation_updated_at = ?, updated_at = ?
                        WHERE id = ?
                    ''', (translated_text, current_time, current_time, email_id))
                elif target_language == 'english':
                    cursor.execute('''
                        UPDATE emails 
                        SET body_english_translation = ?, translation_updated_at = ?, updated_at = ?
                        WHERE id = ?
                    ''', (translated_text, current_time, current_time, email_id))
                else:
                    return False
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"邮件翻译已保存: email_id={email_id}, language={target_language}")
                
                return success
                
        except Exception as e:
            logger.error(f"保存邮件翻译失败: {e}")
            return False
    
    def clear_email_translations(self, email_id: int) -> bool:
        """清除邮件的所有翻译结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查翻译字段是否存在
                cursor.execute("PRAGMA table_info(emails)")
                columns = [row[1] for row in cursor.fetchall()]
                
                update_fields = []
                if 'body_chinese_translation' in columns:
                    update_fields.append('body_chinese_translation = NULL')
                if 'body_english_translation' in columns:
                    update_fields.append('body_english_translation = NULL')
                if 'translation_updated_at' in columns:
                    update_fields.append('translation_updated_at = NULL')
                
                if not update_fields:
                    return True  # 没有翻译字段，视为成功
                
                sql = f'''
                    UPDATE emails 
                    SET {', '.join(update_fields)}, updated_at = ?
                    WHERE id = ?
                '''
                
                cursor.execute(sql, (datetime.now().isoformat(), email_id))
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"清除邮件翻译失败: {e}")
            return False
    
    # 用户管理相关方法
    def create_user(self, username: str, email: str, password_hash: str, full_name: str = None) -> Optional[int]:
        """创建新用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, full_name)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, full_name))
                
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                logger.warning(f"用户名已存在: {username}")
            elif 'email' in str(e):
                logger.warning(f"邮箱已存在: {email}")
            return None
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名获取用户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, password_hash, full_name, 
                           is_active, is_admin, created_at, last_login
                    FROM users
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'username': row['username'],
                        'email': row['email'],
                        'password_hash': row['password_hash'],
                        'full_name': row['full_name'],
                        'is_active': bool(row['is_active']),
                        'is_admin': bool(row['is_admin']),
                        'created_at': row['created_at'],
                        'last_login': row['last_login']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱获取用户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, password_hash, full_name, 
                           is_active, is_admin, created_at, last_login
                    FROM users
                    WHERE email = ? AND is_active = 1
                ''', (email,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'username': row['username'],
                        'email': row['email'],
                        'password_hash': row['password_hash'],
                        'full_name': row['full_name'],
                        'is_active': bool(row['is_active']),
                        'is_admin': bool(row['is_admin']),
                        'created_at': row['created_at'],
                        'last_login': row['last_login']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def update_user_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_login = ?, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), datetime.now().isoformat(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新用户登录时间失败: {e}")
            return False
    
    def create_user_session(self, user_id: int, session_token: str, expires_at: datetime) -> bool:
        """创建用户会话"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, session_token, expires_at.isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"创建用户会话失败: {e}")
            return False
    
    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """根据会话令牌获取用户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.id, u.username, u.email, u.full_name, u.is_active, u.is_admin,
                           s.expires_at
                    FROM users u
                    JOIN user_sessions s ON u.id = s.user_id
                    WHERE s.session_token = ? AND u.is_active = 1
                    AND datetime(s.expires_at) > datetime('now')
                ''', (session_token,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'username': row['username'],
                        'email': row['email'],
                        'full_name': row['full_name'],
                        'is_active': bool(row['is_active']),
                        'is_admin': bool(row['is_admin']),
                        'expires_at': row['expires_at']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return None
    
    def delete_user_session(self, session_token: str) -> bool:
        """删除用户会话"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除用户会话失败: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE datetime(expires_at) <= datetime('now')
                ''')
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
    
    def get_user_stats(self, user_id: int) -> Dict:
        """获取用户统计信息 - 支持Redis缓存"""
        cache = get_cache_service()
        
        # 尝试从缓存获取
        cache_key = None
        if cache and cache.is_connected():
            cache_key = cache.generate_cache_key('stats:user', user_id)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"用户统计缓存命中: user_id={user_id}")
                return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 优化：使用一个查询获取多个统计信息
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
                
                # 主要统计查询
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_emails,
                        SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed_emails,
                        SUM(CASE WHEN date >= ? AND date <= ? THEN 1 ELSE 0 END) as today_emails
                    FROM emails 
                    WHERE user_id = ? AND (deleted IS NULL OR deleted = 0)
                ''', (today_start, today_end, user_id))
                
                email_stats = cursor.fetchone()
                total_emails = email_stats['total_emails']
                processed_emails = email_stats['processed_emails']
                today_emails = email_stats['today_emails']
                
                # 用户邮箱账户统计
                cursor.execute('SELECT COUNT(*) as accounts FROM email_accounts WHERE user_id = ? AND is_active = 1', (user_id,))
                email_accounts = cursor.fetchone()['accounts']
                
                # 用户简报统计
                cursor.execute('SELECT COUNT(*) as digests FROM digests WHERE user_id = ?', (user_id,))
                total_digests = cursor.fetchone()['digests']
                
                # 用户最近活动（最近7天）
                cursor.execute('''
                    SELECT date(date) as date_only, COUNT(*) as count 
                    FROM emails 
                    WHERE user_id = ? AND date >= ? AND (deleted IS NULL OR deleted = 0)
                    GROUP BY date(date)
                    ORDER BY date(date) DESC
                    LIMIT 7
                ''', (user_id, seven_days_ago))
                recent_activity = [{'date': row['date_only'], 'count': row['count']} for row in cursor.fetchall()]
                
                stats = {
                    'total_emails': total_emails,
                    'processed_emails': processed_emails,
                    'today_emails': today_emails,
                    'email_accounts': email_accounts,
                    'total_digests': total_digests,
                    'recent_activity': recent_activity,
                    'processing_rate': round(processed_emails / total_emails * 100, 2) if total_emails > 0 else 0,
                    'updated_at': datetime.now().isoformat()
                }
                
                # 缓存结果
                if cache and cache.is_connected() and cache_key:
                    cache.set(cache_key, stats, Config.CACHE_TTL['user_stats'])
                    logger.debug(f"用户统计已缓存: user_id={user_id}")
                
                return stats
                
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return {
                'total_emails': 0,
                'processed_emails': 0,
                'today_emails': 0,
                'email_accounts': 0,
                'total_digests': 0,
                'recent_activity': [],
                'processing_rate': 0
            }
    
    def get_user_email_accounts(self, user_id: int) -> List[Dict]:
        """获取用户的邮箱账户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, email, provider, is_active, last_check, total_emails, created_at
                    FROM email_accounts
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                accounts = []
                for row in cursor.fetchall():
                    accounts.append({
                        'id': row['id'],
                        'email': row['email'],
                        'provider': row['provider'],
                        'is_active': bool(row['is_active']),
                        'last_check': row['last_check'],
                        'total_emails': row['total_emails'],
                        'created_at': row['created_at']
                    })
                
                return accounts
                
        except Exception as e:
            logger.error(f"获取用户邮箱账户失败: {e}")
            return []
    
    def save_user_email_account(self, user_id: int, email: str, password: str, provider: str) -> bool:
        """保存用户邮箱账户配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO email_accounts 
                    (user_id, email, password, provider, is_active, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (user_id, email, password, provider, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存用户邮箱账户失败: {e}")
            return False
    
    def delete_user_email_account(self, account_id: int, user_id: int) -> bool:
        """删除用户的邮箱账户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 先检查账户是否属于该用户
                cursor.execute('''
                    SELECT email FROM email_accounts 
                    WHERE id = ? AND user_id = ?
                ''', (account_id, user_id))
                
                account = cursor.fetchone()
                if not account:
                    logger.warning(f"账户不存在或不属于用户 {user_id}")
                    return False
                
                account_email = account['email']
                
                # 删除账户
                cursor.execute('''
                    DELETE FROM email_accounts 
                    WHERE id = ? AND user_id = ?
                ''', (account_id, user_id))
                
                conn.commit()
                logger.info(f"成功删除用户 {user_id} 的邮箱账户: {account_email}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除邮箱账户失败: {e}")
            return False
    
    def transfer_email_account(self, account_id: int, from_user_id: int, to_username: str) -> tuple:
        """转移邮箱账户到其他用户
        
        Returns:
            (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取来源用户信息
                cursor.execute('''
                    SELECT username FROM users 
                    WHERE id = ?
                ''', (from_user_id,))
                
                from_user = cursor.fetchone()
                if not from_user:
                    return False, "来源用户不存在"
                
                from_username = from_user['username']
                
                # 先检查账户是否属于来源用户
                cursor.execute('''
                    SELECT email, password, provider FROM email_accounts 
                    WHERE id = ? AND user_id = ?
                ''', (account_id, from_user_id))
                
                account = cursor.fetchone()
                if not account:
                    return False, "账户不存在或不属于当前用户"
                
                account_email = account['email']
                account_password = account['password']
                account_provider = account['provider']
                
                # 查找目标用户
                cursor.execute('''
                    SELECT id, username FROM users 
                    WHERE username = ?
                ''', (to_username,))
                
                target_user = cursor.fetchone()
                if not target_user:
                    return False, f"目标用户 '{to_username}' 不存在"
                
                to_user_id = target_user['id']
                
                # 检查目标用户是否已经有相同的邮箱账户
                cursor.execute('''
                    SELECT id FROM email_accounts 
                    WHERE user_id = ? AND email = ?
                ''', (to_user_id, account_email))
                
                if cursor.fetchone():
                    return False, f"目标用户已经配置了邮箱账户 {account_email}"
                
                # 删除来源用户的账户
                cursor.execute('''
                    DELETE FROM email_accounts 
                    WHERE id = ? AND user_id = ?
                ''', (account_id, from_user_id))
                
                # 为目标用户创建账户
                cursor.execute('''
                    INSERT INTO email_accounts 
                    (user_id, email, password, provider, is_active, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (to_user_id, account_email, account_password, account_provider, datetime.now().isoformat()))
                
                conn.commit()
                
                # 记录操作日志
                logger.info(f"成功将邮箱账户 {account_email} 从用户 {from_user_id} ({from_username}) 转移到用户 {to_user_id} ({to_username})")
                
                # 发送通知给来源用户（转出方）
                try:
                    self.save_notification(
                        user_id=from_user_id,
                        title="邮箱账户转移成功",
                        message=f"您已成功将邮箱账户 {account_email} 转移给用户 @{to_username}。该账户的所有配置（包括密码、服务商设置等）已完整转移，您已失去对该账户的访问权限。",
                        notification_type='info'
                    )
                    logger.info(f"已向转出方用户 {from_user_id} ({from_username}) 发送账户转移通知")
                except Exception as notif_error:
                    logger.warning(f"发送转出方通知失败，但转移操作已成功: {notif_error}")
                
                # 发送通知给目标用户（接收方）
                try:
                    self.save_notification(
                        user_id=to_user_id,
                        title="收到新的邮箱账户",
                        message=f"用户 @{from_username} 已将邮箱账户 {account_email} 转移给您。该账户已添加到您的邮箱列表中，您可以立即开始使用。账户信息：服务商 {account_provider}，状态：已激活。",
                        notification_type='success'
                    )
                    logger.info(f"已向接收方用户 {to_user_id} ({to_username}) 发送账户接收通知")
                except Exception as notif_error:
                    logger.warning(f"发送接收方通知失败，但转移操作已成功: {notif_error}")
                
                return True, f"成功转移邮箱账户到用户 {to_username}"
                
        except Exception as e:
            logger.error(f"转移邮箱账户失败: {e}")
            return False, f"转移失败: {str(e)}"
    
    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """更新用户密码"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, updated_at = ?
                    WHERE id = ?
                ''', (new_password_hash, datetime.now().isoformat(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新用户密码失败: {e}")
            return False
    
    def update_user_profile(self, user_id: int, email: str = None, full_name: str = None) -> bool:
        """更新用户个人资料"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建动态更新语句
                update_fields = []
                params = []
                
                if email is not None:
                    update_fields.append('email = ?')
                    params.append(email)
                
                if full_name is not None:
                    update_fields.append('full_name = ?')
                    params.append(full_name)
                
                if not update_fields:
                    return True  # 没有需要更新的字段
                
                update_fields.append('updated_at = ?')
                params.append(datetime.now().isoformat())
                params.append(user_id)
                
                sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(sql, params)
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.IntegrityError as e:
            if 'email' in str(e):
                logger.warning(f"邮箱已被其他用户使用: {email}")
            return False
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            return False
    
    def get_user_config(self, user_id: int, key: str, default_value: str = None) -> str:
        """获取用户配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT value FROM user_config 
                    WHERE user_id = ? AND key = ?
                ''', (user_id, key))
                
                row = cursor.fetchone()
                return row['value'] if row else default_value
                
        except Exception as e:
            logger.error(f"获取用户配置失败: {e}")
            return default_value
    
    def set_user_config(self, user_id: int, key: str, value: str) -> bool:
        """设置用户配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_config (user_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, key, value, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"设置用户配置失败: {e}")
            return False
    
    def get_user_configs(self, user_id: int) -> Dict[str, str]:
        """获取用户所有配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key, value FROM user_config 
                    WHERE user_id = ?
                ''', (user_id,))
                
                configs = {}
                for row in cursor.fetchall():
                    configs[row['key']] = row['value']
                
                return configs
                
        except Exception as e:
            logger.error(f"获取用户配置失败: {e}")
            return {}
    
    def get_system_config(self, key: str, default_value: str = None) -> str:
        """获取系统配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM system_config WHERE key = ?', (key,))
                
                row = cursor.fetchone()
                return row['value'] if row else default_value
                
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            return default_value
    
    def set_system_config(self, key: str, value: str) -> bool:
        """设置系统配置"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"设置系统配置失败: {e}")
            return False
    
    def get_user_digests_paginated(self, user_id: int, page: int = 1, per_page: int = 10) -> tuple:
        """分页获取用户历史简报"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取用户简报总数
                cursor.execute('SELECT COUNT(*) as total FROM digests WHERE user_id = ?', (user_id,))
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute('''
                    SELECT id, date, title, content, email_count, summary, created_at
                    FROM digests
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, per_page, offset))
                
                digests = []
                for row in cursor.fetchall():
                    digests.append({
                        'id': row['id'],
                        'date': row['date'],
                        'title': row['title'],
                        'content': json.loads(row['content']) if row['content'] else {},
                        'email_count': row['email_count'],
                        'summary': row['summary'],
                        'created_at': row['created_at']
                    })
                
                return digests, total
                
        except Exception as e:
            logger.error(f"获取用户历史简报失败: {e}")
            return [], 0
    
    def get_digest_by_id(self, digest_id: int, user_id: int = None) -> Optional[Dict]:
        """根据ID获取简报详情"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    # 用户只能查看自己的简报
                    cursor.execute('''
                        SELECT id, date, title, content, email_count, summary, created_at
                        FROM digests
                        WHERE id = ? AND user_id = ?
                    ''', (digest_id, user_id))
                else:
                    # 管理员可以查看所有简报
                    cursor.execute('''
                        SELECT id, date, title, content, email_count, summary, created_at
                        FROM digests
                        WHERE id = ?
                    ''', (digest_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'date': row['date'],
                        'title': row['title'],
                        'content': json.loads(row['content']) if row['content'] else {},
                        'email_count': row['email_count'],
                        'summary': row['summary'],
                        'created_at': row['created_at']
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取简报详情失败: {e}")
            return None
    
    def get_digests_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict]:
        """根据日期范围获取简报"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, date, title, content, email_count, summary, created_at
                    FROM digests
                    WHERE user_id = ? AND date >= ? AND date <= ?
                    ORDER BY date DESC, created_at DESC
                ''', (user_id, start_date, end_date))
                
                digests = []
                for row in cursor.fetchall():
                    digests.append({
                        'id': row['id'],
                        'date': row['date'],
                        'title': row['title'],
                        'content': json.loads(row['content']) if row['content'] else {},
                        'email_count': row['email_count'],
                        'summary': row['summary'],
                        'created_at': row['created_at']
                    })
                
                return digests
                
        except Exception as e:
            logger.error(f"根据日期范围获取简报失败: {e}")
            return []
    
    def delete_digest(self, digest_id: int, user_id: int = None) -> bool:
        """删除简报"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    # 用户只能删除自己的简报
                    cursor.execute('DELETE FROM digests WHERE id = ? AND user_id = ?', (digest_id, user_id))
                else:
                    # 管理员可以删除任何简报
                    cursor.execute('DELETE FROM digests WHERE id = ?', (digest_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除简报失败: {e}")
            return False
    
    def update_email_account_stats(self, user_id: int, account_email: str, email_count: int) -> bool:
        """更新邮箱账户的统计信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE email_accounts 
                    SET last_check = ?, total_emails = ?, updated_at = ?
                    WHERE user_id = ? AND email = ?
                ''', (
                    datetime.now().isoformat(),
                    email_count,
                    datetime.now().isoformat(),
                    user_id,
                    account_email
                ))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新邮箱账户统计失败: {e}")
            return False
    
    def get_account_email_count(self, user_id: int, account_email: str) -> int:
        """获取指定邮箱账户的邮件数量"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count FROM emails 
                    WHERE user_id = ? AND account_email = ?
                ''', (user_id, account_email))
                
                return cursor.fetchone()['count']
                
        except Exception as e:
            logger.error(f"获取邮箱账户邮件数量失败: {e}")
            return 0
    
    def get_user_emails_filtered(self, user_id: int, page: int = 1, per_page: int = 20, 
                                search: str = '', category: str = '', provider: str = '', 
                                processed: str = '') -> Tuple[List[Dict], int]:
        """分页获取用户邮件列表（带筛选）- 支持Redis缓存"""
        cache = get_cache_service()
        
        # 生成缓存键
        cache_key = None
        if cache and cache.is_connected():
            # 创建筛选条件的哈希
            filter_params = {
                'search': search,
                'category': category,
                'provider': provider,
                'processed': processed,
                'page': page,
                'per_page': per_page
            }
            cache_key = cache.generate_cache_key('emails:user', user_id, **filter_params)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"邮件列表缓存命中: user_id={user_id}, page={page}")
                return cached_result['emails'], cached_result['total']
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建WHERE条件（默认不显示已删除的邮件）
                where_conditions = ['user_id = ?', '(deleted IS NULL OR deleted = 0)']
                params = [user_id]
                
                # 搜索条件
                if search:
                    where_conditions.append('(subject LIKE ? OR sender LIKE ? OR body LIKE ?)')
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param, search_param])
                
                # 分类筛选
                if category:
                    where_conditions.append('category = ?')
                    params.append(category)
                
                # 服务商筛选
                if provider:
                    where_conditions.append('provider = ?')
                    params.append(provider)
                
                # 处理状态筛选
                if processed:
                    where_conditions.append('processed = ?')
                    params.append(int(processed))
                
                where_clause = ' AND '.join(where_conditions)
                
                # 优化：使用窗口函数一次查询获取数据和总数
                data_sql = f'''
                    WITH email_data AS (
                        SELECT id, subject, sender, date, summary, ai_summary, processed, 
                               account_email, provider, importance, category, created_at,
                               COUNT(*) OVER() as total_count,
                               ROW_NUMBER() OVER(ORDER BY date DESC, created_at DESC) as row_num
                        FROM emails
                        WHERE {where_clause}
                    )
                    SELECT * FROM email_data
                    WHERE row_num > ? AND row_num <= ?
                '''
                
                offset = (page - 1) * per_page
                params.extend([offset, offset + per_page])
                cursor.execute(data_sql, params)
                
                rows = cursor.fetchall()
                total = rows[0]['total_count'] if rows else 0
                
                emails = []
                for row in rows:
                    emails.append({
                        'id': row['id'],
                        'subject': row['subject'],
                        'sender': row['sender'],
                        'date': row['date'],
                        'summary': row['summary'],
                        'ai_summary': row['ai_summary'],
                        'processed': bool(row['processed']),
                        'account_email': row['account_email'],
                        'provider': row['provider'],
                        'importance': row['importance'],
                        'category': row['category'],
                        'created_at': row['created_at']
                    })
                
                # 缓存结果
                if cache and cache.is_connected() and cache_key:
                    cache_data = {
                        'emails': emails,
                        'total': total,
                        'cached_at': datetime.now().isoformat()
                    }
                    cache.set(cache_key, cache_data, Config.CACHE_TTL['email_list'])
                    logger.debug(f"邮件列表已缓存: user_id={user_id}, page={page}, count={len(emails)}")
                
                return emails, total
                
        except Exception as e:
            logger.error(f"获取筛选邮件失败: {e}")
            return [], 0
    
    def soft_delete_email(self, email_id: int, user_id: int) -> bool:
        """软删除邮件（标记为删除）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否需要添加deleted字段
                cursor.execute("PRAGMA table_info(emails)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'deleted' not in columns:
                    # 添加deleted字段
                    cursor.execute('ALTER TABLE emails ADD COLUMN deleted BOOLEAN DEFAULT 0')
                    logger.info("为emails表添加deleted字段")
                
                # 标记为删除
                cursor.execute('''
                    UPDATE emails 
                    SET deleted = 1, updated_at = ?
                    WHERE id = ? AND user_id = ?
                ''', (datetime.now().isoformat(), email_id, user_id))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                # 缓存失效 - 清除相关缓存
                if success:
                    cache = get_cache_service()
                    if cache and cache.is_connected():
                        # 清除普通邮件列表缓存，因为删除的邮件不应该出现在那里
                        email_pattern = f"emails:user:{user_id}:*"
                        email_count = cache.delete_pattern(email_pattern)
                        logger.debug(f"软删除邮件后清除邮件列表缓存: {email_count} 个键")
                        
                        # 清除已删除邮件列表缓存，因为新删除的邮件应该出现在那里
                        deleted_pattern = f"deleted_emails:user:{user_id}:*"
                        deleted_count = cache.delete_pattern(deleted_pattern)
                        logger.debug(f"软删除邮件后清除已删除邮件缓存: {deleted_count} 个键")
                        
                        # 清除用户统计缓存
                        cache.invalidate_user_cache(user_id, 'delete_email')
                
                return success
                
        except Exception as e:
            logger.error(f"软删除邮件失败: {e}")
            return False
    
    def purge_email(self, email_id: int, user_id: int) -> bool:
        """彻底删除邮件（物理删除）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM emails WHERE id = ? AND user_id = ?', (email_id, user_id))
                conn.commit()
                success = cursor.rowcount > 0
                
                # 缓存失效 - 清除相关缓存
                if success:
                    cache = get_cache_service()
                    if cache and cache.is_connected():
                        # 清除已删除邮件列表的所有分页缓存
                        cache_pattern = f"deleted_emails:user:{user_id}:*"
                        deleted_count = cache.delete_pattern(cache_pattern)
                        logger.debug(f"彻底删除邮件后清除已删除邮件缓存: {deleted_count} 个键")
                        
                        # 清除用户统计缓存
                        cache.invalidate_user_cache(user_id, 'purge_email')
                
                return success
                
        except Exception as e:
            logger.error(f"彻底删除邮件失败: {e}")
            return False
    
    def restore_email(self, email_id: int, user_id: int) -> bool:
        """恢复软删除的邮件"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE emails 
                    SET deleted = 0, updated_at = ?
                    WHERE id = ? AND user_id = ?
                ''', (datetime.now().isoformat(), email_id, user_id))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                # 缓存失效 - 清除相关缓存
                if success:
                    cache = get_cache_service()
                    if cache and cache.is_connected():
                        # 清除已删除邮件列表的所有分页缓存
                        cache_pattern = f"deleted_emails:user:{user_id}:*"
                        deleted_count = cache.delete_pattern(cache_pattern)
                        logger.debug(f"恢复邮件后清除已删除邮件缓存: {deleted_count} 个键")
                        
                        # 清除普通邮件列表缓存，因为恢复的邮件会出现在那里
                        email_pattern = f"emails:user:{user_id}:*"
                        email_count = cache.delete_pattern(email_pattern)
                        logger.debug(f"恢复邮件后清除邮件列表缓存: {email_count} 个键")
                        
                        # 清除用户统计缓存
                        cache.invalidate_user_cache(user_id, 'restore_email')
                
                return success
                
        except Exception as e:
            logger.error(f"恢复邮件失败: {e}")
            return False
    
    def get_user_deleted_emails_filtered(self, user_id: int, page: int = 1, per_page: int = 20, 
                                        search: str = '', category: str = '', provider: str = '', 
                                        processed: str = '') -> Tuple[List[Dict], int]:
        """分页获取用户已删除邮件列表（回收站）- 支持Redis缓存"""
        cache = get_cache_service()
        
        # 生成缓存键
        cache_key = None
        if cache and cache.is_connected():
            # 创建筛选条件的哈希
            filter_params = {
                'search': search,
                'category': category,
                'provider': provider,
                'processed': processed,
                'page': page,
                'per_page': per_page
            }
            cache_key = cache.generate_cache_key('deleted_emails:user', user_id, **filter_params)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"已删除邮件列表缓存命中: user_id={user_id}, page={page}")
                return cached_result['emails'], cached_result['total']
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建WHERE条件（只显示已删除的邮件）
                where_conditions = ['user_id = ?', 'deleted = 1']
                params = [user_id]
                
                # 搜索条件
                if search:
                    where_conditions.append('(subject LIKE ? OR sender LIKE ? OR body LIKE ?)')
                    search_param = f'%{search}%'
                    params.extend([search_param, search_param, search_param])
                
                # 分类筛选
                if category:
                    where_conditions.append('category = ?')
                    params.append(category)
                
                # 服务商筛选
                if provider:
                    where_conditions.append('provider = ?')
                    params.append(provider)
                
                # 处理状态筛选
                if processed:
                    where_conditions.append('processed = ?')
                    params.append(int(processed))
                
                where_clause = ' AND '.join(where_conditions)
                
                # 优化：使用窗口函数一次查询获取数据和总数
                data_sql = f'''
                    WITH email_data AS (
                        SELECT id, subject, sender, date, summary, ai_summary, processed, 
                               account_email, provider, importance, category, created_at,
                               COUNT(*) OVER() as total_count,
                               ROW_NUMBER() OVER(ORDER BY date DESC, created_at DESC) as row_num
                        FROM emails
                        WHERE {where_clause}
                    )
                    SELECT * FROM email_data
                    WHERE row_num > ? AND row_num <= ?
                '''
                
                offset = (page - 1) * per_page
                params.extend([offset, offset + per_page])
                cursor.execute(data_sql, params)
                
                rows = cursor.fetchall()
                total = rows[0]['total_count'] if rows else 0
                
                emails = []
                for row in rows:
                    emails.append({
                        'id': row['id'],
                        'subject': row['subject'],
                        'sender': row['sender'],
                        'date': row['date'],
                        'summary': row['summary'],
                        'ai_summary': row['ai_summary'],
                        'processed': bool(row['processed']),
                        'account_email': row['account_email'],
                        'provider': row['provider'],
                        'importance': row['importance'],
                        'category': row['category'],
                        'created_at': row['created_at']
                    })
                
                # 缓存结果
                if cache and cache.is_connected() and cache_key:
                    cache_data = {
                        'emails': emails,
                        'total': total,
                        'cached_at': datetime.now().isoformat()
                    }
                    cache.set(cache_key, cache_data, Config.CACHE_TTL['email_list'])
                    logger.debug(f"已删除邮件列表已缓存: user_id={user_id}, page={page}, count={len(emails)}")
                
                return emails, total
                
        except Exception as e:
            logger.error(f"获取已删除邮件失败: {e}")
            return [], 0
    
    def clear_user_emails(self, user_id: int) -> Tuple[bool, int]:
        """
        清空用户的所有邮件（物理删除）
        注意：不删除邮件账户配置，只删除邮件数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            (success, deleted_count): 成功标志和删除的邮件数量
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 首先获取要删除的邮件数量
                cursor.execute('SELECT COUNT(*) as count FROM emails WHERE user_id = ?', (user_id,))
                deleted_count = cursor.fetchone()['count']
                
                if deleted_count == 0:
                    logger.info(f"用户 {user_id} 没有邮件需要清空")
                    return True, 0
                
                # 物理删除所有用户邮件
                cursor.execute('DELETE FROM emails WHERE user_id = ?', (user_id,))
                
                conn.commit()
                actual_deleted = cursor.rowcount
                
                logger.info(f"成功清空用户 {user_id} 的所有邮件，共删除 {actual_deleted} 封邮件")
                
                # 删除用户的所有附件文件
                try:
                    import os
                    import shutil
                    user_attachment_dir = os.path.join('email_attachments', f'user_{user_id}')
                    
                    if os.path.exists(user_attachment_dir):
                        # 统计附件数量和总大小
                        total_files = 0
                        total_size = 0
                        for root, dirs, files in os.walk(user_attachment_dir):
                            total_files += len(files)
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    total_size += os.path.getsize(file_path)
                                except Exception:
                                    pass
                        
                        # 删除整个用户附件目录
                        shutil.rmtree(user_attachment_dir)
                        logger.info(f"成功删除用户 {user_id} 的附件目录，共删除 {total_files} 个文件，释放 {total_size / 1024 / 1024:.2f} MB 空间")
                    else:
                        logger.info(f"用户 {user_id} 没有附件目录需要删除")
                        
                except Exception as e:
                    logger.error(f"删除用户附件目录失败: {e}")
                    # 即使附件删除失败，也不影响邮件删除的结果
                
                # 缓存失效 - 清除所有相关缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    # 清除所有邮件列表缓存
                    email_pattern = f"emails:user:{user_id}:*"
                    email_count = cache.delete_pattern(email_pattern)
                    logger.debug(f"清空邮件后清除邮件列表缓存: {email_count} 个键")
                    
                    # 清除已删除邮件列表缓存
                    deleted_pattern = f"deleted_emails:user:{user_id}:*"
                    deleted_cache_count = cache.delete_pattern(deleted_pattern)
                    logger.debug(f"清空邮件后清除已删除邮件缓存: {deleted_cache_count} 个键")
                    
                    # 清除用户统计缓存
                    cache.invalidate_user_cache(user_id, 'clear_all_emails')
                
                return True, actual_deleted
                
        except Exception as e:
            logger.error(f"清空用户邮件失败: {e}")
            return False, 0
    
    def clear_user_digests(self, user_id: int) -> Tuple[bool, int]:
        """
        清空用户的所有简报（物理删除）
        
        Args:
            user_id: 用户ID
            
        Returns:
            (success, deleted_count): 成功标志和删除的简报数量
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 首先获取要删除的简报数量
                cursor.execute('SELECT COUNT(*) as count FROM digests WHERE user_id = ?', (user_id,))
                deleted_count = cursor.fetchone()['count']
                
                if deleted_count == 0:
                    logger.info(f"用户 {user_id} 没有简报需要清空")
                    return True, 0
                
                # 物理删除所有用户简报
                cursor.execute('DELETE FROM digests WHERE user_id = ?', (user_id,))
                
                conn.commit()
                actual_deleted = cursor.rowcount
                
                logger.info(f"成功清空用户 {user_id} 的所有简报，共删除 {actual_deleted} 份简报")
                
                # 缓存失效 - 清除所有相关缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    # 清除所有简报列表缓存
                    digest_pattern = f"digests:user:{user_id}:*"
                    digest_count = cache.delete_pattern(digest_pattern)
                    logger.debug(f"清空简报后清除简报列表缓存: {digest_count} 个键")
                    
                    # 清除最新简报缓存
                    latest_key = f"digest:user:{user_id}:latest"
                    cache.delete(latest_key)
                    
                    # 清除用户统计缓存
                    cache.invalidate_user_cache(user_id, 'clear_all_digests')
                
                return True, actual_deleted
                
        except Exception as e:
            logger.error(f"清空用户简报失败: {e}")
            return False, 0
    
    # ==================== 系统通知相关方法 ====================
    
    def save_notification(self, user_id: int, title: str, message: str, 
                         notification_type: str = 'info') -> bool:
        """
        保存系统通知
        
        Args:
            user_id: 用户ID
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型 (info/success/warning/error)
            
        Returns:
            bool: 保存成功返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_notifications 
                    (user_id, type, title, message, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, notification_type, title, message, 
                      datetime.now().isoformat()))
                
                conn.commit()
                logger.info(f"保存系统通知成功: user_id={user_id}, type={notification_type}, title={title}")
                
                # 清除该用户的通知缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    pattern = f"notifications:user:{user_id}:*"
                    cache.delete_pattern(pattern)
                
                return True
                
        except Exception as e:
            logger.error(f"保存系统通知失败: {e}")
            return False
    
    def get_user_notifications(self, user_id: int, page: int = 1, 
                              per_page: int = 20, 
                              unread_only: bool = False) -> Tuple[List[Dict], int]:
        """
        获取用户的系统通知列表（分页）
        
        Args:
            user_id: 用户ID
            page: 页码
            per_page: 每页数量
            unread_only: 仅获取未读通知
            
        Returns:
            (notifications, total): 通知列表和总数
        """
        cache = get_cache_service()
        
        # 生成缓存键
        cache_key = None
        if cache and cache.is_connected():
            cache_key = f"notifications:user:{user_id}:page:{page}:per_page:{per_page}:unread:{unread_only}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"通知列表缓存命中: user_id={user_id}, page={page}")
                return cached_result['notifications'], cached_result['total']
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建WHERE条件
                where_conditions = ['user_id = ?']
                params = [user_id]
                
                if unread_only:
                    where_conditions.append('is_read = 0')
                
                where_clause = ' AND '.join(where_conditions)
                
                # 使用窗口函数一次查询获取数据和总数
                sql = f'''
                    WITH notification_data AS (
                        SELECT id, type, title, message, is_read, created_at,
                               COUNT(*) OVER() as total_count,
                               ROW_NUMBER() OVER(ORDER BY created_at DESC) as row_num
                        FROM system_notifications
                        WHERE {where_clause}
                    )
                    SELECT * FROM notification_data
                    WHERE row_num > ? AND row_num <= ?
                '''
                
                offset = (page - 1) * per_page
                params.extend([offset, offset + per_page])
                cursor.execute(sql, params)
                
                rows = cursor.fetchall()
                total = rows[0]['total_count'] if rows else 0
                
                notifications = []
                for row in rows:
                    notification = {
                        'id': row['id'],
                        'type': row['type'],
                        'title': row['title'],
                        'message': row['message'],
                        'is_read': bool(row['is_read']),
                        'created_at': row['created_at']
                    }
                    notifications.append(notification)
                
                # 缓存结果（5分钟）
                if cache and cache.is_connected():
                    cache.set(cache_key, {
                        'notifications': notifications,
                        'total': total
                    }, ttl=300)
                
                return notifications, total
                
        except Exception as e:
            logger.error(f"获取用户通知失败: {e}")
            return [], 0
    
    def get_unread_notification_count(self, user_id: int) -> int:
        """
        获取用户未读通知数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 未读通知数量
        """
        cache = get_cache_service()
        cache_key = f"notifications:user:{user_id}:unread_count"
        
        # 尝试从缓存获取
        if cache and cache.is_connected():
            cached_count = cache.get(cache_key)
            if cached_count is not None:
                return cached_count
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM system_notifications 
                    WHERE user_id = ? AND is_read = 0
                ''', (user_id,))
                
                count = cursor.fetchone()['count']
                
                # 缓存结果（2分钟）
                if cache and cache.is_connected():
                    cache.set(cache_key, count, ttl=120)
                
                return count
                
        except Exception as e:
            logger.error(f"获取未读通知数量失败: {e}")
            return 0
    
    def mark_notification_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        标记通知为已读
        
        Args:
            notification_id: 通知ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            bool: 标记成功返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE system_notifications 
                    SET is_read = 1 
                    WHERE id = ? AND user_id = ?
                ''', (notification_id, user_id))
                
                conn.commit()
                
                # 清除该用户的通知缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    pattern = f"notifications:user:{user_id}:*"
                    cache.delete_pattern(pattern)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"标记通知为已读失败: {e}")
            return False
    
    def mark_all_notifications_as_read(self, user_id: int) -> bool:
        """
        标记用户所有通知为已读
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 标记成功返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE system_notifications 
                    SET is_read = 1 
                    WHERE user_id = ? AND is_read = 0
                ''', (user_id,))
                
                conn.commit()
                logger.info(f"标记用户 {user_id} 的所有通知为已读，共 {cursor.rowcount} 条")
                
                # 清除该用户的通知缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    pattern = f"notifications:user:{user_id}:*"
                    cache.delete_pattern(pattern)
                
                return True
                
        except Exception as e:
            logger.error(f"标记所有通知为已读失败: {e}")
            return False
    
    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        删除通知
        
        Args:
            notification_id: 通知ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            bool: 删除成功返回True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM system_notifications 
                    WHERE id = ? AND user_id = ?
                ''', (notification_id, user_id))
                
                conn.commit()
                
                # 清除该用户的通知缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    pattern = f"notifications:user:{user_id}:*"
                    cache.delete_pattern(pattern)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除通知失败: {e}")
            return False
    
    def clear_old_notifications(self, days: int = 30) -> int:
        """
        清理超过指定天数的旧通知
        
        Args:
            days: 保留天数（默认30天）
            
        Returns:
            int: 删除的通知数量
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM system_notifications 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                
                conn.commit()
                deleted_count = cursor.rowcount
                
                logger.info(f"清理 {days} 天前的旧通知，共删除 {deleted_count} 条")
                
                # 清除所有通知相关缓存
                cache = get_cache_service()
                if cache and cache.is_connected():
                    pattern = "notifications:*"
                    cache.delete_pattern(pattern)
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧通知失败: {e}")
            return 0