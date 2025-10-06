#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 邮件管理器
支持多种邮件服务商的邮件收取
"""

import imaplib
import email
import ssl
from email.header import decode_header
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Tuple, Optional
import base64
import os
import uuid
import json

from config import Config
from models.database import Database
from services.forward_detector import ForwardDetector

logger = logging.getLogger(__name__)

class EmailManager:
    def __init__(self):
        self.db = Database()
        # 延迟导入分类服务，避免循环导入
        self._classification_service = None
        # 转发检测器
        self.forward_detector = ForwardDetector()
    
    @property
    def classification_service(self):
        """延迟加载分类服务"""
        if self._classification_service is None:
            from services.classification_service import ClassificationService
            self._classification_service = ClassificationService()
        return self._classification_service
        
    def get_configured_accounts(self) -> List[Dict]:
        """获取已配置的邮箱账户"""
        accounts = self.db.get_email_accounts()
        result = []
        
        for account in accounts:
            if account['is_active']:
                # 获取密码（实际部署时应该加密存储）
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT password FROM email_accounts WHERE id = ?', (account['id'],))
                    row = cursor.fetchone()
                    if row:
                        account['password'] = row['password']
                        result.append(account)
        
        return result
    
    def add_account(self, email: str, password: str, provider: str) -> bool:
        """添加邮箱账户"""
        # 新浪邮箱智能识别：根据邮箱地址自动选择正确的服务器配置
        if provider.lower() == 'sina':
            detected_provider = Config.detect_email_provider(email)
            if detected_provider and 'sina' in detected_provider:
                provider = detected_provider
                logger.info(f"新浪邮箱智能识别：{email} → 使用配置 {provider}")
            else:
                logger.error(f"无法识别新浪邮箱域名：{email}")
                return False
        
        return self.db.save_email_account(email, password, provider)
    
    def test_connection(self, email: str, password: str, provider: str) -> Tuple[bool, str]:
        """测试邮箱连接"""
        imap_server = None
        try:
            # 新浪邮箱智能识别：根据邮箱地址自动选择正确的服务器配置
            if provider.lower() == 'sina':
                detected_provider = Config.detect_email_provider(email)
                if detected_provider and 'sina' in detected_provider:
                    provider = detected_provider
                    logger.info(f"新浪邮箱智能识别：{email} → 使用配置 {provider}")
                else:
                    # 如果自动识别失败，提示用户
                    return False, (f"无法识别新浪邮箱域名。\n"
                                 f"支持的域名：@sina.com, @sina.cn, @vip.sina.com, @vip.sina.cn\n"
                                 f"您的邮箱：{email}")
            
            config = Config.get_email_provider_config(provider)
            if not config:
                return False, f"不支持的邮件服务商: {provider}"
            
            # 126邮箱连接前的特别提示
            if provider.lower() == '126':
                logger.info(f"准备连接126邮箱，配置信息：IMAP: {config['imap_host']}:{config['imap_port']} (SSL={config['use_ssl']})")
            
            # 创建IMAP连接
            if config['use_ssl']:
                imap_server = imaplib.IMAP4_SSL(config['imap_host'], config['imap_port'])
            else:
                imap_server = imaplib.IMAP4(config['imap_host'], config['imap_port'])
            
            # 对于126邮箱，需要设置特殊的连接参数
            if provider.lower() == '126':
                # 设置连接超时
                imap_server.sock.settimeout(30)
                # 尝试发送CAPABILITY命令确认连接状态
                try:
                    imap_server.capability()
                except Exception as e:
                    logger.warning(f"126邮箱CAPABILITY检查失败: {e}")
            
            # 尝试登录
            logger.info(f"尝试登录126邮箱: {email}")
            login_result = imap_server.login(email, password)
            logger.info(f"126邮箱登录结果: {login_result}")
            
            if login_result[0] != 'OK':
                if 'unsafe login' in str(login_result[1]).lower() or 'authorization failed' in str(login_result[1]).lower():
                    return False, ("登录失败: 126邮箱安全策略限制。\n\n"
                                 "请确认以下步骤：\n"
                                 "1. 已在网页版邮箱开启【IMAP/SMTP服务】\n"
                                 "2. 已设置【客户端授权密码】\n"
                                 "3. 使用授权密码而非登录密码\n"
                                 "4. 服务器配置：IMAP: imap.126.com:993 (SSL)")
                return False, f"登录失败: {login_result[1]}"
            
            # 对于126/163邮箱，登录成功后必须发送ID命令（官方要求）
            # 参考：https://www.ietf.org/rfc/rfc2971.txt
            # Java示例：store.id(HashMap) - 在登录后调用
            if provider.lower() in ['126', '163']:
                try:
                    logger.info(f"{provider}邮箱登录成功，发送IMAP ID信息（官方要求）...")
                    
                    # 方法1：尝试使用_command方法（最标准）
                    try:
                        # ID命令参数：NIL 或 (key value key value ...)
                        # 根据RFC 2971，参数格式为：("key1" "value1" "key2" "value2")
                        typ, dat = imap_server._command('ID', '("name" "EmailDigestSystem" "version" "1.0.0" "vendor" "EmailDigest")')
                        logger.info(f"✅ IMAP ID命令成功（_command方法）: {typ}, {dat}")
                        if typ != 'OK':
                            logger.warning(f"ID命令返回非OK状态: {typ}")
                    except Exception as e1:
                        logger.info(f"_command方法不可用（正常情况），使用备用方法...")
                        
                        # 方法2：手动构造完整的IMAP命令
                        try:
                            # 获取新标签
                            tag = imap_server._new_tag().decode()
                            # 构造ID命令：TAG ID ("key" "value" ...)
                            id_line = f'{tag} ID ("name" "EmailDigestSystem" "version" "1.0.0" "vendor" "EmailDigest" "support-email" "support@emaildigest.com")\r\n'
                            logger.info(f"发送ID命令: {id_line.strip()}")
                            
                            # 发送命令
                            imap_server.send(id_line.encode('utf-8'))
                            
                            # 读取响应
                            response_lines = []
                            while True:
                                line = imap_server.readline().decode('utf-8', errors='ignore')
                                response_lines.append(line.strip())
                                logger.info(f"ID响应: {line.strip()}")
                                
                                # 检查是否是标签响应（完成响应）
                                if line.startswith(tag):
                                    if ' OK ' in line or ' NO ' in line or ' BAD ' in line:
                                        if ' OK ' in line:
                                            logger.info(f"✅ IMAP ID命令成功（手动方法）")
                                        else:
                                            logger.warning(f"ID命令未成功: {line.strip()}")
                                        break
                                
                                # 防止无限循环
                                if len(response_lines) > 10:
                                    logger.warning("ID命令响应过多，停止读取")
                                    break
                                    
                        except Exception as e2:
                            logger.error(f"手动发送ID命令失败: {e2}")
                            
                except Exception as e:
                    logger.error(f"ID命令发送过程出错: {e}")
                    logger.warning("⚠️ ID命令失败可能导致收件箱访问被拒绝（Unsafe Login）")
            
            # 选择收件箱
            logger.info("尝试选择收件箱...")
            select_result = imap_server.select('INBOX')
            logger.info(f"选择收件箱结果: {select_result}")
            
            if select_result[0] != 'OK':
                error_msg = str(select_result[1])
                logger.error(f"选择收件箱失败，详细错误: {error_msg}")
                
                if 'unsafe login' in error_msg.lower() or 'authorization failed' in error_msg.lower():
                    return False, ("选择收件箱失败: 126邮箱安全策略限制。\n\n"
                                 "❌ 错误详情: " + error_msg + "\n\n"
                                 "🔧 解决方案：\n"
                                 "1. 登录 https://mail.126.com\n"
                                 "2. 进入【设置】→【POP3/SMTP/IMAP】\n"
                                 "3. 关闭IMAP服务，等待10秒\n"
                                 "4. 重新开启【IMAP/SMTP服务（SSL）】\n"
                                 "5. 确保选择【允许客户端收取邮件】\n"
                                 "6. 重新设置客户端授权密码\n"
                                 "7. 使用新的授权密码重试")
                
                return False, f"无法选择收件箱: {error_msg}\n\n建议：尝试在126邮箱设置中重新开启IMAP服务，并确保选择了【允许客户端收取】选项"
            
            # 测试获取邮件数量（使用更安全的搜索方式）
            try:
                status, messages = imap_server.search(None, 'ALL')
                if status == 'OK':
                    count = len(messages[0].split()) if messages[0] else 0
                    success_msg = f"✅ 连接成功！收件箱有 {count} 封邮件"
                    if provider.lower() == '126':
                        success_msg += f"\n\n服务器配置：\n• IMAP: {config['imap_host']}:{config['imap_port']} (SSL)\n• SMTP: {config['smtp_host']}:{config['smtp_port']} (SSL)"
                    return True, success_msg
                else:
                    # 如果搜索失败，至少确认连接和选择收件箱成功
                    return True, "连接成功，但无法获取邮件数量（可能是权限限制）"
            except Exception as search_error:
                # 搜索失败不影响基本连接测试
                return True, f"连接成功，但搜索功能受限: {str(search_error)}"
                
        except imaplib.IMAP4.error as e:
            error_msg = str(e).lower()
            if 'auth' in error_msg or 'login' in error_msg:
                if provider.lower() == '126':
                    return False, ("126邮箱认证失败！\n\n"
                                 "❌ 常见问题排查：\n"
                                 "1. 【必须】使用客户端授权密码，不能使用登录密码\n"
                                 "2. 【必须】在网页版邮箱开启 IMAP/SMTP 服务\n"
                                 "3. 检查授权密码是否复制完整（无多余空格）\n"
                                 "4. 尝试重新生成授权密码\n\n"
                                 f"详细错误: {str(e)}")
                else:
                    return False, f"认证失败，请检查邮箱地址和授权码是否正确。详细: {str(e)}"
            else:
                return False, f"IMAP错误: {str(e)}"
        except Exception as e:
            error_msg = str(e).lower()
            if 'timeout' in error_msg:
                return False, f"连接超时，请检查网络连接。建议：\n1. 检查防火墙设置\n2. 确认可以访问 {config['imap_host']}\n3. 检查端口 {config['imap_port']} 是否被屏蔽"
            elif 'refused' in error_msg:
                return False, f"连接被拒绝。服务器配置：{config['imap_host']}:{config['imap_port']}\n请检查：\n1. 服务器地址和端口是否正确\n2. 网络是否允许SSL连接"
            else:
                if provider.lower() == '126':
                    return False, f"126邮箱连接失败: {str(e)}\n\n请确认：\n• 已开启IMAP服务\n• 使用客户端授权密码\n• 网络正常"
                else:
                    return False, f"连接失败: {str(e)}"
        finally:
            # 确保连接被正确关闭
            if imap_server:
                try:
                    imap_server.logout()
                except:
                    pass
    
    def _decode_mime_words(self, s: str) -> str:
        """解码MIME编码的字符串"""
        if not s:
            return ""
        
        try:
            decoded_fragments = decode_header(s)
            fragments = []
            
            for fragment, encoding in decoded_fragments:
                if isinstance(fragment, bytes):
                    if encoding:
                        try:
                            fragment = fragment.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            # 如果指定编码失败，尝试其他编码
                            for fallback_encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                                try:
                                    fragment = fragment.decode(fallback_encoding)
                                    break
                                except (UnicodeDecodeError, LookupError):
                                    continue
                            else:
                                fragment = fragment.decode('utf-8', errors='ignore')
                    else:
                        fragment = fragment.decode('utf-8', errors='ignore')
                fragments.append(str(fragment))
            
            return ''.join(fragments)
        except Exception as e:
            logger.warning(f"解码MIME字符串失败: {e}")
            return str(s)
    
    def _get_email_body(self, msg) -> Tuple[str, str]:
        """提取邮件正文"""
        body = ""
        body_html = ""
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # 跳过附件
                    if "attachment" in content_disposition:
                        continue
                    
                    try:
                        charset = part.get_content_charset()
                        payload = part.get_payload(decode=True)
                        
                        if payload:
                            # 尝试解码
                            if charset:
                                try:
                                    text = payload.decode(charset)
                                except (UnicodeDecodeError, LookupError):
                                    # 编码失败时尝试其他编码
                                    for fallback_charset in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                                        try:
                                            text = payload.decode(fallback_charset)
                                            break
                                        except (UnicodeDecodeError, LookupError):
                                            continue
                                    else:
                                        text = payload.decode('utf-8', errors='ignore')
                            else:
                                text = payload.decode('utf-8', errors='ignore')
                            
                            if content_type == "text/plain":
                                body += text
                            elif content_type == "text/html":
                                body_html += text
                                
                    except Exception as e:
                        logger.warning(f"解析邮件部分失败: {e}")
                        continue
            else:
                # 单部分邮件
                charset = msg.get_content_charset()
                payload = msg.get_payload(decode=True)
                
                if payload:
                    if charset:
                        try:
                            body = payload.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            body = payload.decode('utf-8', errors='ignore')
                    else:
                        body = payload.decode('utf-8', errors='ignore')
        
        except Exception as e:
            logger.error(f"提取邮件正文失败: {e}")
        
        return body.strip(), body_html.strip()
    
    def _extract_attachments(self, msg, email_id: str, user_id: int) -> List[Dict]:
        """提取邮件附件"""
        attachments = []
        
        if not msg.is_multipart():
            return attachments
        
        # 创建用户专用的附件目录
        user_attachment_dir = os.path.join('email_attachments', f'user_{user_id}')
        os.makedirs(user_attachment_dir, exist_ok=True)
        
        # 危险文件类型黑名单
        dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.jar',
            '.msi', '.dll', '.sys', '.drv', '.ocx', '.cpl', '.inf', '.reg', '.ps1'
        }
        
        # 允许的文件类型白名单
        allowed_extensions = {
            # 文档类型
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.rtf', '.csv', '.xml', '.json', '.md', '.html', '.htm',
            
            # 图片类型
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico',
            
            # 音视频类型
            '.mp3', '.wav', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.m4a', '.aac',
            
            # 压缩文件
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            
            # 日历和联系人文件
            '.ics', '.vcf', '.vcard',
            
            # 代码和配置文件
            '.py', '.js', '.css', '.sql', '.log', '.conf', '.ini', '.cfg',
            
            # 其他常用格式
            '.eml', '.msg', '.mbox'  # 邮件格式
        }
        
        # 最大文件大小限制 (50MB)
        max_file_size = 50 * 1024 * 1024
        
        try:
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                content_type = part.get_content_type()
                
                # 检查是否为附件
                if "attachment" in content_disposition or part.get_filename():
                    filename = part.get_filename()
                    
                    if filename:
                        # 解码文件名
                        filename = self._decode_mime_words(filename)
                        
                        # 清理文件名中的换行符和特殊字符
                        filename = filename.replace('\n', '').replace('\r', '').strip()
                        
                        # 安全检查1: 文件名验证
                        if not self._is_safe_filename(filename):
                            logger.warning(f"跳过不安全的文件名: {filename}")
                            continue
                        
                        # 安全检查2: 文件扩展名检查
                        file_extension = os.path.splitext(filename)[1].lower()
                        if file_extension in dangerous_extensions:
                            logger.warning(f"跳过危险文件类型: {filename} ({file_extension})")
                            continue
                        
                        if file_extension and file_extension not in allowed_extensions:
                            logger.warning(f"跳过不允许的文件类型: {filename} ({file_extension})")
                            continue
                        
                        # 获取附件内容
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue
                        
                        # 安全检查3: 文件大小限制
                        if len(payload) > max_file_size:
                            logger.warning(f"跳过过大的文件: {filename} ({len(payload)} bytes)")
                            continue
                        
                        # 生成唯一的文件名避免冲突（清理email_id中的特殊字符）
                        # 从email_id中提取纯数字部分，避免特殊字符
                        clean_email_id = email_id.split(':')[-1] if ':' in email_id else email_id
                        # 进一步清理，只保留字母数字和下划线
                        clean_email_id = ''.join(c for c in clean_email_id if c.isalnum() or c == '_')[:20]
                        unique_filename = f"{clean_email_id}_{uuid.uuid4().hex[:8]}{file_extension}"
                        file_path = os.path.join(user_attachment_dir, unique_filename)
                        
                        try:
                            # 保存附件到本地
                            with open(file_path, 'wb') as f:
                                f.write(payload)
                            
                            # 记录附件信息
                            attachment_info = {
                                'filename': filename,
                                'original_filename': filename,
                                'stored_filename': unique_filename,
                                'file_path': file_path,
                                'content_type': content_type,
                                'size': len(payload),
                                'created_at': datetime.now().isoformat(),
                                'is_safe': True  # 标记为已通过安全检查
                            }
                            
                            attachments.append(attachment_info)
                            logger.info(f"保存附件: {filename} ({len(payload)} bytes)")
                            
                        except Exception as e:
                            logger.error(f"保存附件失败 {filename}: {e}")
                            # 清理可能创建的文件
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                            continue
                            
        except Exception as e:
            logger.error(f"提取附件失败: {e}")
        
        return attachments
    
    def _is_safe_filename(self, filename: str) -> bool:
        """检查文件名是否安全"""
        if not filename or len(filename) > 255:
            return False
        
        # 检查危险字符
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            if char in filename:
                return False
        
        # 检查路径遍历攻击
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return False
        
        # 检查Windows保留名称
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """解析邮件日期"""
        if not date_str:
            return datetime.now()
        
        try:
            return email.utils.parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"解析邮件日期失败: {date_str}, 错误: {e}")
            return datetime.now()
    
    def _categorize_email(self, subject: str, sender: str, body: str, user_id: int = None) -> Tuple[str, int, str]:
        """
        邮件分类和重要性评分（使用新的智能分类系统）
        
        Returns:
            Tuple[str, int, str]: (category, importance, classification_method)
        """
        # 构造邮件数据
        email_data = {
            'subject': subject,
            'sender': sender,
            'body': body
        }
        
        # 如果有user_id，使用新的智能分类系统
        if user_id and hasattr(self, 'classification_service'):
            try:
                category, importance, method = self.classification_service.classify_email(email_data, user_id)
                return category, importance, method
            except Exception as e:
                logger.warning(f"智能分类失败，使用兜底分类: {e}")
        
        # 兜底：使用原有的简单关键词分类
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        body_lower = body.lower()[:500]
        
        # 重要性关键词
        high_importance_keywords = [
            'urgent', '紧急', '重要', 'important', '急', '立即', 'asap',
            '截止', 'deadline', '会议', 'meeting', '面试', 'interview'
        ]
        
        medium_importance_keywords = [
            '通知', 'notice', '公告', 'announcement', '更新', 'update',
            '邀请', 'invitation', '确认', 'confirmation'
        ]
        
        # 分类关键词（12个类别）
        categories = {
            'work': ['工作', 'work', '项目', 'project', '任务', 'task', '会议', 'meeting'],
            'finance': ['账单', 'bill', '付款', 'payment', '银行', 'bank', '财务', 'finance'],
            'social': ['朋友', 'friend', '社交', 'social', '聚会', 'party'],
            'shopping': ['订单', 'order', '购买', 'purchase', '商品', 'product', '物流', 'shipping'],
            'news': ['新闻', 'news', '资讯', 'information', '更新', 'update'],
            'education': ['课程', 'course', '培训', 'training', '学习', 'study'],
            'travel': ['机票', 'flight', '酒店', 'hotel', '旅行', 'travel'],
            'health': ['医院', 'hospital', '体检', 'checkup', '健康', 'health'],
            'system': ['验证码', 'code', '密码', 'password', '账号', 'account'],
            'advertising': ['广告', 'ad', '推广', 'promotion', '营销', 'marketing', '促销', '优惠', 'discount', '折扣', 'sale'],
            'spam': ['中奖', 'prize', '恭喜', '免费领取', 'free gift', '点击领取', 'click here']
        }
        
        # 计算重要性
        importance = 1  # 默认普通
        text_to_check = f"{subject_lower} {sender_lower} {body_lower}"
        
        if any(keyword in text_to_check for keyword in high_importance_keywords):
            importance = 3  # 高重要性
        elif any(keyword in text_to_check for keyword in medium_importance_keywords):
            importance = 2  # 中等重要性
        
        # 确定分类
        category = 'general'
        for cat, keywords in categories.items():
            if any(keyword in text_to_check for keyword in keywords):
                category = cat
                break
        
        return category, importance, 'keyword'
    
    def fetch_new_emails(self, account: Dict, since_days: int = 1, user_id: int = None, max_emails: int = None) -> List[Dict]:
        """获取指定账户的新邮件
        
        Args:
            account: 邮箱账户信息
            since_days: 获取最近几天的邮件
            user_id: 用户ID
            max_emails: 每次最大处理邮件数量（如果为None，使用系统默认值）
        """
        if not account:
            return []
        
        email_address = account['email']
        password = account['password']
        provider = account['provider']
        
        # 新浪邮箱智能识别：根据邮箱地址自动选择正确的服务器配置
        if provider.lower() == 'sina':
            detected_provider = Config.detect_email_provider(email_address)
            if detected_provider and 'sina' in detected_provider:
                provider = detected_provider
                logger.info(f"新浪邮箱智能识别：{email_address} → 使用配置 {provider}")
        
        logger.info(f"开始获取邮箱 {email_address} 的新邮件")
        
        imap_server = None
        try:
            config = Config.get_email_provider_config(provider)
            if not config:
                logger.error(f"不支持的邮件服务商: {provider}")
                return []
            
            # 建立连接
            if config['use_ssl']:
                imap_server = imaplib.IMAP4_SSL(config['imap_host'], config['imap_port'])
            else:
                imap_server = imaplib.IMAP4(config['imap_host'], config['imap_port'])
            
            # 登录
            login_result = imap_server.login(email_address, password)
            if login_result[0] != 'OK':
                logger.error(f"邮箱 {email_address} 登录失败: {login_result[1]}")
                return []
            
            # 对于126/163邮箱，登录成功后必须发送ID命令（官方要求）
            if provider.lower() in ['126', '163']:
                try:
                    logger.info(f"{provider}邮箱登录成功，发送IMAP ID信息...")
                    
                    try:
                        typ, dat = imap_server._command('ID', '("name" "EmailDigestSystem" "version" "1.0.0" "vendor" "EmailDigest")')
                        logger.info(f"IMAP ID命令结果: {typ}")
                    except Exception as e1:
                        logger.info(f"使用手动发送方式（正常）")
                        tag = imap_server._new_tag().decode()
                        id_line = f'{tag} ID ("name" "EmailDigestSystem" "version" "1.0.0" "vendor" "EmailDigest")\r\n'
                        imap_server.send(id_line.encode('utf-8'))
                        # 读取响应（简化版）
                        while True:
                            line = imap_server.readline().decode('utf-8', errors='ignore')
                            if line.startswith(tag):
                                logger.info(f"ID命令响应: {line.strip()}")
                                break
                except Exception as e:
                    logger.warning(f"ID命令失败: {e}")
            
            # 选择收件箱
            select_result = imap_server.select('INBOX')
            if select_result[0] != 'OK':
                logger.error(f"邮箱 {email_address} 选择收件箱失败: {select_result[1]}")
                return []
            
            # ✅ 修复时区问题: 使用UTC时间计算,避免8小时时差
            # IMAP服务器通常使用UTC时间,如果使用本地时间(UTC+8)会导致早上的邮件检索不到
            from datetime import timezone
            utc_now = datetime.now(timezone.utc)
            since_datetime_utc = utc_now - timedelta(days=since_days)
            since_date = since_datetime_utc.strftime("%d-%b-%Y")
            
            # 详细日志帮助调试时区问题
            logger.info(f"时区信息 - UTC当前: {utc_now.isoformat()}, "
                       f"UTC搜索起点: {since_datetime_utc.isoformat()}, "
                       f"IMAP日期: {since_date}")
            
            search_criteria = f'(SINCE "{since_date}")'
            
            # 搜索邮件
            status, messages = imap_server.search(None, search_criteria)
            if status != 'OK':
                logger.error(f"搜索邮件失败: {email_address}")
                imap_server.logout()
                return []
            
            email_ids = messages[0].split()
            logger.info(f"邮箱 {email_address} 找到 {len(email_ids)} 封邮件")
            
            # 限制处理数量（优先使用用户配置，否则使用系统默认值）
            # 如果max_emails为None，表示不限制数量（批量导入场景）
            if max_emails is None:
                logger.info(f"批量导入模式：不限制邮件数量，将导入所有 {len(email_ids)} 封邮件")
            else:
                max_emails_limit = max_emails
                if len(email_ids) > max_emails_limit:
                    email_ids = email_ids[-max_emails_limit:]
                    logger.info(f"限制处理数量为 {max_emails_limit} 封（用户配置）")
            
            # 获取已处理的邮件ID
            processed_ids = self.db.get_processed_email_ids(email_address)
            
            new_emails = []
            for email_id in email_ids:
                email_id_str = email_id.decode('utf-8')
                
                # 生成唯一的邮件ID（包含账户信息）
                unique_email_id = f"{email_address}:{email_id_str}"
                
                if unique_email_id in processed_ids:
                    continue
                
                try:
                    # 获取邮件
                    status, msg_data = imap_server.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # 解析邮件头
                    subject = self._decode_mime_words(msg.get("Subject", ""))
                    sender = self._decode_mime_words(msg.get("From", ""))
                    recipients = [self._decode_mime_words(r) for r in msg.get_all("To", [])]
                    date_str = msg.get("Date", "")
                    email_date = self._parse_email_date(date_str)
                    
                    # 获取邮件正文
                    body, body_html = self._get_email_body(msg)
                    
                    # 提取附件（需要user_id参数）
                    attachments = self._extract_attachments(msg, unique_email_id, user_id) if user_id else []
                    
                    # 邮件分类和重要性评分（使用新的智能分类系统）
                    category, importance, classification_method = self._categorize_email(subject, sender, body, user_id)
                    
                    # ✨ 转发邮件检测和原始发件人提取
                    is_forwarded, forward_confidence = self.forward_detector.detect_forwarded_email(
                        msg, subject, body, body_html
                    )
                    
                    # 如果检测到转发邮件，提取原始发件人信息
                    if is_forwarded:
                        original_sender, original_email, forward_level, forward_chain = \
                            self.forward_detector.extract_original_sender(msg, body, body_html)
                        
                        # 最近转发者信息
                        forwarded_by = sender
                        forwarded_by_email = self.forward_detector.parse_email_address(sender)[1]
                    else:
                        original_sender = None
                        original_email = None
                        forward_level = 0
                        forward_chain = []
                        forwarded_by = None
                        forwarded_by_email = None
                    
                    email_data = {
                        'email_id': unique_email_id,
                        'subject': subject[:Config.EMAIL_SUBJECT_MAX_LENGTH],
                        'sender': sender,
                        'recipients': recipients,
                        'date': email_date,
                        'body': body[:Config.EMAIL_BODY_MAX_LENGTH],
                        'body_html': body_html,
                        'summary': None,
                        'ai_summary': None,
                        'processed': False,
                        'account_email': email_address,
                        'provider': provider,
                        'importance': importance,
                        'category': category,
                        'classification_method': classification_method,  # 新增：记录分类方法
                        'attachments': attachments,
                        'user_id': user_id,  # 确保user_id被传递
                        # 转发相关字段
                        'is_forwarded': is_forwarded,
                        'forward_level': forward_level,
                        'original_sender': original_sender,
                        'original_sender_email': original_email,
                        'forwarded_by': forwarded_by,
                        'forwarded_by_email': forwarded_by_email,
                        'forward_chain': json.dumps(forward_chain) if forward_chain else None,
                    }
                    
                    new_emails.append(email_data)
                    
                except Exception as e:
                    logger.error(f"解析邮件 {email_id_str} 失败: {e}")
                    continue
            
            logger.info(f"邮箱 {email_address} 获取到 {len(new_emails)} 封新邮件")
            return new_emails
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP错误 - 邮箱 {email_address}: {e}")
            return []
        except Exception as e:
            logger.error(f"获取邮件失败 - 邮箱 {email_address}: {e}")
            return []
        finally:
            # 确保连接被正确关闭
            if imap_server:
                try:
                    imap_server.logout()
                except:
                    pass
    
    def get_provider_from_email(self, email_address: str) -> Optional[str]:
        """根据邮箱地址自动识别服务商"""
        return Config.detect_email_provider(email_address)
