#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件回复功能路由
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
import re

from services.auth_service import auth_service
from models.database import Database

logger = logging.getLogger(__name__)

# 创建蓝图
reply_bp = Blueprint('reply', __name__, url_prefix='/api/emails')

# 初始化数据库
db = Database()

@reply_bp.route('/<int:email_id>/reply-data')
@auth_service.require_login
def get_reply_data(email_id):
    """获取邮件回复数据API"""
    try:
        user = auth_service.get_current_user()
        
        # 获取原始邮件
        email = get_user_email(user['id'], email_id)
        if not email:
            return jsonify({
                'success': False,
                'message': '邮件不存在或无权限'
            }), 404
        
        # 构建回复数据 - 将Row对象转换为字典
        email_dict = dict(email)
        reply_data = {
            'id': email_dict['id'],
            'subject': email_dict['subject'],
            'sender': email_dict['sender'],
            'date': email_dict['date'],
            'body': email_dict['body'],
            'body_html': email_dict.get('body_html'),
            'message_id': email_dict.get('message_id'),
            'recipients': parse_recipients(email_dict.get('recipients', '')),
            'cc_recipients': parse_recipients(email_dict.get('cc', '')),
            'reply_to': extract_reply_to_address(email_dict['sender']),
            'reply_all_recipients': get_reply_all_recipients(email_dict)
        }
        
        return jsonify({
            'success': True,
            'email': reply_data
        })
        
    except Exception as e:
        logger.error(f"获取回复数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取回复数据失败: {str(e)}'
        }), 500

@reply_bp.route('/<int:email_id>/forward-data')
@auth_service.require_login
def get_forward_data(email_id):
    """获取邮件转发数据API"""
    try:
        user = auth_service.get_current_user()
        
        # 获取原始邮件
        email = get_user_email(user['id'], email_id)
        if not email:
            return jsonify({
                'success': False,
                'message': '邮件不存在或无权限'
            }), 404
        
        # 构建转发数据 - 将Row对象转换为字典
        email_dict = dict(email)
        forward_data = {
            'id': email_dict['id'],
            'subject': email_dict['subject'],
            'sender': email_dict['sender'],
            'recipients': email_dict.get('recipients', ''),
            'cc': email_dict.get('cc', ''),
            'date': email_dict['date'],
            'body': email_dict['body'],
            'body_html': email_dict.get('body_html'),
            'attachments': parse_attachments(email_dict.get('attachments')),
            'forward_content': generate_forward_content(email_dict)
        }
        
        return jsonify({
            'success': True,
            'email': forward_data
        })
        
    except Exception as e:
        logger.error(f"获取转发数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取转发数据失败: {str(e)}'
        }), 500

