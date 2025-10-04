#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件发送服务
支持多种邮件服务商的SMTP发送功能
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from datetime import datetime
import logging
from typing import List, Dict, Tuple, Optional
import os
import mimetypes
import json

from config import Config
from models.database import Database

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.db = Database()
    
    def send_email(self, 
                   sender_account_id: int,
                   to_addresses: List[str],
                   subject: str,
                   body: str,
                   cc_addresses: List[str] = None,
                   bcc_addresses: List[str] = None,
                   attachments: List[Dict] = None,
                   is_html: bool = False,
                   reply_to_email_id: int = None,
                   user_id: int = None) -> Tuple[bool, str]:
        """
        发送邮件
        
        Args:
            sender_account_id: 发送者账户ID
            to_addresses: 收件人列表
            subject: 邮件主题
            body: 邮件正文
            cc_addresses: 抄送列表
            bcc_addresses: 密送列表
            attachments: 附件列表 [{'filename': str, 'filepath': str, 'content_type': str}]
            is_html: 是否为HTML格式
            reply_to_email_id: 回复的邮件ID（用于线程追踪）
            user_id: 用户ID（权限验证）
            
        Returns:
            (success: bool, message: str)
        """
        smtp_server = None
        try:
            # 获取发送者账户信息
            account = self._get_sender_account(sender_account_id, user_id)
            if not account:
                return False, "发送者账户不存在或无权限"
            
            # 获取SMTP配置
            smtp_config = Config.get_email_provider_config(account['provider'])
            if not smtp_config:
                return False, f"不支持的邮件服务商: {account['provider']}"
            
            # 创建邮件对象
            msg = self._create_email_message(
                sender_email=account['email'],
                to_addresses=to_addresses,
                subject=subject,
                body=body,
                cc_addresses=cc_addresses,
                bcc_addresses=bcc_addresses,
                is_html=is_html,
                reply_to_email_id=reply_to_email_id
            )
            
            # 添加附件
            if attachments:
                success, error_msg = self._add_attachments(msg, attachments, user_id)
                if not success:
                    return False, error_msg
            
            # 建立SMTP连接并发送
            smtp_server = self._create_smtp_connection(smtp_config)
            if not smtp_server:
                return False, "无法建立SMTP连接"
            
            # 登录SMTP服务器
            login_success, login_msg = self._smtp_login(smtp_server, account)
            if not login_success:
                return False, login_msg
            
            # 发送邮件
            all_recipients = to_addresses + (cc_addresses or []) + (bcc_addresses or [])
            smtp_server.send_message(msg, to_addrs=all_recipients)
            
            # 保存发送记录
            self._save_sent_email(
                user_id=user_id,
                sender_account_id=sender_account_id,
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                bcc_addresses=bcc_addresses,
                subject=subject,
                body=body,
                attachments=attachments,
                reply_to_email_id=reply_to_email_id
            )
            
            logger.info(f"邮件发送成功: {account['email']} -> {', '.join(to_addresses)}")
            return True, "邮件发送成功"
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False, f"邮件发送失败: {str(e)}"
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                except:
                    pass
    
    def _get_sender_account(self, account_id: int, user_id: int) -> Optional[Dict]:
        """获取发送者账户信息"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, email, password, provider, is_active
                    FROM email_accounts 
                    WHERE id = ? AND user_id = ? AND is_active = 1
                ''', (account_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"获取发送者账户失败: {e}")
            return None
    
    def _create_email_message(self, 
                             sender_email: str,
                             to_addresses: List[str],
                             subject: str,
                             body: str,
                             cc_addresses: List[str] = None,
                             bcc_addresses: List[str] = None,
                             is_html: bool = False,
                             reply_to_email_id: int = None) -> MIMEMultipart:
        """创建邮件消息对象"""
        
        msg = MIMEMultipart('alternative')
        
        # 设置邮件头
        msg['From'] = sender_email
        msg['To'] = ', '.join(to_addresses)
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
        
        # 处理主题编码
        msg['Subject'] = Header(subject, 'utf-8')
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # 如果是回复邮件，添加相关头信息
        if reply_to_email_id:
            original_email = self._get_original_email(reply_to_email_id)
            if original_email:
                # 添加In-Reply-To和References头
                if original_email.get('message_id'):
                    msg['In-Reply-To'] = original_email['message_id']
                    msg['References'] = original_email['message_id']
        
        # 添加邮件正文
        if is_html:
            # HTML格式
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 同时添加纯文本版本（从HTML转换）
            plain_text = self._html_to_text(body)
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            msg.attach(text_part)
        else:
            # 纯文本格式
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
        
        return msg
    
    def _add_attachments(self, msg: MIMEMultipart, attachments: List[Dict], user_id: int) -> Tuple[bool, str]:
        """添加附件到邮件"""
        try:
            for attachment in attachments:
                filepath = attachment.get('filepath')
                filename = attachment.get('filename')
                
                if not filepath or not os.path.exists(filepath):
                    return False, f"附件文件不存在: {filename}"
                
                # 安全检查：验证文件路径
                if not self._validate_attachment_path(filepath, user_id):
                    return False, f"附件路径不安全: {filename}"
                
                # 检查文件大小（最大50MB）
                file_size = os.path.getsize(filepath)
                if file_size > 50 * 1024 * 1024:
                    return False, f"附件过大: {filename} ({file_size / 1024 / 1024:.1f}MB)"
                
                # 读取文件并添加到邮件
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                
                # 设置附件头信息
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                
                # 设置MIME类型
                content_type = attachment.get('content_type')
                if not content_type:
                    content_type, _ = mimetypes.guess_type(filename)
                    if content_type:
                        main_type, sub_type = content_type.split('/', 1)
                        part.set_type(f"{main_type}/{sub_type}")
                
                msg.attach(part)
            
            return True, ""
            
        except Exception as e:
            logger.error(f"添加附件失败: {e}")
            return False, f"添加附件失败: {str(e)}"
    
    def _validate_attachment_path(self, filepath: str, user_id: int) -> bool:
        """验证附件路径安全性"""
        try:
            # 检查路径是否在用户的上传目录内
            user_upload_dir = f"uploads/user_{user_id}/"
            abs_filepath = os.path.abspath(filepath)
            abs_upload_dir = os.path.abspath(user_upload_dir)
            
            return abs_filepath.startswith(abs_upload_dir)
        except:
            return False
    
    def _create_smtp_connection(self, smtp_config: Dict):
        """创建SMTP连接"""
        try:
            if smtp_config['use_ssl']:
                # 使用SSL连接
                context = ssl.create_default_context()
                if smtp_config['smtp_port'] == 465:
                    # SSL连接
                    smtp_server = smtplib.SMTP_SSL(
                        smtp_config['smtp_host'], 
                        smtp_config['smtp_port'],
                        context=context
                    )
                else:
                    # STARTTLS连接
                    smtp_server = smtplib.SMTP(
                        smtp_config['smtp_host'], 
                        smtp_config['smtp_port']
                    )
                    smtp_server.starttls(context=context)
            else:
                smtp_server = smtplib.SMTP(
                    smtp_config['smtp_host'], 
                    smtp_config['smtp_port']
                )
            
            return smtp_server
            
        except Exception as e:
            logger.error(f"创建SMTP连接失败: {e}")
            return None
    
    def _smtp_login(self, smtp_server, account: Dict) -> Tuple[bool, str]:
        """SMTP服务器登录"""
        try:
            smtp_server.login(account['email'], account['password'])
            return True, "登录成功"
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP认证失败: {str(e)}"
            if account['provider'].lower() in ['126', '163']:
                error_msg += "\n提示：请确认使用的是客户端授权密码，而不是邮箱登录密码"
            return False, error_msg
        except Exception as e:
            return False, f"SMTP登录失败: {str(e)}"
    
    def _get_original_email(self, email_id: int) -> Optional[Dict]:
        """获取原始邮件信息（用于回复）"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT message_id, subject, sender, body
                    FROM emails 
                    WHERE id = ?
                ''', (email_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"获取原始邮件失败: {e}")
            return None
    
    def _html_to_text(self, html: str) -> str:
        """将HTML转换为纯文本"""
        try:
            from html2text import html2text
            return html2text(html)
        except ImportError:
            # 简单的HTML标签移除
            import re
            text = re.sub(r'<[^>]+>', '', html)
            return text.strip()
    
    def _save_sent_email(self, 
                        user_id: int,
                        sender_account_id: int,
                        to_addresses: List[str],
                        cc_addresses: List[str],
                        bcc_addresses: List[str],
                        subject: str,
                        body: str,
                        attachments: List[Dict],
                        reply_to_email_id: int = None):
        """保存发送的邮件记录"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 准备附件信息
                attachments_json = json.dumps(attachments) if attachments else None
                
                cursor.execute('''
                    INSERT INTO sent_emails (
                        user_id, sender_account_id, to_addresses, cc_addresses, 
                        bcc_addresses, subject, body, attachments, reply_to_email_id,
                        sent_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    sender_account_id,
                    ', '.join(to_addresses),
                    ', '.join(cc_addresses) if cc_addresses else None,
                    ', '.join(bcc_addresses) if bcc_addresses else None,
                    subject,
                    body,
                    attachments_json,
                    reply_to_email_id,
                    datetime.now(),
                    datetime.now()
                ))
                
                conn.commit()
                logger.info(f"已保存发送邮件记录: 用户{user_id}")
                
        except Exception as e:
            logger.error(f"保存发送邮件记录失败: {e}")

    def get_user_sent_emails(self, user_id: int, limit: int = 50) -> List[Dict]:
        """获取用户的发送邮件记录"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT se.*, ea.email as sender_email
                    FROM sent_emails se
                    LEFT JOIN email_accounts ea ON se.sender_account_id = ea.id
                    WHERE se.user_id = ?
                    ORDER BY se.sent_at DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取发送邮件记录失败: {e}")
            return []

    def test_smtp_connection(self, email: str, password: str, provider: str) -> Tuple[bool, str]:
        """测试SMTP连接"""
        smtp_server = None
        try:
            smtp_config = Config.get_email_provider_config(provider)
            if not smtp_config:
                return False, f"不支持的邮件服务商: {provider}"
            
            smtp_server = self._create_smtp_connection(smtp_config)
            if not smtp_server:
                return False, "无法建立SMTP连接"
            
            # 测试登录
            account = {'email': email, 'password': password, 'provider': provider}
            success, message = self._smtp_login(smtp_server, account)
            
            if success:
                return True, "SMTP连接测试成功"
            else:
                return False, message
                
        except Exception as e:
            return False, f"SMTP连接测试失败: {str(e)}"
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                except:
                    pass
