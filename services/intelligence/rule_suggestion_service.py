#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则建议服务
分析用户手动分类行为，自动生成智能规则建议
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from models.database import Database

logger = logging.getLogger(__name__)

class RuleSuggestionService:
    """规则建议服务 - 从用户行为中学习"""
    
    def __init__(self):
        self.db = Database()
        
        # 建议生成阈值
        self.SENDER_THRESHOLD = 3  # 发件人出现>=3次生成建议
        self.DOMAIN_THRESHOLD = 5  # 域名出现>=5次生成建议
        self.KEYWORD_THRESHOLD = 4  # 关键词出现>=4次生成建议
        
        # 分析时间窗口
        self.ANALYSIS_DAYS = 30  # 分析最近30天的数据
    
    def analyze_user_behavior(self, user_id: int) -> List[Dict]:
        """
        分析用户手动修改行为，生成规则建议
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 规则建议列表
        """
        logger.info(f"开始分析用户 {user_id} 的分类行为...")
        
        try:
            # 1. 获取用户手动修改记录
            manual_changes = self._get_manual_changes(user_id)
            
            if not manual_changes:
                logger.info(f"用户 {user_id} 暂无手动分类记录")
                return []
            
            logger.info(f"获取到 {len(manual_changes)} 条手动分类记录")
            
            # 2. 提取模式
            patterns = self._extract_patterns(manual_changes)
            
            # 3. 生成建议
            suggestions = self._generate_suggestions(user_id, patterns)
            
            logger.info(f"为用户 {user_id} 生成了 {len(suggestions)} 条建议")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"分析用户行为失败: {e}")
            return []
    
    def _get_manual_changes(self, user_id: int) -> List[Dict]:
        """获取用户手动修改记录"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取最近30天的手动修改记录
                since_date = (datetime.now() - timedelta(days=self.ANALYSIS_DAYS)).isoformat()
                
                cursor.execute('''
                    SELECT 
                        id, email_id, sender, subject,
                        original_category, new_category,
                        original_importance, new_importance,
                        created_at
                    FROM manual_classification_history
                    WHERE user_id = ? AND created_at >= ?
                    ORDER BY created_at DESC
                ''', (user_id, since_date))
                
                changes = []
                for row in cursor.fetchall():
                    changes.append(dict(row))
                
                return changes
                
        except Exception as e:
            logger.error(f"获取手动修改记录失败: {e}")
            return []
    
    def _extract_patterns(self, manual_changes: List[Dict]) -> Dict:
        """
        从手动修改记录中提取模式
        
        Returns:
            {
                'frequent_senders': {sender: {'category': ..., 'importance': ..., 'count': ...}},
                'domain_patterns': {domain: {'category': ..., 'importance': ..., 'count': ...}},
                'subject_keywords': {keyword: {'category': ..., 'importance': ..., 'count': ...}}
            }
        """
        patterns = {
            'frequent_senders': defaultdict(lambda: defaultdict(int)),
            'domain_patterns': defaultdict(lambda: defaultdict(int)),
            'subject_keywords': defaultdict(lambda: defaultdict(int))
        }
        
        for change in manual_changes:
            sender = change['sender']
            category = change['new_category']
            importance = change['new_importance']
            subject = change.get('subject', '')
            
            # 1. 统计发件人
            if sender:
                key = f"{sender}:{category}:{importance}"
                patterns['frequent_senders'][sender]['count'] += 1
                patterns['frequent_senders'][sender]['category'] = category
                patterns['frequent_senders'][sender]['importance'] = importance
            
            # 2. 统计域名
            if sender and '@' in sender:
                domain = sender.split('@')[-1]
                key = f"{domain}:{category}:{importance}"
                patterns['domain_patterns'][domain]['count'] += 1
                patterns['domain_patterns'][domain]['category'] = category
                patterns['domain_patterns'][domain]['importance'] = importance
            
            # 3. 提取主题关键词（简单实现：提取长度>2的词）
            if subject:
                keywords = self._extract_keywords(subject)
                for keyword in keywords:
                    key = f"{keyword}:{category}:{importance}"
                    patterns['subject_keywords'][keyword]['count'] += 1
                    patterns['subject_keywords'][keyword]['category'] = category
                    patterns['subject_keywords'][keyword]['importance'] = importance
        
        return patterns
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        简单实现：分词并过滤
        """
        # 移除常见标点符号
        for char in ['，', '。', '！', '？', ',', '.', '!', '?', ':', '：', '-', '_']:
            text = text.replace(char, ' ')
        
        # 分词
        words = text.split()
        
        # 过滤：长度>2，非纯数字
        keywords = []
        for word in words:
            word = word.strip()
            if len(word) > 2 and not word.isdigit():
                keywords.append(word.lower())
        
        return keywords[:10]  # 最多返回10个关键词
    
    def _generate_suggestions(self, user_id: int, patterns: Dict) -> List[Dict]:
        """根据模式生成建议"""
        suggestions = []
        
        # 1. 发件人建议（精确匹配）
        for sender, data in patterns['frequent_senders'].items():
            count = data['count']
            if count >= self.SENDER_THRESHOLD:
                # 检查是否已有相同规则
                if not self._has_existing_rule(user_id, 'exact', sender, data['category']):
                    suggestion = {
                        'user_id': user_id,
                        'type': 'sender_exact',
                        'pattern': sender,
                        'target_category': data['category'],
                        'target_importance': data['importance'],
                        'confidence': min(count / 10.0, 0.95),
                        'reason': f'您已将来自 {sender} 的邮件修改为"{self._get_category_name(data["category"])}"类别 {count} 次',
                        'sample_count': count,
                        'priority': 10  # 建议优先级
                    }
                    suggestions.append(suggestion)
        
        # 2. 域名建议（域名匹配）
        for domain, data in patterns['domain_patterns'].items():
            count = data['count']
            if count >= self.DOMAIN_THRESHOLD:
                pattern = f'@{domain}'
                if not self._has_existing_rule(user_id, 'domain', pattern, data['category']):
                    suggestion = {
                        'user_id': user_id,
                        'type': 'sender_domain',
                        'pattern': pattern,
                        'target_category': data['category'],
                        'target_importance': data['importance'],
                        'confidence': min(count / 20.0, 0.90),
                        'reason': f'您已将来自 {domain} 域名的邮件修改为"{self._get_category_name(data["category"])}"类别 {count} 次',
                        'sample_count': count,
                        'priority': 8
                    }
                    suggestions.append(suggestion)
        
        # 3. 主题关键词建议
        for keyword, data in patterns['subject_keywords'].items():
            count = data['count']
            if count >= self.KEYWORD_THRESHOLD:
                if not self._has_existing_rule(user_id, 'subject_keyword', keyword, data['category']):
                    suggestion = {
                        'user_id': user_id,
                        'type': 'subject_keyword',
                        'pattern': keyword,
                        'target_category': data['category'],
                        'target_importance': data['importance'],
                        'confidence': min(count / 15.0, 0.85),
                        'reason': f'您已将主题包含"{keyword}"的邮件修改为"{self._get_category_name(data["category"])}"类别 {count} 次',
                        'sample_count': count,
                        'priority': 6
                    }
                    suggestions.append(suggestion)
        
        # 按置信度排序
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions
    
    def _has_existing_rule(self, user_id: int, match_type: str, pattern: str, category: str) -> bool:
        """检查是否已有相同的规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if match_type == 'exact':
                    cursor.execute('''
                        SELECT id FROM classification_rules
                        WHERE user_id = ? 
                          AND sender_match_type = 'exact'
                          AND sender_pattern = ?
                          AND target_category = ?
                          AND is_active = 1
                    ''', (user_id, pattern, category))
                    
                elif match_type == 'domain':
                    cursor.execute('''
                        SELECT id FROM classification_rules
                        WHERE user_id = ? 
                          AND sender_match_type = 'domain'
                          AND sender_pattern = ?
                          AND target_category = ?
                          AND is_active = 1
                    ''', (user_id, pattern, category))
                    
                elif match_type == 'subject_keyword':
                    cursor.execute('''
                        SELECT id, subject_keywords FROM classification_rules
                        WHERE user_id = ? 
                          AND target_category = ?
                          AND is_active = 1
                    ''', (user_id, category))
                    
                    # 检查关键词是否已在任何规则中
                    for row in cursor.fetchall():
                        keywords_json = row['subject_keywords']
                        if keywords_json:
                            try:
                                keywords = json.loads(keywords_json)
                                if pattern in keywords:
                                    return True
                            except:
                                pass
                    
                    return False
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"检查规则是否存在失败: {e}")
            return False
    
    def _get_category_name(self, category: str) -> str:
        """获取分类的中文名称"""
        category_names = {
            'work': '工作邮件',
            'finance': '财务邮件',
            'social': '社交邮件',
            'shopping': '购物邮件',
            'news': '资讯邮件',
            'education': '教育学习',
            'travel': '旅行出行',
            'health': '健康医疗',
            'system': '系统通知',
            'advertising': '广告邮件',
            'spam': '垃圾邮件',
            'general': '其他邮件'
        }
        return category_names.get(category, category)
    
    def save_suggestions_to_db(self, suggestions: List[Dict]) -> int:
        """
        将建议保存到数据库
        
        Returns:
            int: 保存成功的数量
        """
        if not suggestions:
            return 0
        
        saved_count = 0
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                for sugg in suggestions:
                    try:
                        # 检查是否已存在相同建议
                        cursor.execute('''
                            SELECT id FROM classification_suggestions
                            WHERE user_id = ? 
                              AND suggestion_type = ?
                              AND pattern_data LIKE ?
                              AND is_applied = 0
                        ''', (sugg['user_id'], sugg['type'], f'%{sugg["pattern"]}%'))
                        
                        if cursor.fetchone():
                            continue  # 已存在，跳过
                        
                        # 插入新建议
                        pattern_data = json.dumps(sugg, ensure_ascii=False)
                        
                        cursor.execute('''
                            INSERT INTO classification_suggestions
                            (user_id, suggestion_type, suggested_category, suggested_importance,
                             pattern_data, confidence, sample_count, sender_pattern, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            sugg['user_id'],
                            sugg['type'],
                            sugg['target_category'],
                            sugg['target_importance'],
                            pattern_data,
                            sugg['confidence'],
                            sugg['sample_count'],
                            sugg.get('pattern', ''),
                            datetime.now().isoformat()
                        ))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"保存单个建议失败: {e}")
                        continue
                
                conn.commit()
                logger.info(f"成功保存 {saved_count} 条建议到数据库")
                
        except Exception as e:
            logger.error(f"保存建议到数据库失败: {e}")
        
        return saved_count
    
    def get_user_suggestions(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户的智能建议"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM classification_suggestions
                    WHERE user_id = ? AND is_applied = 0
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                suggestions = []
                for row in cursor.fetchall():
                    sugg = dict(row)
                    
                    # 字段名映射
                    if 'suggested_category' in sugg:
                        sugg['target_category'] = sugg['suggested_category']
                    if 'suggested_importance' in sugg:
                        sugg['target_importance'] = sugg['suggested_importance']
                    if 'suggestion_type' in sugg:
                        sugg['type'] = sugg['suggestion_type']
                    
                    # 解析pattern_data
                    if sugg.get('pattern_data'):
                        try:
                            pattern_data = json.loads(sugg['pattern_data'])
                            sugg.update(pattern_data)
                        except:
                            pass
                    
                    # 如果没有pattern字段，使用sender_pattern
                    if 'pattern' not in sugg and 'sender_pattern' in sugg:
                        sugg['pattern'] = sugg['sender_pattern']
                    
                    suggestions.append(sugg)
                
                return suggestions
                
        except Exception as e:
            logger.error(f"获取用户建议失败: {e}")
            return []
    
    def apply_suggestion(self, suggestion_id: int, user_id: int) -> Optional[int]:
        """
        应用建议，创建规则
        
        Returns:
            Optional[int]: 创建的规则ID，失败返回None
        """
        try:
            # 1. 获取建议
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM classification_suggestions
                    WHERE id = ? AND user_id = ?
                ''', (suggestion_id, user_id))
                
                sugg_row = cursor.fetchone()
                if not sugg_row:
                    logger.warning(f"建议 {suggestion_id} 不存在")
                    return None
                
                sugg = dict(sugg_row)
                
                # 解析pattern_data
                pattern_data = json.loads(sugg['pattern_data']) if sugg.get('pattern_data') else {}
                
                # 从数据库字段获取基本信息
                suggestion_type = sugg.get('suggestion_type', pattern_data.get('type', ''))
                target_category = sugg.get('suggested_category', pattern_data.get('target_category', ''))
                target_importance = sugg.get('suggested_importance', pattern_data.get('target_importance', 2))
                pattern = sugg.get('sender_pattern', pattern_data.get('pattern', ''))
                
                # 2. 创建规则
                rule_data = {
                    'rule_name': f"智能建议: {pattern_data.get('reason', pattern)}",
                    'target_category': target_category,
                    'target_importance': target_importance,
                    'priority': pattern_data.get('priority', 5),
                    'is_active': True
                }
                
                # 根据类型设置规则参数
                if suggestion_type == 'sender_exact':
                    rule_data['sender_pattern'] = pattern
                    rule_data['sender_match_type'] = 'exact'
                    
                elif suggestion_type == 'sender_domain':
                    rule_data['sender_pattern'] = pattern
                    rule_data['sender_match_type'] = 'domain'
                    
                elif suggestion_type == 'subject_keyword':
                    rule_data['subject_keywords'] = json.dumps([pattern], ensure_ascii=False)
                    rule_data['subject_logic'] = 'OR'
                
                # 导入分类服务创建规则
                from services.classification_service import ClassificationService
                classification_service = ClassificationService()
                
                rule = classification_service.create_rule(user_id, rule_data)
                
                # 3. 标记建议为已应用
                cursor.execute('''
                    UPDATE classification_suggestions
                    SET is_applied = 1, applied_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), suggestion_id))
                conn.commit()
                
                logger.info(f"成功应用建议 {suggestion_id}，创建规则 {rule['id']}")
                
                return rule['id']
                
        except Exception as e:
            logger.error(f"应用建议失败: {e}")
            return None