@reply_bp.route('/<int:email_id>/quick-reply', methods=['POST'])
@auth_service.require_login
def quick_reply(email_id):
    """快速回复API"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('body'):
            return jsonify({
                'success': False,
                'message': '回复内容不能为空'
            }), 400
        
        # 获取原始邮件
        email = get_user_email(user['id'], email_id)
        if not email:
            return jsonify({
                'success': False,
                'message': '邮件不存在或无权限'
            }), 404
        
        # 获取用户的默认发件账户
        sender_account = get_user_default_sender_account(user['id'])
        if not sender_account:
            return jsonify({
                'success': False,
                'message': '未找到可用的发件账户'
            }), 400
        
        # 构建回复邮件数据 - 将Row对象转换为字典
        email_dict = dict(email)
        reply_subject = generate_reply_subject(email_dict['subject'])
        reply_body = generate_quick_reply_body(data['body'], email_dict)
        reply_to = extract_reply_to_address(email_dict['sender'])
        
        # 使用邮件发送服务发送回复
        from services.email_sender import EmailSender
        email_sender = EmailSender()
        
        success, message = email_sender.send_email(
            sender_account_id=sender_account['id'],
            to_addresses=[reply_to],
            subject=reply_subject,
            body=reply_body,
            is_html=True,
            reply_to_email_id=email_id,
            user_id=user['id']
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '回复发送成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'回复发送失败: {message}'
            }), 500
            
    except Exception as e:
        logger.error(f"快速回复失败: {e}")
        return jsonify({
            'success': False,
            'message': f'快速回复失败: {str(e)}'
        }), 500

@reply_bp.route('/templates')
@auth_service.require_login
def get_reply_templates():
    """获取回复模板API"""
    try:
        user = auth_service.get_current_user()
        
        # 获取用户自定义模板
        custom_templates = get_user_reply_templates(user['id'])
        
        # 系统默认模板
        default_templates = [
            {
                'id': 'thanks',
                'name': '感谢回复',
                'content': '感谢您的邮件。我已收到并会尽快处理。',
                'is_default': True
            },
            {
                'id': 'received',
                'name': '确认收到',
                'content': '您好，我已收到您的邮件，会在24小时内回复您。',
                'is_default': True
            },
            {
                'id': 'meeting',
                'name': '会议安排',
                'content': '关于您提到的会议，我的时间安排如下：\n\n请告知您方便的时间。',
                'is_default': True
            },
            {
                'id': 'follow_up',
                'name': '跟进回复',
                'content': '感谢您的耐心等待。关于您的问题，现在有了进展：\n\n',
                'is_default': True
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': {
                'default': default_templates,
                'custom': [dict(t) for t in custom_templates]
            }
        })
        
    except Exception as e:
        logger.error(f"获取回复模板失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取回复模板失败: {str(e)}'
        }), 500

@reply_bp.route('/templates', methods=['POST'])
@auth_service.require_login
def save_reply_template():
    """保存回复模板API"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('name') or not data.get('content'):
            return jsonify({
                'success': False,
                'message': '模板名称和内容不能为空'
            }), 400
        
        # 保存模板
        template_id = save_user_reply_template(
            user_id=user['id'],
            name=data['name'],
            content=data['content']
        )
        
        return jsonify({
            'success': True,
            'template_id': template_id,
            'message': '模板保存成功'
        })
        
    except Exception as e:
        logger.error(f"保存回复模板失败: {e}")
        return jsonify({
            'success': False,
            'message': f'保存回复模板失败: {str(e)}'
        }), 500

# 辅助函数

