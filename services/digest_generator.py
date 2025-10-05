#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 简报生成器
"""

from datetime import datetime, timezone
import json
import logging
from typing import List, Dict, Optional

from services.ai_client import AIClient

logger = logging.getLogger(__name__)

class DigestGenerator:
    def __init__(self):
        self.ai_client = AIClient()
    
    def _categorize_emails(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """按类别分组邮件"""
        categories = {
            'important': [],    # 重要邮件
            'work': [],         # 工作邮件
            'finance': [],      # 财务邮件
            'social': [],       # 社交邮件
            'shopping': [],     # 购物邮件
            'news': [],         # 资讯邮件
            'general': []       # 其他邮件
        }
        
        for email in emails:
            # 按重要性分类
            if email.get('importance', 1) >= 3:
                categories['important'].append(email)
            
            # 按内容分类
            category = email.get('category', 'general')
            if category in categories:
                categories[category].append(email)
            else:
                categories['general'].append(email)
        
        # 移除空分类
        return {k: v for k, v in categories.items() if v}
    
    def _format_email_for_digest(self, email: Dict) -> Dict:
        """格式化邮件信息用于简报"""
        # 处理日期字段，支持字符串和datetime对象
        email_date = email.get('date')
        if email_date:
            if isinstance(email_date, str):
                # 如果是字符串，直接使用
                date_iso = email_date
                try:
                    # 尝试解析字符串获取时间部分
                    date_obj = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                    time_str = date_obj.strftime('%H:%M')
                except:
                    time_str = ''
            else:
                # 如果是datetime对象，转换为ISO格式
                date_iso = email_date.isoformat()
                time_str = email_date.strftime('%H:%M')
        else:
            date_iso = datetime.now(timezone.utc).isoformat()
            time_str = ''
        
        return {
            'id': email.get('id'),  # 添加邮件ID用于翻译功能
            'subject': email.get('subject', 'Unknown Subject'),
            'sender': email.get('sender', 'Unknown Sender'),
            'sender_name': self._extract_sender_name(email.get('sender', '')),
            'date': date_iso,
            'time': time_str,
            'summary': email.get('ai_summary') or email.get('summary', '暂无摘要'),
            'importance': email.get('importance', 1),
            'category': email.get('category', 'general'),
            'account_email': email.get('account_email', ''),
            'provider': email.get('provider', '')
        }
    
    def _extract_sender_name(self, sender: str) -> str:
        """提取发件人姓名"""
        if not sender:
            return 'Unknown'
        
        # 提取 "Name <email@domain.com>" 格式中的姓名
        if '<' in sender:
            name = sender.split('<')[0].strip()
            if name and name != sender:
                return name
        
        # 如果没有姓名，使用邮箱的用户名部分
        if '@' in sender:
            return sender.split('@')[0]
        
        return sender
    
    def _calculate_digest_stats(self, emails: List[Dict]) -> Dict:
        """计算简报统计信息（增强版：包含日程、任务、截止日期）"""
        if not emails:
            return {
                'total_emails': 0,
                'important_count': 0,
                'urgent_count': 0,
                'categories': {},
                'providers': {},
                'accounts': {},
                'time_distribution': {},
                'meetings': [],
                'tasks': [],
                'deadlines': [],
                'financial_items': []
            }
        
        stats = {
            'total_emails': len(emails),
            'important_count': 0,
            'urgent_count': 0,
            'categories': {},
            'providers': {},
            'accounts': {},
            'time_distribution': {},
            'meetings': [],
            'tasks': [],
            'deadlines': [],
            'financial_items': []
        }
        
        for email in emails:
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            combined_text = f"{subject} {body[:500]}"
            
            # 重要邮件统计
            importance = email.get('importance', 1)
            if importance >= 3:
                stats['urgent_count'] += 1
                stats['important_count'] += 1
            elif importance >= 2:
                stats['important_count'] += 1
            
            # 分类统计
            category = email.get('category', 'general')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # 邮件服务商统计
            provider = email.get('provider', 'unknown')
            stats['providers'][provider] = stats['providers'].get(provider, 0) + 1
            
            # 账户统计
            account = email.get('account_email', 'unknown')
            stats['accounts'][account] = stats['accounts'].get(account, 0) + 1
            
            # 时间分布统计
            if email.get('date'):
                try:
                    # 处理日期字段，支持字符串和datetime对象
                    email_date = email['date']
                    if isinstance(email_date, str):
                        # 如果是字符串，解析为datetime对象
                        date_obj = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                        hour = date_obj.hour
                    elif hasattr(email_date, 'hour'):
                        # 如果是datetime对象
                        hour = email_date.hour
                    else:
                        # 无法获取小时信息，跳过
                        continue
                    
                    time_slot = f"{hour:02d}:00-{(hour+1):02d}:00"
                    stats['time_distribution'][time_slot] = stats['time_distribution'].get(time_slot, 0) + 1
                except Exception as e:
                    logger.debug(f"处理邮件时间分布统计时出错: {e}")
                    continue
            
            # 会议识别
            meeting_keywords = ['会议', 'meeting', '例会', '讨论', 'discussion', '面谈', 'zoom', '腾讯会议']
            if any(keyword in combined_text for keyword in meeting_keywords):
                stats['meetings'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', ''),
                    'time': email.get('date', '')
                })
            
            # 任务识别
            task_keywords = ['任务', 'task', 'todo', '待办', '需要完成', '请处理', '请完成']
            if any(keyword in combined_text for keyword in task_keywords):
                stats['tasks'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
            
            # 截止日期识别
            deadline_keywords = ['截止', 'deadline', '最迟', '截至', 'due date', '到期']
            if any(keyword in combined_text for keyword in deadline_keywords):
                stats['deadlines'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
            
            # 财务相关
            if category == 'finance':
                stats['financial_items'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
        
        return stats
    
    def _generate_digest_title(self, date: datetime, email_count: int) -> str:
        """生成简报标题"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            weekday = weekday_names[date.weekday()]
            
            return f"{date_str} ({weekday}) Email Digest - {email_count} emails"
        except Exception as e:
            logger.error(f"生成简报标题失败: {e}")
            # 使用安全的备用标题
            return f"{date.strftime('%Y-%m-%d')} Email Digest - {email_count} emails"
    
    def generate_digest_content(self, emails: List[Dict], is_manual_fetch: bool = False) -> Dict:
        """生成简报内容
        
        Args:
            emails: 邮件列表
            is_manual_fetch: 是否为手动收取
        """
        if not emails:
            now_utc = datetime.now(timezone.utc)
            return {
                "title": self._generate_digest_title(now_utc, 0),
                "generated_at": now_utc.isoformat(),
                "email_count": 0,
                "summary": "No emails today",
                "categories": {},
                "stats": self._calculate_digest_stats([]),
                "emails": []
            }
        
        # 按类别分组
        categorized_emails = self._categorize_emails(emails)
        
        # 格式化邮件
        formatted_categories = {}
        all_formatted_emails = []
        
        for category, category_emails in categorized_emails.items():
            formatted_emails = [self._format_email_for_digest(email) for email in category_emails]
            formatted_categories[category] = formatted_emails
            all_formatted_emails.extend(formatted_emails)
        
        # 生成AI总结（传递is_manual_fetch参数）
        try:
            ai_summary = self.ai_client.generate_digest_summary(emails, is_manual_fetch=is_manual_fetch)
        except Exception as e:
            logger.error(f"生成AI总结失败: {e}")
            ai_summary = f"Received {len(emails)} emails today"
        
        # 计算统计信息
        stats = self._calculate_digest_stats(emails)
        
        now_utc = datetime.now(timezone.utc)
        digest_content = {
            "title": self._generate_digest_title(now_utc, len(emails)),
            "generated_at": now_utc.isoformat(),
            "email_count": len(emails),
            "summary": ai_summary,
            "categories": formatted_categories,
            "stats": stats,
            "emails": all_formatted_emails
        }
        
        return digest_content
    
    def create_digest(self, emails: List[Dict], is_manual_fetch: bool = False) -> Dict:
        """创建简报记录
        
        Args:
            emails: 邮件列表
            is_manual_fetch: 是否为手动收取
        """
        try:
            content = self.generate_digest_content(emails, is_manual_fetch=is_manual_fetch)
            
            digest = {
                'date': datetime.now(timezone.utc),
                'title': content['title'],
                'content': content,
                'email_count': len(emails),
                'summary': content['summary']
            }
            
            logger.info(f"简报创建完成: {digest['title']}")
            return digest
            
        except Exception as e:
            logger.error(f"创建简报失败: {e}")
            # 返回基础简报
            now_utc = datetime.now(timezone.utc)
            return {
                'date': now_utc,
                'title': f"{now_utc.strftime('%Y-%m-%d')} Email Digest",
                'content': {
                    "title": f"{now_utc.strftime('%Y-%m-%d')} Email Digest",
                    "email_count": len(emails),
                    "summary": f"Processed {len(emails)} emails",
                    "categories": {},
                    "emails": []
                },
                'email_count': len(emails),
                'summary': f"Processed {len(emails)} emails, but detailed digest generation failed"
            }
