#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件撰写路由
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
import logging
import json
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from typing import List, Dict, Optional

from services.auth_service import auth_service
from services.email_sender import EmailSender
from models.database import Database

logger = logging.getLogger(__name__)

# 创建蓝图
compose_bp = Blueprint('compose', __name__)

# 初始化服务
email_sender = EmailSender()
db = Database()

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', '7z', 'mp3', 
    'mp4', 'avi', 'mov', 'csv'
}

# 危险文件类型黑名单
DANGEROUS_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 
    'jar', 'msi', 'dll', 'sys', 'scf', 'lnk'
}

def allowed_file(filename):
    """检查文件是否允许上传"""
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # 检查是否在危险文件黑名单中
    if ext in DANGEROUS_EXTENSIONS:
        return False
    
    # 检查是否在允许的文件类型中
    return ext in ALLOWED_EXTENSIONS

@compose_bp.route('/compose')
@auth_service.require_login
def compose_page():
    """邮件撰写页面"""
    return render_template('compose_email.html')

@compose_bp.route('/compose/reply/<int:email_id>')
@auth_service.require_login
def reply_page(email_id):
    """邮件回复页面"""
    user = auth_service.get_current_user()
    
    # 验证邮件是否属于当前用户
    email = get_user_email(user['id'], email_id)
    if not email:
        return redirect(url_for('emails'))
    
    return render_template('compose_email.html', reply_to=email_id)

@compose_bp.route('/compose/draft/<int:draft_id>')
@auth_service.require_login
def edit_draft_page(draft_id):
    """编辑草稿页面"""
    user = auth_service.get_current_user()
    
    # 验证草稿是否属于当前用户
    draft = get_user_draft(user['id'], draft_id)
    if not draft:
        return redirect(url_for('compose.compose_page'))
    
    return render_template('compose_email.html', draft_id=draft_id)