def get_user_email(user_id, email_id):
    """获取用户的邮件"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM emails 
                WHERE id = ? AND user_id = ?
            ''', (email_id, user_id))
            
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"获取用户邮件失败: {e}")
        return None

def get_user_default_sender_account(user_id):
    """获取用户的默认发件账户"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM email_accounts 
                WHERE user_id = ? AND is_active = 1
                ORDER BY id ASC
                LIMIT 1
            ''', (user_id,))
            
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"获取默认发件账户失败: {e}")
        return None

def get_user_reply_templates(user_id):
    """获取用户的回复模板"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reply_templates 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"获取回复模板失败: {e}")
        return []

def save_user_reply_template(user_id, name, content):
    """保存用户回复模板"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reply_templates (user_id, name, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, name, content, datetime.now()))
            
            template_id = cursor.lastrowid
            conn.commit()
            return template_id
    except Exception as e:
        logger.error(f"保存回复模板失败: {e}")
        raise

def parse_recipients(recipients_str):
    """解析收件人字符串"""
    if not recipients_str:
        return []
    
    # 简单的邮箱地址提取
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, recipients_str)
    return emails

def parse_attachments(attachments_json):
    """解析附件JSON数据"""
    if not attachments_json:
        return []
    
    try:
        import json
        return json.loads(attachments_json)
    except:
        return []

def extract_reply_to_address(sender):
    """提取回复地址"""
    # 从发件人字符串中提取邮箱地址
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, sender)
    return emails[0] if emails else sender

def get_reply_all_recipients(email):
    """获取全部回复的收件人列表"""
    recipients = []
    
    # 确保email是字典类型
    if hasattr(email, 'keys'):
        email_dict = dict(email) if not isinstance(email, dict) else email
    else:
        email_dict = email
    
    # 添加原发件人
    sender_email = extract_reply_to_address(email_dict['sender'])
    if sender_email:
        recipients.append(sender_email)
    
    # 添加原收件人（排除当前用户）
    original_recipients = parse_recipients(email_dict.get('recipients', ''))
    recipients.extend(original_recipients)
    
    # 添加原抄送人
    cc_recipients = parse_recipients(email_dict.get('cc', ''))
    recipients.extend(cc_recipients)
    
    # 去重并返回
    return list(set(recipients))

def generate_reply_subject(original_subject):
    """生成回复主题"""
    if not original_subject:
        return "Re: "
    
    # 如果已经有Re:前缀，不重复添加
    if original_subject.lower().startswith('re:'):
        return original_subject
    
    return f"Re: {original_subject}"

def generate_forward_subject(original_subject):
    """生成转发主题"""
    if not original_subject:
        return "Fwd: "
    
    # 如果已经有Fwd:前缀，不重复添加
    if original_subject.lower().startswith('fwd:'):
        return original_subject
    
    return f"Fwd: {original_subject}"

def generate_quick_reply_body(reply_content, original_email):
    """生成快速回复的邮件正文"""
    # 确保original_email是字典类型
    if hasattr(original_email, 'keys'):
        email_dict = dict(original_email) if not isinstance(original_email, dict) else original_email
    else:
        email_dict = original_email
        
    date_str = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    sender = email_dict['sender']
    
    # 获取原邮件内容（优先使用HTML格式）
    original_content = email_dict.get('body_html') or email_dict.get('body', '')
    
    reply_body = f"""
    <div style="font-family: Arial, sans-serif; font-size: 14px;">
        <p>{reply_content}</p>
        <br>
        <div style="border-left: 3px solid #ccc; padding-left: 15px; margin-left: 0; color: #666;">
            <p><strong>在 {date_str}，{sender} 写道：</strong></p>
            <div>{original_content}</div>
        </div>
    </div>
    """
    
    return reply_body

def generate_forward_content(email):
    """生成转发邮件内容"""
    # 确保email是字典类型
    if hasattr(email, 'keys'):
        email_dict = dict(email) if not isinstance(email, dict) else email
    else:
        email_dict = email
        
    try:
        if email_dict['date']:
            # 尝试多种日期格式解析
            date_obj = None
            if isinstance(email_dict['date'], str):
                # 尝试ISO格式
                try:
                    date_obj = datetime.fromisoformat(email_dict['date'].replace('Z', '+00:00'))
                except:
                    # 尝试其他常见格式
                    try:
                        date_obj = datetime.strptime(email_dict['date'], '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
            
            date_str = date_obj.strftime('%Y年%m月%d日 %H:%M') if date_obj else email_dict['date']
        else:
            date_str = '未知时间'
    except:
        date_str = '未知时间'
    
    forward_header = f"""
    <div style="font-family: Arial, sans-serif; font-size: 14px; border-left: 3px solid #007bff; padding-left: 15px; margin: 20px 0;">
        <p><strong>---------- 转发邮件 ----------</strong></p>
        <p><strong>发件人：</strong> {email_dict['sender']}</p>
        <p><strong>收件人：</strong> {email_dict.get('recipients', '')}</p>
        {f"<p><strong>抄送：</strong> {email_dict['cc']}</p>" if email_dict.get('cc') else ''}
        <p><strong>发送时间：</strong> {date_str}</p>
        <p><strong>主题：</strong> {email_dict['subject']}</p>
        <br>
        <div>{email_dict.get('body_html') or email_dict.get('body', '')}</div>
    </div>
    """
    
    return forward_header

# 注册蓝图到主应用
def register_reply_routes(app):
    """注册邮件回复路由到Flask应用"""
    app.register_blueprint(reply_bp)
