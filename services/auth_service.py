#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 用户认证服务
"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from functools import wraps
from flask import session, request, redirect, url_for, flash, g
import logging

from models.database import Database

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.db = Database()
        self.session_timeout_hours = 24  # 24小时会话超时
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        # 使用SHA-256 + 盐值
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码"""
        try:
            if ':' not in stored_hash:
                return False
            
            salt, hash_value = stored_hash.split(':', 1)
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return password_hash == hash_value
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """验证用户名格式"""
        if not username:
            return False, "用户名不能为空"
        
        if len(username) < 3:
            return False, "用户名至少3个字符"
        
        if len(username) > 20:
            return False, "用户名不能超过20个字符"
        
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"
        
        return True, ""
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """验证邮箱格式"""
        if not email:
            return False, "邮箱不能为空"
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "邮箱格式不正确"
        
        return True, ""
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """验证密码强度"""
        if not password:
            return False, "密码不能为空"
        
        if len(password) < 6:
            return False, "密码至少6个字符"
        
        if len(password) > 50:
            return False, "密码不能超过50个字符"
        
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_letter and has_digit):
            return False, "密码必须包含字母和数字"
        
        return True, ""
    
    def register_user(self, username: str, email: str, password: str, full_name: str = None) -> Tuple[bool, str, int]:
        """用户注册
        
        Returns:
            Tuple[bool, str, int]: (成功标志, 消息, 用户ID)
        """
        # 验证输入
        valid, msg = self.validate_username(username)
        if not valid:
            return False, msg, None
        
        valid, msg = self.validate_email(email)
        if not valid:
            return False, msg, None
        
        valid, msg = self.validate_password(password)
        if not valid:
            return False, msg, None
        
        # 检查用户名和邮箱是否已存在
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            return False, "用户名已存在", None
        
        existing_email = self.db.get_user_by_email(email)
        if existing_email:
            return False, "邮箱已被注册", None
        
        # 创建用户
        password_hash = self.hash_password(password)
        user_id = self.db.create_user(username, email, password_hash, full_name)
        
        if user_id:
            logger.info(f"新用户注册成功: {username} ({email})")
            return True, "注册成功", user_id
        else:
            return False, "注册失败，请稍后重试", None
    
    def login_user(self, username_or_email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """用户登录"""
        # 尝试用户名登录
        user = self.db.get_user_by_username(username_or_email)
        
        # 如果用户名不存在，尝试邮箱登录
        if not user:
            user = self.db.get_user_by_email(username_or_email)
        
        if not user:
            return False, "用户不存在", None
        
        # 验证密码
        if not self.verify_password(password, user['password_hash']):
            return False, "密码错误", None
        
        # 更新最后登录时间
        self.db.update_user_last_login(user['id'])
        
        # 创建会话
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=self.session_timeout_hours)
        
        if self.db.create_user_session(user['id'], session_token, expires_at):
            # 设置Flask会话
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['session_token'] = session_token
            session['is_admin'] = user['is_admin']
            
            logger.info(f"用户登录成功: {user['username']}")
            return True, "登录成功", user
        else:
            return False, "创建会话失败", None
    
    def logout_user(self) -> bool:
        """用户登出"""
        session_token = session.get('session_token')
        if session_token:
            self.db.delete_user_session(session_token)
        
        # 清除Flask会话
        session.clear()
        return True
    
    def get_current_user(self) -> Optional[Dict]:
        """获取当前登录用户"""
        session_token = session.get('session_token')
        if not session_token:
            return None
        
        user = self.db.get_user_by_session(session_token)
        if user:
            # 更新Flask会话中的用户信息
            g.current_user = user
            return user
        else:
            # 会话无效，清除本地会话
            session.clear()
            return None
    
    def is_logged_in(self) -> bool:
        """检查用户是否已登录"""
        return self.get_current_user() is not None
    
    def require_login(self, f):
        """登录装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_logged_in():
                flash('请先登录', 'warning')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    
    def require_admin(self, f):
        """管理员权限装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = self.get_current_user()
            if not user:
                flash('请先登录', 'warning')
                return redirect(url_for('login', next=request.url))
            
            if not user.get('is_admin'):
                flash('需要管理员权限', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改用户密码"""
        # 验证新密码格式
        valid, msg = self.validate_password(new_password)
        if not valid:
            return False, msg
        
        # 获取用户信息验证旧密码
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False, "用户不存在"
                
                # 验证旧密码
                if not self.verify_password(old_password, row['password_hash']):
                    return False, "原密码错误"
                
                # 生成新密码哈希
                new_password_hash = self.hash_password(new_password)
                
                # 更新密码
                success = self.db.update_user_password(user_id, new_password_hash)
                if success:
                    logger.info(f"用户 {user_id} 密码修改成功")
                    return True, "密码修改成功"
                else:
                    return False, "密码更新失败"
                    
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return False, "系统错误，请稍后重试"
    
    def update_profile(self, user_id: int, email: str = None, full_name: str = None) -> Tuple[bool, str]:
        """更新用户个人资料"""
        # 验证邮箱格式
        if email is not None:
            valid, msg = self.validate_email(email)
            if not valid:
                return False, msg
        
        try:
            success = self.db.update_user_profile(user_id, email, full_name)
            if success:
                logger.info(f"用户 {user_id} 资料更新成功")
                return True, "资料更新成功"
            else:
                return False, "资料更新失败"
                
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            return False, "系统错误，请稍后重试"
    
    def cleanup_sessions(self):
        """清理过期会话"""
        try:
            cleaned = self.db.cleanup_expired_sessions()
            if cleaned > 0:
                logger.info(f"清理了 {cleaned} 个过期会话")
        except Exception as e:
            logger.error(f"清理会话失败: {e}")

# 全局认证服务实例
auth_service = AuthService()
