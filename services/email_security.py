#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件安全验证服务
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import hashlib
import json

from models.database import Database

logger = logging.getLogger(__name__)

class EmailSecurityValidator:
    """邮件安全验证器"""
    
    def __init__(self):
        self.db = Database()
        
        # 危险文件扩展名黑名单
        self.dangerous_extensions = {
            'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 
            'jar', 'msi', 'dll', 'sys', 'scf', 'lnk', 'reg', 'ps1'
        }
        
        # 垃圾邮件关键词
        self.spam_keywords = {
            '中奖', '免费', '赚钱', '投资', '贷款', '优惠', '促销',
            '限时', '紧急', '立即', '马上', '赶快', '机会', '秘密'
        }
        
        # 恶意URL模式
        self.malicious_url_patterns = [
            r'bit\.ly',
            r'tinyurl\.com',
            r'短链接',
            r'点击.*领取',
            r'免费.*下载'
        ]
    
    def validate_email_send(self, user_id: int, email_data: Dict) -> Tuple[bool, str]:
        """
        验证邮件发送请求
        
        Args:
            user_id: 用户ID
            email_data: 邮件数据
            
        Returns:
            (is_valid: bool, message: str)
        """
        try:
            # 1. 验证用户权限
            if not self._validate_user_permissions(user_id):
                return False, "用户权限不足"
            
            # 2. 验证发送频率限制
            if not self._validate_send_rate_limit(user_id):
                return False, "发送频率过高，请稍后再试"
            
            # 3. 验证收件人数量
            if not self._validate_recipient_count(email_data):
                return False, "收件人数量超过限制"
            
            # 4. 验证邮件内容
            content_valid, content_msg = self._validate_email_content(email_data)
            if not content_valid:
                return False, content_msg
            
            # 5. 验证附件安全性
            if email_data.get('attachments'):
                attachment_valid, attachment_msg = self._validate_attachments(email_data['attachments'])
                if not attachment_valid:
                    return False, attachment_msg
            
            # 6. 验证发件人账户
            if not self._validate_sender_account(user_id, email_data.get('sender_account_id')):
                return False, "发件人账户无效或无权限"
            
            return True, "验证通过"
            
        except Exception as e:
            logger.error(f"邮件发送验证失败: {e}")
            return False, f"验证过程出错: {str(e)}"
    
    def validate_attachment_upload(self, user_id: int, filename: str, file_size: int) -> Tuple[bool, str]:
        """
        验证附件上传
        
        Args:
            user_id: 用户ID
            filename: 文件名
            file_size: 文件大小
            
        Returns:
            (is_valid: bool, message: str)
        """
        try:
            # 1. 验证文件扩展名
            if not self._validate_file_extension(filename):
                return False, "不允许的文件类型"
            
            # 2. 验证文件大小
            if file_size > 50 * 1024 * 1024:  # 50MB
                return False, "文件大小超过50MB限制"
            
            # 3. 验证用户上传配额
            if not self._validate_upload_quota(user_id, file_size):
                return False, "上传配额不足"
            
            # 4. 验证文件名安全性
            if not self._validate_filename_security(filename):
                return False, "文件名包含不安全字符"
            
            return True, "验证通过"
            
        except Exception as e:
            logger.error(f"附件上传验证失败: {e}")
            return False, f"验证过程出错: {str(e)}"
    
    def _validate_user_permissions(self, user_id: int) -> bool:
        """验证用户权限"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT is_active, email_send_enabled 
                    FROM users 
                    WHERE id = ?
                ''', (user_id,))
                
                user = cursor.fetchone()
                if not user:
                    return False
                
                # 检查用户是否激活且允许发送邮件
                return user['is_active'] and user.get('email_send_enabled', True)
                
        except Exception as e:
            logger.error(f"验证用户权限失败: {e}")
            return False
    
    def _validate_send_rate_limit(self, user_id: int) -> bool:
        """验证发送频率限制"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查最近1小时内的发送数量
                one_hour_ago = datetime.now() - timedelta(hours=1)
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM sent_emails 
                    WHERE user_id = ? AND sent_at > ?
                ''', (user_id, one_hour_ago))
                
                result = cursor.fetchone()
                hourly_count = result['count'] if result else 0
                
                # 每小时最多发送50封邮件
                if hourly_count >= 50:
                    return False
                
                # 检查最近1分钟内的发送数量
                one_minute_ago = datetime.now() - timedelta(minutes=1)
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM sent_emails 
                    WHERE user_id = ? AND sent_at > ?
                ''', (user_id, one_minute_ago))
                
                result = cursor.fetchone()
                minute_count = result['count'] if result else 0
                
                # 每分钟最多发送5封邮件
                return minute_count < 5
                
        except Exception as e:
            logger.error(f"验证发送频率限制失败: {e}")
            return False
    
    def _validate_recipient_count(self, email_data: Dict) -> bool:
        """验证收件人数量"""
        try:
            to_count = len([addr.strip() for addr in email_data.get('to_addresses', '').split(',') if addr.strip()])
            cc_count = len([addr.strip() for addr in email_data.get('cc_addresses', '').split(',') if addr.strip()])
            bcc_count = len([addr.strip() for addr in email_data.get('bcc_addresses', '').split(',') if addr.strip()])
            
            total_recipients = to_count + cc_count + bcc_count
            
            # 单次发送最多100个收件人
            return total_recipients <= 100
            
        except Exception as e:
            logger.error(f"验证收件人数量失败: {e}")
            return False
    
    def _validate_email_content(self, email_data: Dict) -> Tuple[bool, str]:
        """验证邮件内容"""
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            
            # 1. 检查主题长度
            if len(subject) > 200:
                return False, "邮件主题过长（最多200字符）"
            
            # 2. 检查正文长度
            if len(body) > 1000000:  # 1MB
                return False, "邮件正文过长（最多1MB）"
            
            # 3. 检查垃圾邮件关键词
            content_to_check = (subject + ' ' + body).lower()
            spam_score = 0
            
            for keyword in self.spam_keywords:
                if keyword in content_to_check:
                    spam_score += 1
            
            if spam_score >= 3:
                return False, "邮件内容疑似垃圾邮件"
            
            # 4. 检查恶意URL
            for pattern in self.malicious_url_patterns:
                if re.search(pattern, content_to_check, re.IGNORECASE):
                    return False, "邮件内容包含可疑链接"
            
            # 5. 检查HTML注入
            if self._contains_html_injection(body):
                return False, "邮件内容包含不安全的HTML代码"
            
            return True, "内容验证通过"
            
        except Exception as e:
            logger.error(f"验证邮件内容失败: {e}")
            return False, f"内容验证出错: {str(e)}"
    
    def _validate_attachments(self, attachments: List[Dict]) -> Tuple[bool, str]:
        """验证附件"""
        try:
            if len(attachments) > 10:
                return False, "附件数量过多（最多10个）"
            
            total_size = 0
            for attachment in attachments:
                filename = attachment.get('original_filename', '')
                file_size = attachment.get('file_size', 0)
                
                # 验证文件扩展名
                if not self._validate_file_extension(filename):
                    return False, f"不允许的文件类型: {filename}"
                
                # 验证单个文件大小
                if file_size > 50 * 1024 * 1024:
                    return False, f"文件过大: {filename} (最大50MB)"
                
                total_size += file_size
            
            # 验证总附件大小
            if total_size > 100 * 1024 * 1024:  # 100MB
                return False, "附件总大小超过100MB限制"
            
            return True, "附件验证通过"
            
        except Exception as e:
            logger.error(f"验证附件失败: {e}")
            return False, f"附件验证出错: {str(e)}"
    
    def _validate_sender_account(self, user_id: int, sender_account_id: int) -> bool:
        """验证发件人账户"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM email_accounts 
                    WHERE id = ? AND user_id = ? AND is_active = 1
                ''', (sender_account_id, user_id))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"验证发件人账户失败: {e}")
            return False
    
    def _validate_file_extension(self, filename: str) -> bool:
        """验证文件扩展名"""
        if '.' not in filename:
            return False
        
        ext = filename.rsplit('.', 1)[1].lower()
        return ext not in self.dangerous_extensions
    
    def _validate_upload_quota(self, user_id: int, file_size: int) -> bool:
        """验证上传配额"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 计算用户本月已上传的文件总大小
                current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                cursor.execute('''
                    SELECT COALESCE(SUM(file_size), 0) as total_size
                    FROM email_upload_attachments 
                    WHERE user_id = ? AND created_at >= ?
                ''', (user_id, current_month))
                
                result = cursor.fetchone()
                used_quota = result['total_size'] if result else 0
                
                # 每月上传配额1GB
                monthly_quota = 1024 * 1024 * 1024  # 1GB
                
                return (used_quota + file_size) <= monthly_quota
                
        except Exception as e:
            logger.error(f"验证上传配额失败: {e}")
            return False
    
    def _validate_filename_security(self, filename: str) -> bool:
        """验证文件名安全性"""
        # 检查路径遍历攻击
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # 检查Windows保留名称
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        # 检查特殊字符
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            if char in filename:
                return False
        
        return True
    
    def _contains_html_injection(self, content: str) -> bool:
        """检查HTML注入"""
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def log_security_event(self, user_id: int, event_type: str, details: Dict):
        """记录安全事件"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO security_logs (
                        user_id, event_type, details, ip_address, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    event_type,
                    json.dumps(details),
                    details.get('ip_address', ''),
                    datetime.now()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")
    
    def get_user_security_stats(self, user_id: int) -> Dict:
        """获取用户安全统计"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取发送统计
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_sent,
                        COUNT(CASE WHEN sent_at > datetime('now', '-1 hour') THEN 1 END) as sent_last_hour,
                        COUNT(CASE WHEN sent_at > datetime('now', '-1 day') THEN 1 END) as sent_last_day
                    FROM sent_emails 
                    WHERE user_id = ?
                ''', (user_id,))
                
                send_stats = cursor.fetchone()
                
                # 获取上传统计
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_uploads,
                        COALESCE(SUM(file_size), 0) as total_size,
                        COALESCE(SUM(CASE WHEN created_at > datetime('now', '-1 month') THEN file_size ELSE 0 END), 0) as monthly_size
                    FROM email_upload_attachments 
                    WHERE user_id = ?
                ''', (user_id,))
                
                upload_stats = cursor.fetchone()
                
                return {
                    'send_stats': dict(send_stats) if send_stats else {},
                    'upload_stats': dict(upload_stats) if upload_stats else {},
                    'monthly_quota': 1024 * 1024 * 1024,  # 1GB
                    'hourly_limit': 50,
                    'minute_limit': 5
                }
                
        except Exception as e:
            logger.error(f"获取用户安全统计失败: {e}")
            return {}

# 全局安全验证器实例
email_security = EmailSecurityValidator()
