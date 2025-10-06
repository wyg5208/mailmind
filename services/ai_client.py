#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - AI客户端
支持多种AI服务提供商
"""

import requests
import json
import logging
import time
import threading
from typing import List, Dict, Optional, Callable
import re
from datetime import datetime

from config import Config
from services.translation_service import translation_service

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self._init_client()
    
    def _init_client(self):
        """初始化AI客户端"""
        # 尝试从数据库获取配置，如果没有则使用环境变量
        try:
            from models.database import Database
            db = Database()
            
            self.provider = db.get_system_config('ai_provider', Config.AI_PROVIDER)
            
            if self.provider == 'glm':
                self.api_key = db.get_system_config('glm_api_key', Config.GLM_API_KEY)
                self.base_url = Config.GLM_BASE_URL
                self.model = db.get_system_config('glm_model', Config.GLM_MODEL)
            elif self.provider == 'openai':
                self.api_key = db.get_system_config('openai_api_key', Config.OPENAI_API_KEY)
                self.base_url = Config.OPENAI_BASE_URL
                self.model = db.get_system_config('openai_model', Config.OPENAI_MODEL)
            else:
                logger.warning(f"不支持的AI服务提供商: {self.provider}")
                
        except Exception as e:
            logger.warning(f"从数据库加载AI配置失败，使用默认配置: {e}")
            # 降级到环境变量配置
            if self.provider == 'glm':
                self.api_key = Config.GLM_API_KEY
                self.base_url = Config.GLM_BASE_URL
                self.model = Config.GLM_MODEL
            elif self.provider == 'openai':
                self.api_key = Config.OPENAI_API_KEY
                self.base_url = Config.OPENAI_BASE_URL
                self.model = Config.OPENAI_MODEL
    
    def _clean_email_content(self, content: str) -> str:
        """清理邮件内容，移除无用信息"""
        if not content:
            return ""
        
        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 移除邮件签名（简单规则）
        signature_patterns = [
            r'--\s*\n.*',  # -- 开始的签名
            r'Best regards.*',
            r'Sent from.*',
            r'发自.*',
            r'此邮件.*自动发送.*'
        ]
        
        for pattern in signature_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        return content.strip()
    
    def _create_summary_prompt(self, email_data: Dict) -> str:
        """创建邮件摘要提示词"""
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = self._clean_email_content(email_data.get('body', ''))
        category = email_data.get('category', 'general')
        
        # 根据邮件分类调整摘要重点
        category_instructions = {
            'work': '重点关注工作任务、截止时间、会议安排等关键信息',
            'finance': '重点关注金额、付款时间、账户信息等财务要点',
            'social': '重点关注活动安排、时间地点等社交信息',
            'shopping': '重点关注订单状态、商品信息、物流信息等',
            'news': '重点关注新闻要点、关键事件等',
            'general': '提取邮件的核心信息和关键要点'
        }
        
        instruction = category_instructions.get(category, category_instructions['general'])
        
        prompt = f"""
请为以下邮件生成简洁准确的中文摘要：

邮件主题：{subject}
发件人：{sender}
邮件内容：{body[:1500]}  

要求：
1. {instruction}
2. 摘要控制在{Config.SUMMARY_MAX_LENGTH}字以内
3. 突出关键信息，如时间、地点、金额、截止日期等
4. 语言简洁明了，避免冗余
5. 如果是重要邮件，在开头标注[重要]
6. 如果内容不完整或无意义，请说明"邮件内容不完整"