@compose_bp.route('/api/compose/send', methods=['POST'])
@auth_service.require_login
def send_email():
    """发送邮件API"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['sender_account_id', 'to_addresses', 'subject', 'body']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }), 400
        
        # 解析收件人地址
        to_addresses = [addr.strip() for addr in data['to_addresses'].split(',') if addr.strip()]
        cc_addresses = [addr.strip() for addr in data.get('cc_addresses', '').split(',') if addr.strip()]
        bcc_addresses = [addr.strip() for addr in data.get('bcc_addresses', '').split(',') if addr.strip()]
        
        if not to_addresses:
            return jsonify({
                'success': False,
                'message': '至少需要一个收件人'
            }), 400
        
        # 验证邮箱地址格式
        all_addresses = to_addresses + cc_addresses + bcc_addresses
        for addr in all_addresses:
            if not is_valid_email(addr):
                return jsonify({
                    'success': False,
                    'message': f'无效的邮箱地址: {addr}'
                }), 400
        
        # 处理附件
        attachments = []
        if data.get('attachments'):
            for att in data['attachments']:
                attachment_info = {
                    'filename': att['original_filename'],
                    'filepath': att['file_path'],
                    'content_type': att.get('content_type')
                }
                attachments.append(attachment_info)
        
        # 发送邮件
        success, message = email_sender.send_email(
            sender_account_id=int(data['sender_account_id']),
            to_addresses=to_addresses,
            subject=data['subject'],
            body=data['body'],
            cc_addresses=cc_addresses if cc_addresses else None,
            bcc_addresses=bcc_addresses if bcc_addresses else None,
            attachments=attachments if attachments else None,
            is_html=True,  # 默认使用HTML格式
            reply_to_email_id=data.get('reply_to_email_id'),
            user_id=user['id']
        )
        
        if success:
            # 删除相关的草稿和临时附件
            cleanup_after_send(user['id'], data.get('upload_session'))
            
            return jsonify({
                'success': True,
                'message': '邮件发送成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'发送邮件失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/upload-attachment', methods=['POST'])
@auth_service.require_login
def upload_attachment():
    """上传附件API"""
    try:
        user = auth_service.get_current_user()
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        file = request.files['file']
        upload_session = request.form.get('upload_session')
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400
        
        # 检查文件大小（50MB限制）
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 50 * 1024 * 1024:
            return jsonify({
                'success': False,
                'message': '文件大小超过50MB限制'
            }), 400
        
        # 创建用户上传目录
        upload_dir = f"uploads/user_{user['id']}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(upload_dir, stored_filename)
        
        # 保存文件
        file.save(file_path)
        
        # 保存附件记录到数据库
        attachment_id = save_attachment_record(
            user_id=user['id'],
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            content_type=file.content_type,
            upload_session=upload_session
        )
        
        return jsonify({
            'success': True,
            'attachment': {
                'id': attachment_id,
                'original_filename': original_filename,
                'stored_filename': stored_filename,
                'file_path': file_path,
                'file_size': file_size,
                'content_type': file.content_type
            }
        })
        
    except Exception as e:
        logger.error(f"上传附件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'上传附件失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/remove-attachment/<int:attachment_id>', methods=['DELETE'])
@auth_service.require_login
def remove_attachment(attachment_id):
    """删除附件API"""
    try:
        user = auth_service.get_current_user()
        
        # 获取附件信息
        attachment = get_user_attachment(user['id'], attachment_id)
        if not attachment:
            return jsonify({
                'success': False,
                'message': '附件不存在或无权限'
            }), 404
        
        # 删除文件
        try:
            if os.path.exists(attachment['file_path']):
                os.remove(attachment['file_path'])
        except Exception as e:
            logger.warning(f"删除附件文件失败: {e}")
        
        # 删除数据库记录
        delete_attachment_record(attachment_id)
        
        return jsonify({
            'success': True,
            'message': '附件删除成功'
        })
        
    except Exception as e:
        logger.error(f"删除附件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除附件失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/save-draft', methods=['POST'])
@auth_service.require_login
def save_draft():
    """保存草稿API"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        # 保存草稿到数据库
        draft_id = save_draft_to_db(user['id'], data)
        
        return jsonify({
            'success': True,
            'draft_id': draft_id,
            'message': '草稿保存成功'
        })
        
    except Exception as e:
        logger.error(f"保存草稿失败: {e}")
        return jsonify({
            'success': False,
            'message': f'保存草稿失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/draft/<int:draft_id>')
@auth_service.require_login
def get_draft(draft_id):
    """获取草稿API"""
    try:
        user = auth_service.get_current_user()
        
        draft = get_user_draft(user['id'], draft_id)
        if not draft:
            return jsonify({
                'success': False,
                'message': '草稿不存在或无权限'
            }), 404
        
        return jsonify({
            'success': True,
            'draft': dict(draft)
        })
        
    except Exception as e:
        logger.error(f"获取草稿失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取草稿失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/drafts')
@auth_service.require_login
def get_drafts():
    """获取用户草稿列表API"""
    try:
        user = auth_service.get_current_user()
        
        drafts = get_user_drafts(user['id'])
        
        return jsonify({
            'success': True,
            'drafts': [dict(draft) for draft in drafts]
        })
        
    except Exception as e:
        logger.error(f"获取草稿列表失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取草稿列表失败: {str(e)}'
        }), 500

# 辅助函数

def is_valid_email(email):
    """验证邮箱地址格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_user_email(user_id, email_id):
    """获取用户的邮件"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM emails 
                WHERE id = ? AND user_id = ?
            ''', (email_id, user_id))
            
            row = cursor.fetchone()
            if row:
                # 将Row对象转换为字典，确保可以使用.get()方法
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"获取用户邮件失败: {e}")
        return None

def get_user_draft(user_id, draft_id):
    """获取用户的草稿"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM email_drafts 
                WHERE id = ? AND user_id = ?
            ''', (draft_id, user_id))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"获取用户草稿失败: {e}")
        return None

def get_user_drafts(user_id, limit=50):
    """获取用户的草稿列表"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM email_drafts 
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"获取用户草稿列表失败: {e}")
        return []

def get_user_attachment(user_id, attachment_id):
    """获取用户的附件"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM email_upload_attachments 
                WHERE id = ? AND user_id = ?
            ''', (attachment_id, user_id))
            
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"获取用户附件失败: {e}")
        return None

def save_attachment_record(user_id, original_filename, stored_filename, 
                          file_path, file_size, content_type, upload_session):
    """保存附件记录到数据库"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO email_upload_attachments (
                    user_id, original_filename, stored_filename, file_path,
                    file_size, content_type, upload_session, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, original_filename, stored_filename, file_path,
                file_size, content_type, upload_session, datetime.now()
            ))
            
            attachment_id = cursor.lastrowid
            conn.commit()
            return attachment_id
    except Exception as e:
        logger.error(f"保存附件记录失败: {e}")
        raise

def delete_attachment_record(attachment_id):
    """删除附件记录"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM email_upload_attachments 
                WHERE id = ?
            ''', (attachment_id,))
            
            conn.commit()
    except Exception as e:
        logger.error(f"删除附件记录失败: {e}")
        raise

