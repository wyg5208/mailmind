#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 转发邮件检测服务
支持转发邮件的识别和原始发件人提取
"""

import re
import logging
from typing import Tuple, Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ForwardDetector:
    """转发邮件检测器"""
    
    def __init__(self):
        # 转发邮件头标识
        self.forwarded_headers = [
            'X-Forwarded-For',
            'X-Forwarded-Message-Id',
            'Resent-From',
            'Resent-Sender',
            'X-Forwarded-To',
        ]
        
        # 主题前缀模式
        self.forward_subject_patterns = [
            r'^(Fwd:|FW:|转发:|Trans:|Forward:|转:|Fw:)',  # 英中文前缀
            r'^(Re:\s*)?(Fwd:|FW:|转发:)',  # 组合前缀
        ]
        
        # 正文结构模式
        self.forward_body_patterns = [
            r'-{3,}\s*(Original Message|Forwarded message|转发邮件)',
            r'Begin forwarded message:',
            r'---------- Forwarded message ---------',
            r'发件人:.*\n收件人:.*\n主题:',
            r'From:.*\nTo:.*\nSubject:',
            r'>\s*From:',  # 引用格式的From
            r'On.*wrote:',  # Gmail风格
        ]
        
        # HTML标记模式
        self.html_forward_markers = [
            r'<div class=["\']gmail_quote["\']',  # Gmail
            r'<blockquote.*?>.*?From:.*?</blockquote>',  # Outlook
            r'<div.*?forwarded.*?>',  # 通用
        ]
        
        # 原始发件人提取模式
        self.sender_patterns = [
            # 126邮箱格式 (最优先 - 带引号的发件人格式)
            {
                'from': r'发件人[:：]\s*["""\'](.*?)["""\']?\s*<([^>]+)>',
                'subject': r'主题[:：]\s*([^\n]+)',
                'date': r'发送日期[:：]\s*([^\n]+)',
            },
            # Gmail / 通用格式
            {
                'from': r'From:\s*([^\n<]+?)\s*<([^>]+)>',
                'subject': r'Subject:\s*([^\n]+)',
                'date': r'Date:\s*([^\n]+)',
            },
            # Outlook格式
            {
                'from': r'发件人:\s*([^\n<]+?)\s*<([^>]+)>',
                'subject': r'主题:\s*([^\n]+)',
                'date': r'发送时间:\s*([^\n]+)',
            },
            # 网易邮箱简化格式 (发件人：邮箱,无尖括号)
            {
                'from': r'发件人[:：]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                'subject': r'主题[:：]\s*([^\n]+)',
            },
            # 简单格式
            {
                'from': r'>\s*From:\s*([^\n]+)',
            },
            # 中文格式
            {
                'from': r'(?:原始)?发件人[:：]\s*([^\n<]+?)(?:\s*<([^>]+)>)?',
            },
            # 纯邮箱格式
            {
                'from': r'From:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            },
        ]
    
    def detect_forwarded_email(self, msg, subject: str, body: str, body_html: str) -> Tuple[bool, int]:
        """
        多维度检测转发邮件
        
        Args:
            msg: 邮件消息对象
            subject: 邮件主题
            body: 邮件正文
            body_html: HTML正文
            
        Returns:
            (is_forwarded: bool, confidence: int): 是否转发 和 置信度评分
        """
        is_forwarded = False
        confidence = 0
        
        try:
            # === 维度1: 邮件头分析 (最可靠) ===
            for header in self.forwarded_headers:
                if msg.get(header):
                    is_forwarded = True
                    confidence += 40
                    logger.debug(f"检测到转发邮件头: {header}")
                    break
            
            # === 维度2: 主题前缀分析 ===
            for pattern in self.forward_subject_patterns:
                if re.match(pattern, subject, re.IGNORECASE):
                    is_forwarded = True
                    confidence += 25
                    logger.debug(f"检测到转发主题前缀: {subject[:50]}")
                    break
            
            # === 维度3: 正文结构分析 ===
            text_to_check = body if body else body_html
            if text_to_check:
                for pattern in self.forward_body_patterns:
                    if re.search(pattern, text_to_check, re.MULTILINE | re.IGNORECASE):
                        is_forwarded = True
                        confidence += 20
                        logger.debug(f"检测到转发正文标识")
                        break
            
            # === 维度4: HTML标记分析 ===
            if body_html:
                for pattern in self.html_forward_markers:
                    if re.search(pattern, body_html, re.IGNORECASE | re.DOTALL):
                        is_forwarded = True
                        confidence += 15
                        logger.debug(f"检测到转发HTML标记")
                        break
            
            if is_forwarded:
                logger.info(f"检测到转发邮件，置信度: {confidence}, 主题: {subject[:50]}")
            
            return is_forwarded, confidence
            
        except Exception as e:
            logger.error(f"转发邮件检测失败: {e}")
            return False, 0
    
    def extract_original_sender(self, msg, body: str, body_html: str) -> Tuple[Optional[str], Optional[str], int, List[Dict]]:
        """
        提取原始发件人信息
        
        Args:
            msg: 邮件消息对象
            body: 邮件正文
            body_html: HTML正文
            
        Returns:
            (original_sender, original_email, forward_level, forward_chain):
            原始发件人姓名, 原始邮箱, 转发层级, 转发链
        """
        original_sender = None
        original_email = None
        forward_chain = []
        
        try:
            # === 策略1: 检查Resent-From邮件头 ===
            if msg:  # 只有msg对象存在时才检查邮件头
                resent_from = msg.get('Resent-From')
                if resent_from:
                    original_sender, original_email = self.parse_email_address(resent_from)
                    if original_email:
                        logger.info(f"从Resent-From头提取原始发件人: {original_email}")
                        return original_sender, original_email, 1, []
            
            # === 策略2: 解析正文中的原始邮件头 ===
            text_to_parse = body if body else body_html
            if text_to_parse:
                for pattern_set in self.sender_patterns:
                    from_match = re.search(pattern_set['from'], text_to_parse, re.MULTILINE | re.IGNORECASE)
                    
                    if from_match:
                        groups = from_match.groups()
                        if len(groups) >= 2 and groups[1]:
                            # 格式: Name <email>
                            original_sender = groups[0].strip()
                            original_email = groups[1].strip()
                        else:
                            # 只有email或Name
                            potential_value = groups[0].strip()
                            if '@' in potential_value:
                                original_email = potential_value
                                original_sender = potential_value.split('@')[0]
                            else:
                                original_sender = potential_value
                        
                        # 尝试提取更多信息构建转发链
                        if 'subject' in pattern_set and original_email:
                            subject_match = re.search(pattern_set['subject'], text_to_parse, re.MULTILINE | re.IGNORECASE)
                            date_match = re.search(pattern_set['date'], text_to_parse, re.MULTILINE | re.IGNORECASE) if 'date' in pattern_set else None
                            
                            forward_info = {
                                'from_name': original_sender,
                                'from_email': original_email,
                                'subject': subject_match.group(1).strip() if subject_match else None,
                                'date': date_match.group(1).strip() if date_match else None,
                            }
                            forward_chain.append(forward_info)
                        
                        if original_email:
                            logger.info(f"从正文提取原始发件人: {original_email}")
                        break
            
            # === 策略3: 从HTML中提取 ===
            if not original_email and body_html:
                original_sender, original_email = self._extract_from_html(body_html)
                if original_email:
                    logger.info(f"从HTML提取原始发件人: {original_email}")
            
            # === 验证和清理 ===
            if original_email:
                original_email = self.validate_and_clean_email(original_email)
            
            if original_sender:
                original_sender = self.clean_sender_name(original_sender)
            
            # 计算转发层级
            forward_level = len(forward_chain) if forward_chain else (1 if original_email else 0)
            
            return original_sender, original_email, forward_level, forward_chain
            
        except Exception as e:
            logger.error(f"提取原始发件人失败: {e}")
            return None, None, 0, []
    
    def _extract_from_html(self, body_html: str) -> Tuple[Optional[str], Optional[str]]:
        """从HTML中提取原始发件人"""
        try:
            soup = BeautifulSoup(body_html, 'html.parser')
            
            # 查找Gmail风格的引用
            gmail_quote = soup.find('div', class_='gmail_quote')
            if gmail_quote:
                from_tag = gmail_quote.find(string=re.compile(r'From:', re.IGNORECASE))
                if from_tag:
                    from_text = from_tag.parent.get_text()
                    email_match = re.search(r'<([^>]+)>', from_text)
                    if email_match:
                        email = email_match.group(1)
                        name_match = re.search(r'From:\s*([^<]+)', from_text, re.IGNORECASE)
                        name = name_match.group(1).strip() if name_match else None
                        return name, email
            
            # 查找blockquote中的内容
            blockquotes = soup.find_all('blockquote')
            for bq in blockquotes:
                text = bq.get_text()
                match = re.search(r'From:\s*([^\n<]+?)\s*<([^>]+)>', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip(), match.group(2).strip()
            
            return None, None
            
        except Exception as e:
            logger.warning(f"从HTML提取发件人失败: {e}")
            return None, None
    
    def parse_email_address(self, email_str: str) -> Tuple[Optional[str], Optional[str]]:
        """解析邮件地址字符串"""
        if not email_str:
            return None, None
        
        # 格式: "Name <email@example.com>" 或 "email@example.com"
        match = re.match(r'([^<]+?)\s*<([^>]+)>', email_str)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # 纯邮箱地址
        if '@' in email_str:
            email = email_str.strip()
            return email, email
        
        return email_str.strip(), None
    
    def validate_and_clean_email(self, email: str) -> Optional[str]:
        """验证并清理邮箱地址"""
        if not email:
            return None
        
        # 移除空白字符
        email = email.strip()
        
        # 基本邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return email.lower()
        
        return None
    
    def clean_sender_name(self, name: str) -> Optional[str]:
        """清理发件人姓名"""
        if not name:
            return None
        
        # 移除引号
        name = name.strip('"\'')
        
        # 移除多余空白
        name = re.sub(r'\s+', ' ', name).strip()
        
        # 移除邮箱地址(如果包含)
        name = re.sub(r'<[^>]+>', '', name).strip()
        
        # 移除常见的前缀
        name = re.sub(r'^(From|发件人|原始发件人)[:：]\s*', '', name, flags=re.IGNORECASE).strip()
        
        return name if name else None
    
    def calculate_forward_level(self, body: str, body_html: str) -> int:
        """计算转发层级"""
        forward_markers = [
            r'-{3,}\s*(Original Message|Forwarded message)',
            r'Begin forwarded message:',
            r'发件人:.*\n收件人:.*\n主题:',
        ]
        
        text = body if body else body_html
        if not text:
            return 1
        
        count = 0
        for pattern in forward_markers:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            count = max(count, len(matches))
        
        return count if count > 0 else 1