摘要：
"""
        return prompt.strip()
    
    def _call_glm_api(self, prompt: str) -> Optional[str]:
        """调用GLM API"""
        if not self.api_key:
            logger.error("GLM API key 未配置")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": Config.SUMMARY_TEMPERATURE,
            "max_tokens": Config.SUMMARY_MAX_LENGTH + 50,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    summary = result['choices'][0]['message']['content'].strip()
                    return self._post_process_summary(summary)
                else:
                    logger.error("GLM API 返回格式错误")
                    return None
            else:
                error_text = response.text
                logger.error(f"GLM API 调用失败: {response.status_code} - {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("GLM API 调用超时")
            return None
        except Exception as e:
            logger.error(f"GLM API 调用异常: {e}")
            return None
    
    def _call_openai_api(self, prompt: str) -> Optional[str]:
        """调用OpenAI API"""
        if not self.api_key:
            logger.error("OpenAI API key 未配置")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": Config.SUMMARY_TEMPERATURE,
            "max_tokens": Config.SUMMARY_MAX_LENGTH + 50
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result['choices'][0]['message']['content'].strip()
                return self._post_process_summary(summary)
            else:
                error_text = response.text
                logger.error(f"OpenAI API 调用失败: {response.status_code} - {error_text}")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API 调用异常: {e}")
            return None
    
    def _post_process_summary(self, summary: str) -> str:
        """后处理摘要内容"""
        if not summary:
            return "摘要生成失败"
        
        # 移除可能的提示词残留
        summary = re.sub(r'^摘要[:：]\s*', '', summary)
        summary = re.sub(r'^总结[:：]\s*', '', summary)
        
        # 对于简报摘要，不再强制截断，保留完整内容
        # 因为智能助理摘要需要更多空间来展示详细信息
        # 只在超过1500字符时才截断（防止极端情况）
        max_allowed = 1500
        if len(summary) > max_allowed:
            summary = summary[:max_allowed - 3] + "..."
        
        return summary.strip()
    
    def _generate_fallback_summary(self, email_data: Dict) -> str:
        """生成备用摘要（当AI调用失败时）"""
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')
        
        # 提取发件人名称
        sender_name = sender.split('<')[0].strip() if '<' in sender else sender.split('@')[0]
        
        # 简单的关键信息提取
        body_preview = body[:100] + "..." if len(body) > 100 else body
        
        if not body.strip():
            return f"来自 {sender_name} 的邮件：{subject}"
        else:
            return f"来自 {sender_name} 的邮件：{subject}。内容摘要：{body_preview}"
    
    def summarize_email(self, email_data: Dict) -> str:
        """生成单封邮件摘要"""
        try:
            prompt = self._create_summary_prompt(email_data)
            
            # 根据配置的AI提供商调用相应API
            if self.provider == 'glm':
                summary = self._call_glm_api(prompt)
            elif self.provider == 'openai':
                summary = self._call_openai_api(prompt)
            else:
                logger.warning(f"不支持的AI提供商: {self.provider}")
                summary = None
            
            # 如果AI调用失败，使用备用摘要
            if not summary:
                summary = self._generate_fallback_summary(email_data)
                logger.warning(f"AI摘要生成失败，使用备用摘要: {email_data.get('subject', 'Unknown')}")
            
            # 自动翻译英文摘要为中文
            if summary and translation_service.is_translation_available():
                try:
                    translated_summary = translation_service.translate_to_chinese(summary)
                    if translated_summary != summary:
                        logger.info(f"摘要已自动翻译: {email_data.get('subject', 'Unknown')}")
                        summary = translated_summary
                except Exception as e:
                    logger.warning(f"摘要翻译失败: {e}")
            
            return summary
            
        except Exception as e:
            logger.error(f"生成邮件摘要时出错: {e}")
            return self._generate_fallback_summary(email_data)
    
    def batch_summarize(self, emails: List[Dict]) -> List[Dict]:
        """批量生成邮件摘要"""
        if not emails:
            return []
        
        logger.info(f"开始批量生成 {len(emails)} 封邮件的摘要")
        
        processed_emails = []
        success_count = 0
        
        for i, email_data in enumerate(emails):
            try:
                logger.debug(f"处理邮件 {i+1}/{len(emails)}: {email_data.get('subject', 'Unknown')}")
                
                # 检查邮件内容是否有效
                if not email_data.get('body', '').strip() and not email_data.get('subject', '').strip():
                    email_data['ai_summary'] = "邮件内容为空"
                    email_data['processed'] = True
                else:
                    # 生成AI摘要
                    ai_summary = self.summarize_email(email_data)
                    email_data['ai_summary'] = ai_summary
                    email_data['processed'] = True
                    success_count += 1
                
                processed_emails.append(email_data)
                
                # 添加延迟避免API限制
                if i < len(emails) - 1:  # 不是最后一封邮件
                    time.sleep(0.5)  # 500ms延迟
                    
            except Exception as e:
                logger.error(f"处理邮件摘要时出错: {e}")
                email_data['ai_summary'] = self._generate_fallback_summary(email_data)
                email_data['processed'] = True
                processed_emails.append(email_data)
        
        logger.info(f"批量摘要生成完成: {success_count}/{len(emails)} 成功")
        return processed_emails
    
    def summarize_email_with_async_translation(self, email_data: Dict, callback: Optional[Callable] = None) -> str:
        """生成邮件摘要并异步翻译"""
        try:
            prompt = self._create_summary_prompt(email_data)
            
            # 根据配置的AI提供商调用相应API
            if self.provider == 'glm':
                summary = self._call_glm_api(prompt)
            elif self.provider == 'openai':
                summary = self._call_openai_api(prompt)
            else:
                logger.warning(f"不支持的AI提供商: {self.provider}")
                summary = None
            
            # 如果AI调用失败，使用备用摘要
            if not summary:
                summary = self._generate_fallback_summary(email_data)
                logger.warning(f"AI摘要生成失败，使用备用摘要: {email_data.get('subject', 'Unknown')}")
            
            # 异步翻译英文摘要为中文
            if summary and translation_service.is_translation_available():
                def translation_callback(translated_summary: str):
                    if translated_summary != summary:
                        logger.info(f"摘要已异步翻译: {email_data.get('subject', 'Unknown')}")
                        email_data['ai_summary'] = translated_summary
                        # 如果提供了回调函数，调用它
                        if callback:
                            callback(email_data, translated_summary)
                    elif callback:
                        callback(email_data, summary)
                
                try:
                    translation_service.translate_to_chinese_async(summary, translation_callback)
                except Exception as e:
                    logger.warning(f"异步翻译启动失败: {e}")
                    if callback:
                        callback(email_data, summary)
            elif callback:
                callback(email_data, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"生成邮件摘要时出错: {e}")
            fallback_summary = self._generate_fallback_summary(email_data)
            if callback:
                callback(email_data, fallback_summary)
            return fallback_summary
    
    def batch_summarize_with_async_translation(self, emails: List[Dict], 
                                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """批量生成邮件摘要并异步翻译"""
        if not emails:
            return []
        
        logger.info(f"开始批量生成 {len(emails)} 封邮件的摘要（异步翻译）")
        
        processed_emails = []
        success_count = 0
        translation_pending = []
        
        def translation_update_callback(email_data: Dict, translated_summary: str):
            """翻译完成后的回调函数"""
            email_data['ai_summary'] = translated_summary
            email_data['translation_completed'] = True
            
            # 检查是否所有翻译都完成了
            if all(email.get('translation_completed', False) for email in translation_pending):
                logger.info("所有邮件摘要翻译完成")
                if progress_callback:
                    progress_callback('translation_completed', processed_emails)
        
        for i, email_data in enumerate(emails):
            try:
                logger.debug(f"处理邮件 {i+1}/{len(emails)}: {email_data.get('subject', 'Unknown')}")
                
                # 检查邮件内容是否有效
                if not email_data.get('body', '').strip() and not email_data.get('subject', '').strip():
                    email_data['ai_summary'] = "邮件内容为空"
                    email_data['processed'] = True
                    email_data['translation_completed'] = True
                else:
                    # 生成AI摘要（异步翻译）
                    ai_summary = self.summarize_email_with_async_translation(
                        email_data, translation_update_callback
                    )
                    email_data['ai_summary'] = ai_summary
                    email_data['processed'] = True
                    email_data['translation_completed'] = False  # 等待翻译完成
                    translation_pending.append(email_data)
                    success_count += 1
                
                processed_emails.append(email_data)
                
                # 报告进度
                if progress_callback:
                    progress_callback('processing', {
                        'current': i + 1,
                        'total': len(emails),
                        'success': success_count
                    })
                
                # 添加延迟避免API限制
                if i < len(emails) - 1:  # 不是最后一封邮件
                    time.sleep(0.5)  # 500ms延迟
                    
            except Exception as e:
                logger.error(f"处理邮件摘要时出错: {e}")
                email_data['ai_summary'] = self._generate_fallback_summary(email_data)
                email_data['processed'] = True
                email_data['translation_completed'] = True
                processed_emails.append(email_data)
        
        logger.info(f"批量摘要生成完成: 成功 {success_count}/{len(emails)}, 等待翻译: {len(translation_pending)}")
        
        # 如果没有需要翻译的邮件，立即完成
        if not translation_pending and progress_callback:
            progress_callback('translation_completed', processed_emails)
        
        return processed_emails
    
    def generate_digest_summary(self, emails: List[Dict], is_manual_fetch: bool = False) -> str:
        """生成智能简报总结 - 拟人化贴心助理风格
        
        Args:
            emails: 邮件列表
            is_manual_fetch: 是否为手动实时收取（True=手动收取，False=定时收取）
        """
        if not emails:
            return "主人，今天还没有收到新邮件哦~ 😊"
        
        # 详细统计信息
        total_count = len(emails)
        categories = {}
        important_emails = []
        urgent_emails = []
        meetings = []
        tasks = []
        deadlines = []
        financial_items = []
        
        # 智能分析每封邮件
        for email in emails:
            subject = email.get('subject', '').lower()
            body = email.get('body', '').lower()
            combined_text = f"{subject} {body[:500]}"
            
            # 分类统计
            category = email.get('category', 'general')
            categories[category] = categories.get(category, 0) + 1
            
            # 重要邮件识别
            importance = email.get('importance', 1)
            if importance >= 3:
                urgent_emails.append(email)
            elif importance >= 2:
                important_emails.append(email)
            
            # 会议识别
            meeting_keywords = ['会议', 'meeting', '例会', '讨论', 'discussion', '面谈', 'zoom', '腾讯会议']
            if any(keyword in combined_text for keyword in meeting_keywords):
                meetings.append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', ''),
                    'time': email.get('date', '')
                })
            
            # 任务识别
            task_keywords = ['任务', 'task', 'todo', '待办', '需要完成', '请处理', '请完成']
            if any(keyword in combined_text for keyword in task_keywords):
                tasks.append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
            
            # 截止日期识别
            deadline_keywords = ['截止', 'deadline', '最迟', '截至', 'due date', '到期']
            if any(keyword in combined_text for keyword in deadline_keywords):
                deadlines.append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
            
            # 财务相关
            if category == 'finance':
                financial_items.append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', '')
                })
        
        # 根据是否手动收取，决定是否包含时间问候
        greeting_instruction = ""
        if is_manual_fetch:
            # 手动收取：不需要时间问候，直接聚焦邮件内容
            greeting_instruction = """