def save_draft_to_db(user_id, data):
    """保存草稿到数据库"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在草稿（基于upload_session）
            upload_session = data.get('upload_session')
            if upload_session:
                cursor.execute('''
                    SELECT id FROM email_drafts 
                    WHERE user_id = ? AND attachments LIKE ?
                ''', (user_id, f'%{upload_session}%'))
                
                existing_draft = cursor.fetchone()
                if existing_draft:
                    # 更新现有草稿
                    cursor.execute('''
                        UPDATE email_drafts SET
                            sender_account_id = ?,
                            to_addresses = ?,
                            cc_addresses = ?,
                            bcc_addresses = ?,
                            subject = ?,
                            body = ?,
                            attachments = ?,
                            is_auto_saved = ?,
                            updated_at = ?
                        WHERE id = ?
                    ''', (
                        data.get('sender_account_id'),
                        data.get('to_addresses'),
                        data.get('cc_addresses'),
                        data.get('bcc_addresses'),
                        data.get('subject'),
                        data.get('body'),
                        json.dumps(data.get('attachments', [])),
                        data.get('is_auto_saved', True),
                        datetime.now(),
                        existing_draft['id']
                    ))
                    
                    conn.commit()
                    return existing_draft['id']
            
            # 创建新草稿
            cursor.execute('''
                INSERT INTO email_drafts (
                    user_id, sender_account_id, to_addresses, cc_addresses,
                    bcc_addresses, subject, body, attachments, is_auto_saved,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('sender_account_id'),
                data.get('to_addresses'),
                data.get('cc_addresses'),
                data.get('bcc_addresses'),
                data.get('subject'),
                data.get('body'),
                json.dumps(data.get('attachments', [])),
                data.get('is_auto_saved', True),
                datetime.now(),
                datetime.now()
            ))
            
            draft_id = cursor.lastrowid
            conn.commit()
            return draft_id
            
    except Exception as e:
        logger.error(f"保存草稿到数据库失败: {e}")
        raise

def cleanup_after_send(user_id, upload_session):
    """发送成功后清理草稿和临时附件"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 删除相关草稿
            if upload_session:
                cursor.execute('''
                    DELETE FROM email_drafts 
                    WHERE user_id = ? AND attachments LIKE ?
                ''', (user_id, f'%{upload_session}%'))
            
            # 清理临时附件记录（文件保留，因为已经发送）
            if upload_session:
                cursor.execute('''
                    DELETE FROM email_upload_attachments 
                    WHERE user_id = ? AND upload_session = ?
                ''', (user_id, upload_session))
            
            conn.commit()
            
    except Exception as e:
        logger.warning(f"清理发送后数据失败: {e}")

@compose_bp.route('/api/compose/reply-data/<int:email_id>')
@auth_service.require_login
def get_reply_data(email_id):
    """获取回复邮件所需的数据"""
    try:
        user = auth_service.get_current_user()
        
        logger.info(f"用户 {user['id']} 请求获取邮件 {email_id} 的回复数据")
        
        # 获取原始邮件
        email = get_user_email(user['id'], email_id)
        if not email:
            logger.warning(f"邮件 {email_id} 不存在或用户 {user['id']} 无权限访问")
            return jsonify({
                'success': False,
                'message': '邮件不存在或无权限访问'
            }), 404
        
        logger.info(f"成功获取邮件 {email_id}，发件人: {email.get('sender', 'N/A')}")
        
        # 从sender字段中提取邮箱地址和名称
        # sender格式通常为: "Name <email@example.com>" 或 "email@example.com"
        sender = email.get('sender', '')
        import re
        
        # 尝试解析 "Name <email>" 格式
        match = re.match(r'^(.+?)\s*<(.+?)>$', sender)
        if match:
            sender_name = match.group(1).strip().strip('"')
            sender_email = match.group(2).strip()
        else:
            # 如果没有匹配，假设整个字符串就是邮箱
            sender_email = sender.strip()
            sender_name = sender_email.split('@')[0] if '@' in sender_email else sender_email
        
        # 准备回复数据
        reply_data = {
            'original_email_id': email_id,
            'original_subject': email.get('subject', ''),
            'original_sender': sender_email,
            'original_sender_name': sender_name,
            'original_date': email.get('date', ''),
            'original_body': email.get('body', ''),
            'reply_to': sender_email,
            'subject': f"Re: {email.get('subject', '')}" if not email.get('subject', '').startswith('Re:') else email.get('subject', ''),
            'quoted_body': f'''
<br><br>
<div style="border-left: 3px solid #ccc; padding-left: 10px; margin-left: 5px; color: #666;">
    <p><strong>原始邮件</strong></p>
    <p><strong>发件人:</strong> {sender_name} &lt;{sender_email}&gt;</p>
    <p><strong>日期:</strong> {email.get('date', '')}</p>
    <p><strong>主题:</strong> {email.get('subject', '')}</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">
    {email.get('body', '')}
</div>
'''
        }
        
        return jsonify({
            'success': True,
            'reply_data': reply_data
        })
        
    except Exception as e:
        logger.error(f"获取回复数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取回复数据失败: {str(e)}'
        }), 500

