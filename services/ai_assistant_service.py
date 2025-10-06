#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - AI助手服务
提供智能对话、邮件搜索、意图识别等功能
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz

from models.database import Database
from services.ai_client import AIClient

logger = logging.getLogger(__name__)


class IntentParser:
    """意图识别引擎"""
    
    # 意图类型定义
    INTENT_SEARCH = "search_emails"
    INTENT_REPLY = "reply_email"
    INTENT_SUMMARIZE = "summarize"
    INTENT_STATISTICS = "statistics"
    INTENT_GENERAL = "general_chat"
    
    # 时间关键词映射
    TIME_KEYWORDS = {
        '今天': {'type': 'relative', 'days': 0},
        '今日': {'type': 'relative', 'days': 0},
        '昨天': {'type': 'relative', 'days': 1},
        '前天': {'type': 'relative', 'days': 2},
        '本周': {'type': 'week', 'value': 0},
        '上周': {'type': 'week', 'value': -1},
        '本月': {'type': 'month', 'value': 0},
        '上月': {'type': 'month', 'value': -1},
    }
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    def parse(self, user_message: str, context: Dict = None) -> Dict:
        """
        解析用户消息，识别意图和提取参数
        
        返回格式:
        {
            'intent': 'search_emails',
            'confidence': 0.95,
            'parameters': {
                'time_range': {...},
                'sender': {...},
                'keywords': [...],
                'email_ids': [...]
            },
            'response_type': 'text' | 'email_list' | 'action'
        }
        """
        context = context or {}
        
        # 1. 使用规则快速匹配常见意图
        rule_result = self._rule_based_intent(user_message)
        if rule_result and rule_result.get('confidence', 0) > 0.8:
            return rule_result
        
        # 2. 使用AI进行深度意图识别
        try:
            ai_result = self._ai_based_intent(user_message, context)
            if ai_result:
                return ai_result
        except Exception as e:
            logger.error(f"AI意图识别失败: {e}")
        
        # 3. 降级到规则结果或默认意图
        return rule_result or self._default_intent(user_message)
    
    def _rule_based_intent(self, message: str) -> Optional[Dict]:
        """基于规则的快速意图识别"""
        message_lower = message.lower()
        
        # 搜索邮件意图
        search_patterns = [
            r'(查找|搜索|找|看|显示|列出|有没有|检索)(.*?)(邮件|信|消息)',
            r'(今天|昨天|最近|近\d+天)(.*?)(邮件|信)',
            r'([^发给我的]*)(发给我|给我发|寄给我)(.*?)(邮件|信)',
        ]
        
        for pattern in search_patterns:
            if re.search(pattern, message):
                params = self._extract_search_params(message)
                return {
                    'intent': self.INTENT_SEARCH,
                    'confidence': 0.9,
                    'parameters': params,
                    'response_type': 'email_list'
                }
        
        # 回复邮件意图
        reply_patterns = [
            r'(回复|回|答复)(这封|那封)?(邮件|信)',
            r'帮我(回|写)(.*?)(邮件|信)',
        ]
        
        for pattern in reply_patterns:
            if re.search(pattern, message):
                return {
                    'intent': self.INTENT_REPLY,
                    'confidence': 0.85,
                    'parameters': {},
                    'response_type': 'action'
                }
        
        # 统计意图
        stats_patterns = [
            r'(统计|多少|数量|总共|总计)',
            r'(分析|报告|概览|总结)',
        ]
        
        for pattern in stats_patterns:
            if re.search(pattern, message):
                return {
                    'intent': self.INTENT_STATISTICS,
                    'confidence': 0.8,
                    'parameters': self._extract_search_params(message),
                    'response_type': 'text'
                }
        
        return None
    
    def _extract_search_params(self, message: str) -> Dict:
        """从消息中提取搜索参数"""
        params = {}
        
        # 1. 提取时间范围
        time_range = self._extract_time_range(message)
        if time_range:
            params['time_range'] = time_range
            logger.info(f"提取到时间范围: {time_range}")
        
        # 2. 提取发件人
        sender = self._extract_sender(message)
        if sender:
            params['sender'] = sender
            logger.info(f"提取到发件人: {sender}")
        
        # 3. 提取分类
        category = self._extract_category(message)
        if category:
            params['category'] = category
            logger.info(f"提取到分类: {category}")
        
        # 4. 提取关键词
        keywords = self._extract_keywords(message)
        if keywords:
            params['keywords'] = keywords
            logger.info(f"提取到关键词: {keywords}")
        
        logger.info(f"最终提取的搜索参数: {params}")
        return params
    
    def _extract_category(self, message: str) -> Optional[str]:
        """提取邮件分类"""
        # 分类关键词映射
        category_keywords = {
            '重要': ['重要', '紧急', 'important', 'urgent'],
            '工作': ['工作', '办公', 'work', 'office', '项目', 'project'],
            '财务': ['财务', '金融', '账单', '发票', 'finance', 'bill', 'invoice'],
            '社交': ['社交', '朋友', '聚会', 'social', 'friend'],
            '购物': ['购物', '订单', '快递', 'shopping', 'order', '电商'],
            '新闻': ['新闻', '资讯', '通知', 'news', 'notification'],
        }
        
        message_lower = message.lower()
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    logger.info(f"匹配到分类关键词: '{keyword}' -> 分类: '{category}'")
                    return category
        
        return None
    
    def _extract_time_range(self, message: str) -> Optional[Dict]:
        """提取时间范围"""
        # 匹配预定义关键词
        for keyword, time_info in self.TIME_KEYWORDS.items():
            if keyword in message:
                return time_info
        
        # 匹配"近N天"格式
        match = re.search(r'近(\d+)天', message)
        if match:
            days = int(match.group(1))
            return {'type': 'relative', 'days': days}
        
        # 匹配"最近N天"格式
        match = re.search(r'最近(\d+)天', message)
        if match:
            days = int(match.group(1))
            return {'type': 'relative', 'days': days}
        
        # 匹配具体日期
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', message)
        if date_match:
            return {
                'type': 'absolute',
                'date': f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            }
        
        return None
    
    def _extract_sender(self, message: str) -> Optional[Dict]:
        """提取发件人信息"""
        # 模式: "XXX发给我"、"来自XXX"、"XXX的邮件"
        patterns = [
            r'([^\s发给我的]{2,10})(发给我|给我发|寄给我)',
            r'来自([^\s的]{2,10})',
            r'([^\s]{2,10})(的邮件|的信)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                sender_name = match.group(1).strip()
                # 过滤掉时间词等
                if sender_name not in ['今天', '昨天', '最近', '本周', '上周']:
                    return {'name': sender_name}
        
        # 检查是否有邮箱地址
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
        if email_match:
            return {'email': email_match.group(0)}
        
        return None
    
    def _extract_keywords(self, message: str) -> List[str]:
        """提取关键词"""
        # 简单实现：移除常见停用词后的剩余词汇
        stop_words = {'帮我', '请', '看', '查', '找', '有', '吗', '的', '了', '是', 
                     '邮件', '信', '消息', '一下', '下', '今天', '昨天', '最近'}
        
        # 简单分词（按空格和标点）
        words = re.findall(r'[\w]+', message)
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        return keywords[:5]  # 最多返回5个关键词
    
    def _ai_based_intent(self, message: str, context: Dict) -> Optional[Dict]:
        """基于AI的深度意图识别"""
        prompt = f"""
分析以下用户查询并返回JSON格式的意图识别结果：

用户查询: {message}

请识别用户的意图类型并提取相关参数。返回格式：
{{
    "intent": "search_emails | reply_email | summarize | statistics | general_chat",
    "confidence": 0.0-1.0,
    "parameters": {{
        "time_range": {{"type": "relative|absolute|week|month", "days": 3, "value": 0}},
        "sender": {{"name": "发件人名称", "email": "邮箱地址"}},
        "keywords": ["关键词1", "关键词2"],
        "category": "工作|金融|社交|购物|新闻|通用"
    }},
    "response_type": "text | email_list | action"
}}

注意：
1. 仅返回JSON，不要包含其他说明文字
2. 如果某个参数不存在，设为null
3. confidence表示意图识别的置信度
4. response_type表示期望的响应类型
"""
        
        try:
            response = self.ai_client.generate(prompt)
            if not response:
                return None
            
            # 清理响应，提取JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"AI意图识别返回JSON解析失败: {e}, 响应: {response}")
            return None
        except Exception as e:
            logger.error(f"AI意图识别异常: {e}")
            return None
    
    def _default_intent(self, message: str) -> Dict:
        """默认意图（一般对话）"""
        return {
            'intent': self.INTENT_GENERAL,
            'confidence': 0.5,
            'parameters': {},
            'response_type': 'text'
        }


class EmailSearchEngine:
    """邮件搜索引擎"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def search(self, user_id: int, parameters: Dict) -> List[Dict]:
        """
        根据参数搜索邮件
        
        参数:
        - user_id: 用户ID
        - parameters: 搜索参数字典
        """
        # 构建SQL查询
        sql_parts = ["SELECT * FROM emails WHERE user_id = ? AND deleted = 0"]
        params = [user_id]
        
        # 时间范围过滤
        time_filter = self._build_time_filter(parameters.get('time_range'))
        if time_filter:
            sql_parts.append(time_filter['sql'])
            params.extend(time_filter['params'])
        
        # 发件人过滤
        sender_filter = self._build_sender_filter(parameters.get('sender'))
        if sender_filter:
            sql_parts.append(sender_filter['sql'])
            params.extend(sender_filter['params'])
        
        # 分类过滤（增强版：支持importance筛选）
        category = parameters.get('category')
        if category:
            logger.info(f"分类过滤: category={category}")
            
            # 特殊处理：重要邮件
            if category in ['重要', '重要邮件', 'important']:
                logger.info("使用importance筛选重要邮件 (importance >= 3)")
                sql_parts.append("importance >= 3")
            # 其他分类
            else:
                logger.info(f"使用category筛选: {category}")
                sql_parts.append("category = ?")
                params.append(category)
        
        # 关键词搜索
        keyword_filter = self._build_keyword_filter(parameters.get('keywords'))
        if keyword_filter:
            sql_parts.append(keyword_filter['sql'])
            params.extend(keyword_filter['params'])
        
        # 组合查询
        sql = " AND ".join(sql_parts)
        sql += " ORDER BY date DESC LIMIT 50"
        
        # 详细日志
        logger.info(f"邮件搜索SQL: {sql}")
        logger.info(f"邮件搜索参数: {params}")
        logger.info(f"搜索条件详情: {parameters}")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 转换为字典列表
                emails = []
                for row in rows:
                    email = dict(row)
                    # 解析JSON字段
                    if email.get('recipients'):
                        try:
                            email['recipients'] = json.loads(email['recipients'])
                        except:
                            pass
                    if email.get('attachments'):
                        try:
                            email['attachments'] = json.loads(email['attachments'])
                        except:
                            pass
                    emails.append(email)
                
                logger.info(f"邮件搜索完成，找到 {len(emails)} 封邮件")
                if len(emails) > 0:
                    logger.info(f"第一封邮件日期: {emails[0].get('date')}, 主题: {emails[0].get('subject')}")
                return emails
                
        except Exception as e:
            logger.error(f"邮件搜索失败: {e}")
            return []
    
    def _build_time_filter(self, time_range: Optional[Dict]) -> Optional[Dict]:
        """构建时间过滤条件"""
        if not time_range:
            return None
        
        time_type = time_range.get('type')
        logger.info(f"构建时间过滤条件: type={time_type}, range={time_range}")
        
        from datetime import datetime, timedelta
        
        if time_type == 'relative':
            days = time_range.get('days', 0)
            
            if days == 0:
                # 今天：从今天00:00:00开始
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                date_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"今天的邮件，开始时间: {date_str}")
                return {
                    'sql': "date >= ?",
                    'params': [date_str]
                }
            elif days == 1:
                # 昨天：昨天00:00:00到今天00:00:00
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday_start = (today_start - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                today_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"昨天的邮件，时间范围: {yesterday_start} 到 {today_str}")
                return {
                    'sql': "(date >= ? AND date < ?)",
                    'params': [yesterday_start, today_str]
                }
            else:
                # 近N天（包括今天）
                target_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
                date_str = target_date.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"近{days}天的邮件，开始时间: {date_str}")
                return {
                    'sql': "date >= ?",
                    'params': [date_str]
                }
        
        elif time_type == 'week':
            value = time_range.get('value', 0)
            # 本周：从本周一00:00:00开始
            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            if value != 0:
                week_start = week_start + timedelta(weeks=value)
            date_str = week_start.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"周过滤(value={value})，开始时间: {date_str}")
            return {
                'sql': "date >= ?",
                'params': [date_str]
            }
        
        elif time_type == 'month':
            value = time_range.get('value', 0)
            # 本月：从本月1号00:00:00开始
            today = datetime.now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if value != 0:
                # 计算几个月前
                month = month_start.month + value
                year = month_start.year
                while month <= 0:
                    month += 12
                    year -= 1
                month_start = month_start.replace(year=year, month=month)
            date_str = month_start.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"月过滤(value={value})，开始时间: {date_str}")
            return {
                'sql': "date >= ?",
                'params': [date_str]
            }
        
        elif time_type == 'absolute':
            date_str = time_range.get('date')
            if date_str:
                logger.info(f"绝对日期过滤: {date_str}")
                return {
                    'sql': "date(date) = date(?)",
                    'params': [date_str]
                }
        
        logger.warning(f"无法识别的时间类型: {time_type}")
        return None
    
    def _build_sender_filter(self, sender: Optional[Dict]) -> Optional[Dict]:
        """构建发件人过滤条件"""
        if not sender:
            return None
        
        if sender.get('email'):
            # 精确邮箱匹配
            return {
                'sql': "sender LIKE ?",
                'params': [f"%{sender['email']}%"]
            }
        
        if sender.get('name'):
            # 名称模糊匹配
            name = sender['name']
            return {
                'sql': "(sender LIKE ? OR sender LIKE ?)",
                'params': [f"%{name}%", f"%<*{name}*>%"]
            }
        
        return None
    
    def _build_keyword_filter(self, keywords: Optional[List[str]]) -> Optional[Dict]:
        """构建关键词过滤条件"""
        if not keywords or len(keywords) == 0:
            return None
        
        # 在主题和正文中搜索关键词
        conditions = []
        params = []
        
        for keyword in keywords:
            conditions.append("(subject LIKE ? OR body LIKE ?)")
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")
        
        sql = " OR ".join(conditions)
        return {
            'sql': f"({sql})",
            'params': params
        }


class AIAssistantService:
    """AI助手核心服务"""
    
    def __init__(self):
        self.db = Database()
        self.ai_client = AIClient()
        self.intent_parser = IntentParser(self.ai_client)
        self.search_engine = EmailSearchEngine(self.db)
    
    def process_message(self, user_id: int, message: str, context: Dict = None) -> Dict:
        """
        处理用户消息
        
        返回格式:
        {
            'response': '回复文本',
            'emails': [...],  # 相关邮件列表
            'intent': '识别的意图',
            'actions': [...], # 可执行的操作
            'success': True/False
        }
        """
        try:
            logger.info(f"AI助手处理消息: 用户={user_id}, 消息={message}")
            
            # 1. 意图识别
            intent_result = self.intent_parser.parse(message, context)
            intent = intent_result.get('intent')
            params = intent_result.get('parameters', {})
            
            logger.info(f"意图识别结果: {intent}, 参数: {params}")
            
            # 2. 根据意图处理
            if intent == IntentParser.INTENT_SEARCH:
                return self._handle_search(user_id, message, params)
            
            elif intent == IntentParser.INTENT_STATISTICS:
                return self._handle_statistics(user_id, message, params)
            
            elif intent == IntentParser.INTENT_REPLY:
                return self._handle_reply(user_id, message, context)
            
            elif intent == IntentParser.INTENT_SUMMARIZE:
                return self._handle_summarize(user_id, message, context)
            
            else:
                # 一般对话
                return self._handle_general_chat(user_id, message)
        
        except Exception as e:
            logger.error(f"AI助手处理消息失败: {e}")
            return {
                'response': f'抱歉，处理您的请求时出现了错误。请稍后再试。',
                'emails': [],
                'intent': 'error',
                'actions': [],
                'success': False
            }
    
    def _handle_search(self, user_id: int, message: str, params: Dict) -> Dict:
        """处理邮件搜索请求"""
        # 搜索邮件
        emails = self.search_engine.search(user_id, params)
        
        # 生成响应文本
        if len(emails) == 0:
            response = self._generate_no_result_response(params)
        else:
            response = self._generate_search_response(emails, params)
        
        return {
            'response': response,
            'emails': emails,
            'intent': 'search_emails',
            'actions': [],
            'success': True
        }
    
    def _handle_statistics(self, user_id: int, message: str, params: Dict) -> Dict:
        """处理统计分析请求"""
        # 搜索邮件
        emails = self.search_engine.search(user_id, params)
        
        # 生成统计信息
        stats = {
            'total': len(emails),
            'by_category': {},
            'by_sender': {}
        }
        
        for email in emails:
            # 按分类统计
            category = email.get('category', 'general')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # 按发件人统计
            sender = email.get('sender', 'unknown')
            stats['by_sender'][sender] = stats['by_sender'].get(sender, 0) + 1
        
        # 生成响应
        response = self._generate_stats_response(stats, params)
        
        return {
            'response': response,
            'emails': emails[:10],  # 只返回前10封作为示例
            'intent': 'statistics',
            'actions': [],
            'success': True,
            'statistics': stats
        }
    
    def _handle_reply(self, user_id: int, message: str, context: Dict) -> Dict:
        """处理回复邮件请求"""
        # 检查上下文中是否有选中的邮件
        selected_email_ids = context.get('selected_email_ids', []) if context else []
        
        if not selected_email_ids:
            return {
                'response': '请先选择要回复的邮件。点击下方的"选择邮件"按钮来选择一封邮件。',
                'emails': [],
                'intent': 'reply_email',
                'actions': [{'type': 'select_email', 'label': '选择邮件'}],
                'success': False
            }
        
        # 获取邮件详情
        email_id = selected_email_ids[0]
        email = self.db.get_email_by_id(email_id)
        
        if not email:
            return {
                'response': '抱歉，无法找到该邮件。',
                'emails': [],
                'intent': 'reply_email',
                'actions': [],
                'success': False
            }
        
        return {
            'response': f'好的，我将帮您回复邮件《{email.get("subject", "无主题")}》。请问您想如何回复？',
            'emails': [email],
            'intent': 'reply_email',
            'actions': [
                {'type': 'generate_reply', 'label': '生成回复草稿', 'email_id': email_id},
                {'type': 'open_compose', 'label': '打开撰写窗口', 'email_id': email_id}
            ],
            'success': True
        }
    
    def _handle_summarize(self, user_id: int, message: str, context: Dict) -> Dict:
        """处理总结请求"""
        # 获取最近的邮件
        params = context.get('parameters', {}) if context else {}
        emails = self.search_engine.search(user_id, params)
        
        if len(emails) == 0:
            return {
                'response': '没有找到相关邮件可以总结。',
                'emails': [],
                'intent': 'summarize',
                'actions': [],
                'success': False
            }
        
        # 使用AI生成总结
        summary_prompt = self._create_summary_prompt(emails)
        summary = self.ai_client.generate(summary_prompt)
        
        return {
            'response': summary or '抱歉，生成总结失败。',
            'emails': emails[:10],
            'intent': 'summarize',
            'actions': [],
            'success': bool(summary)
        }
    
    def _handle_general_chat(self, user_id: int, message: str) -> Dict:
        """处理一般对话"""
        # 使用AI生成回复
        prompt = f"""
你是一个智能邮件助手，帮助用户管理和查询邮件。
用户说：{message}

请用友好、专业的语气回复用户，并提示用户可以：
1. 搜索邮件（例如："帮我找今天的邮件"）
2. 查看特定发件人的邮件（例如："小明发给我的邮件"）
3. 统计邮件（例如："本周收到多少邮件"）
4. 回复邮件（例如："帮我回复这封邮件"）

简短回复（不超过100字）：
"""
        
        response = self.ai_client.generate(prompt)
        
        return {
            'response': response or '您好！我是您的邮件助手，有什么可以帮您的吗？',
            'emails': [],
            'intent': 'general_chat',
            'actions': [],
            'success': True
        }
    
    def _generate_search_response(self, emails: List[Dict], params: Dict) -> str:
        """生成搜索结果响应文本"""
        count = len(emails)
        
        # 构建描述性文本
        desc_parts = []
        
        if params.get('time_range'):
            time_desc = self._describe_time_range(params['time_range'])
            desc_parts.append(time_desc)
        
        if params.get('sender'):
            sender = params['sender']
            sender_name = sender.get('name') or sender.get('email')
            desc_parts.append(f"来自{sender_name}")
        
        if params.get('keywords'):
            keywords_str = '、'.join(params['keywords'])
            desc_parts.append(f"包含关键词「{keywords_str}」")
        
        desc = ''.join(desc_parts) if desc_parts else ''
        
        if count == 0:
            return f"没有找到{desc}的邮件。"
        else:
            return f"找到了{count}封{desc}的邮件，按时间倒序排列如下："
    
    def _generate_no_result_response(self, params: Dict) -> str:
        """生成无结果响应（增强版：提供具体建议）"""
        desc_parts = []
        suggestions = []
        
        # 构建描述
        if params.get('time_range'):
            time_desc = self._describe_time_range(params['time_range'])
            desc_parts.append(time_desc)
            suggestions.append("尝试扩大时间范围，比如「本周」或「近7天」")
        
        if params.get('category'):
            category = params['category']
            desc_parts.append(f"「{category}」类型")
            suggestions.append("检查邮件分类是否正确，或搜索其他分类")
        
        if params.get('sender'):
            sender = params['sender']
            sender_name = sender.get('name') or sender.get('email')
            desc_parts.append(f"来自「{sender_name}」")
            suggestions.append("确认发件人名称或邮箱是否正确")
        
        if params.get('keywords'):
            keywords_str = '、'.join(params['keywords'])
            desc_parts.append(f"包含关键词「{keywords_str}」")
            suggestions.append("尝试使用更通用的关键词")
        
        desc = '的'.join(desc_parts) if desc_parts else ''
        
        # 生成友好的响应
        response = f"😔 抱歉，没有找到{desc}的邮件。\n\n"
        
        if suggestions:
            response += "💡 建议：\n"
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
        else:
            response += "💡 建议：\n"
            response += "1. 尝试使用更通用的搜索条件\n"
            response += "2. 检查邮件是否已被删除或归档\n"
            response += "3. 尝试「所有邮件」或「最近的邮件」\n"
        
        return response
    
    def _generate_stats_response(self, stats: Dict, params: Dict) -> str:
        """生成统计响应"""
        total = stats['total']
        by_category = stats['by_category']
        
        response = f"统计结果：共找到 {total} 封邮件\n\n"
        
        if by_category:
            response += "📊 按分类统计：\n"
            category_names = {
                'work': '工作',
                'finance': '金融',
                'social': '社交',
                'shopping': '购物',
                'news': '新闻',
                'general': '通用'
            }
            for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
                category_name = category_names.get(category, category)
                response += f"  • {category_name}: {count} 封\n"
        
        return response
    
    def _describe_time_range(self, time_range: Dict) -> str:
        """描述时间范围"""
        time_type = time_range.get('type')
        
        if time_type == 'relative':
            days = time_range.get('days', 0)
            if days == 0:
                return "今天"
            elif days == 1:
                return "昨天"
            else:
                return f"近{days}天"
        elif time_type == 'week':
            value = time_range.get('value', 0)
            if value == 0:
                return "本周"
            elif value == -1:
                return "上周"
            else:
                return f"{value}周前"
        elif time_type == 'month':
            value = time_range.get('value', 0)
            if value == 0:
                return "本月"
            elif value == -1:
                return "上月"
            else:
                return f"{value}月前"
        elif time_type == 'absolute':
            return time_range.get('date', '')
        
        return ''
    
    def _create_summary_prompt(self, emails: List[Dict]) -> str:
        """创建邮件总结提示词"""
        email_summaries = []
        for email in emails[:10]:  # 最多总结前10封
            email_summaries.append(f"""
主题: {email.get('subject', '无主题')}
发件人: {email.get('sender', '未知')}
时间: {email.get('date', '未知')}
摘要: {email.get('summary') or email.get('body', '')[:200]}
""")
        
        prompt = f"""
请对以下邮件进行总结，提取关键信息：

{''.join(email_summaries)}

要求：
1. 总结应简洁明了，不超过200字
2. 突出重要邮件和关键信息
3. 按主题分类总结
4. 使用中文

总结：
"""
        return prompt