1. **直接开场**（1句话）：直接说明本次收取到的邮件情况，例如：
   - "本次为您收取了XX封邮件，其中..."
   - "刚刚收到了XX封新邮件..."
   - "这次共收取到XX封邮件..."
   注意：不要使用"早上好/下午好/晚上好"等时间问候语"""
        else:
            # 定时收取：使用基于东八区的时间问候
            from utils.timezone_helper import now_china_naive
            china_time = now_china_naive()
            current_hour = china_time.hour
            current_time_str = china_time.strftime('%H:%M')
            
            # 确定问候语
            if 6 <= current_hour < 12:
                expected_greeting = "早上好！☀️"
            elif 12 <= current_hour < 18:
                expected_greeting = "下午好！🌤️"
            else:
                expected_greeting = "晚上好！🌙"
            
            greeting_instruction = f"""
1. **时间问候**（1句话）：当前中国时间是 {current_time_str}（{current_hour}点），请使用"{expected_greeting}"作为开场问候，然后简要说明邮件情况"""
        
        # 构建AI风格的智能摘要提示词
        prompt = f"""
你是一位贴心、专业的邮件助理，请用生动活泼、温暖友好的口吻，为用户生成邮件的智能摘要。

**邮件数据统计**：
- 收到邮件总数：{total_count} 封
- 紧急重要邮件：{len(urgent_emails)} 封
- 需要关注邮件：{len(important_emails)} 封
- 会议邀请/通知：{len(meetings)} 个
- 待办任务：{len(tasks)} 项
- 有截止日期的事项：{len(deadlines)} 项
- 财务相关：{len(financial_items)} 项