@compose_bp.route('/api/compose/sender-accounts')
@auth_service.require_login
def get_sender_accounts():
    """获取用户的发件人账户列表"""
    try:
        user = auth_service.get_current_user()
        
        # 获取用户的邮箱账户
        accounts = db.get_user_email_accounts(user['id'])
        
        # 格式化账户信息
        sender_accounts = []
        for account in accounts:
            if account['is_active']:  # 只返回激活的账户
                sender_accounts.append({
                    'id': account['id'],
                    'email': account['email'],
                    'provider': account['provider'],
                    'smtp_server': get_smtp_server(account['provider']),
                    'is_default': len(sender_accounts) == 0  # 第一个账户设为默认
                })
        
        return jsonify({
            'success': True,
            'accounts': sender_accounts
        })
        
    except Exception as e:
        logger.error(f"获取发件人账户失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取发件人账户失败: {str(e)}'
        }), 500

def get_smtp_server(provider):
    """根据邮件服务商返回SMTP服务器信息"""
    smtp_configs = {
        'gmail': 'smtp.gmail.com',
        'outlook': 'smtp-mail.outlook.com',
        'yahoo': 'smtp.mail.yahoo.com',
        '163': 'smtp.163.com',
        '126': 'smtp.126.com',
        'qq': 'smtp.qq.com',
        'sina': 'smtp.sina.com',
        'sohu': 'smtp.sohu.com',
        'other': '自定义SMTP'
    }
    return smtp_configs.get(provider, provider or '未知')

@compose_bp.route('/api/compose/resend', methods=['POST'])
@auth_service.require_login
def resend_email():
    """再次发送已发送的邮件"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        email_id = data.get('email_id')
        
        if not email_id:
            return jsonify({
                'success': False,
                'message': '缺少邮件ID'
            }), 400
        
        # 获取原邮件信息
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT to_addresses, cc_addresses, bcc_addresses, subject, body
                FROM sent_emails 
                WHERE id = ? AND user_id = ?
            ''', (email_id, user['id']))
            
            email_data = cursor.fetchone()
            if not email_data:
                return jsonify({
                    'success': False,
                    'message': '邮件不存在或无权限访问'
                }), 404
        
        # 准备发送数据
        email_dict = dict(email_data)
        
        # 发送邮件
        email_sender = EmailSender()
        success, message = email_sender.send_email(
            user_id=user['id'],
            to_addresses=email_dict['to_addresses'],
            cc_addresses=email_dict['cc_addresses'],
            bcc_addresses=email_dict['bcc_addresses'],
            subject=email_dict['subject'],
            body=email_dict['body'],
            attachments=None  # 再次发送时不包含附件
        )
        
        if success:
            logger.info(f"用户 {user['username']} 成功再次发送邮件: {email_dict['subject']}")
            return jsonify({
                'success': True,
                'message': '邮件已成功再次发送'
            })
        else:
            logger.error(f"用户 {user['username']} 再次发送邮件失败: {message}")
            return jsonify({
                'success': False,
                'message': f'发送失败: {message}'
            }), 500
            
    except Exception as e:
        logger.error(f"再次发送邮件异常: {e}")
        return jsonify({
            'success': False,
            'message': f'系统错误: {str(e)}'
        }), 500

# 注册蓝图到主应用
def register_compose_routes(app):
    """注册邮件撰写路由到Flask应用"""
    app.register_blueprint(compose_bp)