**分类统计**：
{json.dumps(categories, ensure_ascii=False, indent=2)}

**紧急邮件概要**（前3个）：
{json.dumps([{'主题': e.get('subject', ''), '发件人': e.get('sender', '')} for e in urgent_emails[:3]], ensure_ascii=False, indent=2)}

**会议通知概要**（前3个）：
{json.dumps(meetings[:3], ensure_ascii=False, indent=2)}

**任务提醒概要**（前3个）：
{json.dumps(tasks[:3], ensure_ascii=False, indent=2)}

**截止日期提醒**（前3个）：
{json.dumps(deadlines[:3], ensure_ascii=False, indent=2)}

请生成一段**不超过500字**的智能摘要，要求：

{greeting_instruction}
2. **总体概况**（2-3句话）：用生动的语言描述邮件总数和重要程度分布
3. **重点提醒**（3-5句话）：
   - 紧急邮件：如果有，用引人注目的方式突出最重要的1-2封，说明关键信息
   - 会议日程：如果有，生动地提醒时间和主题
   - 任务待办：如果有，活泼地提醒需要完成的事项
   - 截止日期：如果有，特别强调临近的deadline，增加紧迫感
4. **财务提醒**（可选1-2句话）：如果有账单、付款等财务邮件，用醒目的方式特别提醒
5. **贴心建议**（1-2句话）：基于邮件内容，给出处理优先级建议

**语言风格要求**：
- 使用"您"而不是"你"，体现专业性
- 语气温暖、生动、活泼，但不失专业
- 用emoji增加亲和力（适度使用，不要过多）
- 重要信息用加粗或特殊符号标注
- 避免机械化、呆板的表述，要自然流畅、充满活力
- 可以使用比喻、拟人等修辞手法，让文字更生动
- 适当增加一些趣味性的表达，但保持专业度

请直接输出摘要内容，不要加任何前缀或解释。
"""
        
        try:
            # 调用AI生成智能摘要
            if self.provider == 'glm':
                summary = self._call_glm_api(prompt)
            elif self.provider == 'openai':
                summary = self._call_openai_api(prompt)
            else:
                summary = None
            
            # 如果AI生成成功，返回
            if summary:
                return summary
            
            # AI失败，使用增强版备用摘要
            return self._generate_enhanced_fallback_summary(
                total_count, urgent_emails, important_emails, meetings, 
                tasks, deadlines, financial_items, categories, is_manual_fetch
            )
            
        except Exception as e:
            logger.error(f"生成智能摘要失败: {e}")
            return self._generate_enhanced_fallback_summary(
                total_count, urgent_emails, important_emails, meetings, 
                tasks, deadlines, financial_items, categories, is_manual_fetch
            )
    
    def _generate_enhanced_fallback_summary(self, total_count, urgent_emails, important_emails, 
                                          meetings, tasks, deadlines, financial_items, categories, is_manual_fetch=False):
        """生成增强版备用摘要（当AI不可用时）
        
        Args:
            is_manual_fetch: 是否为手动实时收取
        """
        # 使用东八区时间
        from utils.timezone_helper import now_china_naive
        
        summary_parts = []
        
        # 根据收取方式决定开场
        if is_manual_fetch:
            # 手动收取：直接聚焦内容
            summary_parts.append(f"本次为您收取了 **{total_count}** 封邮件")
        else:
            # 定时收取：使用基于东八区的时间问候
            china_time = now_china_naive()
            hour = china_time.hour
            if 6 <= hour < 12:
                greeting = "早上好！☀️"
            elif 12 <= hour < 18:
                greeting = "下午好！🌤️"
            else:
                greeting = "晚上好！🌙"
            
            summary_parts.append(greeting)
            summary_parts.append(f"已为您整理了 **{total_count}** 封邮件")
        
        # 紧急提醒（更生动的表述）
        if urgent_emails:
            summary_parts.append(f"⚠️ 发现 **{len(urgent_emails)}** 封紧急邮件，建议立即关注")
            if urgent_emails[0]:
                subject = urgent_emails[0].get('subject', '')
                summary_parts.append(f"📌 最紧急的是：《{subject}》")
        
        # 会议提醒（更活泼）
        if meetings:
            summary_parts.append(f"📅 今天排了 **{len(meetings)}** 场会议，记得提前准备")
        
        # 任务提醒（增加活力）
        if tasks:
            summary_parts.append(f"✅ 有 **{len(tasks)}** 项待办任务等着您，加油")
        
        # 截止日期（增加紧迫感）
        if deadlines:
            summary_parts.append(f"⏰ **{len(deadlines)}** 个事项临近截止，时间紧迫，请注意")
        
        # 财务提醒（更醒目）
        if financial_items:
            summary_parts.append(f"💰 收到 **{len(financial_items)}** 封财务相关邮件，请及时查看")
        
        # 其他分类
        if important_emails and not urgent_emails:
            summary_parts.append(f"另有 **{len(important_emails)}** 封重要邮件值得关注")
        
        # 贴心建议（更生动）
        if urgent_emails or deadlines:
            summary_parts.append("🎯 建议按优先级处理：紧急邮件 > 临近deadline > 其他事项")
        elif meetings:
            summary_parts.append("🎯 建议先确认会议时间，做好充分准备")
        else:
            summary_parts.append("😊 邮件都比较常规，可以从容应对")
        
        return "。".join(summary_parts) + "。"
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
        """
        通用的AI文本生成方法
        
        参数:
        - prompt: 提示词
        - temperature: 温度参数，控制生成的随机性（0-1）
        - max_tokens: 最大生成token数
        
        返回:
        - 生成的文本，失败返回None
        """
        if self.provider == 'glm':
            return self._generate_with_glm(prompt, temperature, max_tokens)
        elif self.provider == 'openai':
            return self._generate_with_openai(prompt, temperature, max_tokens)
        else:
            logger.error(f"不支持的AI提供商: {self.provider}")
            return None
    
    def _generate_with_glm(self, prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        """使用GLM生成文本"""
        if not self.api_key:
            logger.error("GLM API key 未配置")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    return content
                else:
                    logger.error("GLM API 返回格式错误")
                    return None
            else:
                error_text = response.text
                logger.error(f"GLM API 调用失败: {response.status_code} - {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("GLM API 调用超时")
            return None
        except Exception as e:
            logger.error(f"GLM API 调用异常: {e}")
            return None
    
    def _generate_with_openai(self, prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
        """使用OpenAI生成文本"""
        if not self.api_key:
            logger.error("OpenAI API key 未配置")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    return content
                else:
                    logger.error("OpenAI API 返回格式错误")
                    return None
            else:
                error_text = response.text
                logger.error(f"OpenAI API 调用失败: {response.status_code} - {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("OpenAI API 调用超时")
            return None
        except Exception as e:
            logger.error(f"OpenAI API 调用异常: {e}")
            return None
    
    # ========================================================================
    # Function Call 支持
    # ========================================================================
    
    def chat_with_tools(self, messages: List[Dict], tools: List[Dict] = None, 
                       temperature: float = 0.7, max_tokens: int = 2000) -> Dict:
        """
        使用Function Call能力进行对话
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            tools: 工具定义列表（Function Call格式）
            temperature: 温度参数
            max_tokens: 最大token数
        
        Returns:
            {
                'content': '回复内容',
                'tool_calls': [工具调用列表],
                'finish_reason': '结束原因',
                'usage': {使用统计}
            }
        """
        if self.provider == 'glm':
            return self._chat_with_tools_glm(messages, tools, temperature, max_tokens)
        elif self.provider == 'openai':
            return self._chat_with_tools_openai(messages, tools, temperature, max_tokens)
        else:
            logger.error(f"不支持的AI提供商: {self.provider}")
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': f'不支持的AI提供商: {self.provider}'
            }
    
    def _chat_with_tools_glm(self, messages: List[Dict], tools: List[Dict], 
                            temperature: float, max_tokens: int) -> Dict:
        """使用GLM-4 Function Call"""
        if not self.api_key:
            logger.error("GLM API key 未配置")
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': 'GLM API key 未配置'
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # 添加工具定义
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"  # 让模型自动决定是否调用工具
        
        logger.info(f"GLM Function Call 请求: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60  # Function Call可能需要更长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"GLM Function Call 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    message = choice['message']
                    
                    return {
                        'content': message.get('content', ''),
                        'tool_calls': message.get('tool_calls', []),
                        'finish_reason': choice.get('finish_reason', 'stop'),
                        'usage': result.get('usage', {})
                    }
                else:
                    logger.error("GLM API 返回格式错误")
                    return {
                        'content': '',
                        'tool_calls': [],
                        'finish_reason': 'error',
                        'error': 'GLM API 返回格式错误'
                    }
            else:
                error_text = response.text
                logger.error(f"GLM Function Call 失败: {response.status_code} - {error_text}")
                return {
                    'content': '',
                    'tool_calls': [],
                    'finish_reason': 'error',
                    'error': f'GLM API 调用失败: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("GLM Function Call 超时")
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': 'GLM API 调用超时'
            }
        except Exception as e:
            logger.error(f"GLM Function Call 异常: {e}", exc_info=True)
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': f'GLM API 调用异常: {str(e)}'
            }
    
    def _chat_with_tools_openai(self, messages: List[Dict], tools: List[Dict], 
                               temperature: float, max_tokens: int) -> Dict:
        """使用OpenAI Function Call"""
        if not self.api_key:
            logger.error("OpenAI API key 未配置")
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': 'OpenAI API key 未配置'
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 添加工具定义
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        logger.info(f"OpenAI Function Call 请求: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"OpenAI Function Call 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    message = choice['message']
                    
                    return {
                        'content': message.get('content', ''),
                        'tool_calls': message.get('tool_calls', []),
                        'finish_reason': choice.get('finish_reason', 'stop'),
                        'usage': result.get('usage', {})
                    }
                else:
                    logger.error("OpenAI API 返回格式错误")
                    return {
                        'content': '',
                        'tool_calls': [],
                        'finish_reason': 'error',
                        'error': 'OpenAI API 返回格式错误'
                    }
            else:
                error_text = response.text
                logger.error(f"OpenAI Function Call 失败: {response.status_code} - {error_text}")
                return {
                    'content': '',
                    'tool_calls': [],
                    'finish_reason': 'error',
                    'error': f'OpenAI API 调用失败: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("OpenAI Function Call 超时")
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': 'OpenAI API 调用超时'
            }
        except Exception as e:
            logger.error(f"OpenAI Function Call 异常: {e}", exc_info=True)
            return {
                'content': '',
                'tool_calls': [],
                'finish_reason': 'error',
                'error': f'OpenAI API 调用异常: {str(e)}'
            }