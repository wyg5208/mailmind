#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件分类系统 - 规则匹配引擎
提供强大的模式匹配功能
"""

import re
import fnmatch
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RuleMatcher:
    """规则匹配引擎"""
    
    @staticmethod
    def match_sender(sender: str, pattern: str, match_type: str) -> bool:
        """
        发件人匹配
        
        Args:
            sender: 发件人邮箱地址
            pattern: 匹配模式
            match_type: 匹配类型 (exact/contains/domain/regex/wildcard)
            
        Returns:
            bool: 是否匹配成功
        """
        if not sender or not pattern:
            return False
        
        sender = sender.lower().strip()
        pattern = pattern.lower().strip()
        
        try:
            if match_type == 'exact':
                # 精确匹配
                return sender == pattern
            
            elif match_type == 'contains':
                # 包含匹配
                return pattern in sender
            
            elif match_type == 'domain':
                # 域名匹配
                if pattern.startswith('@'):
                    # @company.com - 匹配整个域名
                    return sender.endswith(pattern)
                else:
                    # company.com - 包含即可
                    return pattern in sender
            
            elif match_type == 'wildcard':
                # 通配符匹配 (*@*.edu.cn)
                return fnmatch.fnmatch(sender, pattern)
            
            elif match_type == 'regex':
                # 正则表达式匹配
                return bool(re.search(pattern, sender, re.IGNORECASE))
            
            else:
                logger.warning(f"未知的匹配类型: {match_type}，使用包含匹配")
                return pattern in sender
                
        except Exception as e:
            logger.error(f"发件人匹配失败: sender={sender}, pattern={pattern}, type={match_type}, error={e}")
            return False
    
    @staticmethod
    def match_keywords(text: str, keywords: List[str], logic: str = 'OR') -> bool:
        """
        关键词匹配（支持AND/OR逻辑）
        
        Args:
            text: 要匹配的文本
            keywords: 关键词列表
            logic: 逻辑关系 (AND/OR)
            
        Returns:
            bool: 是否匹配成功
        """
        if not keywords:
            return True  # 没有关键词要求，视为匹配
        
        if not text:
            return False
        
        text_lower = text.lower().strip()
        matches = [kw.lower().strip() in text_lower for kw in keywords if kw]
        
        if not matches:
            return True  # 如果关键词列表为空（过滤后），视为匹配
        
        if logic == 'AND':
            return all(matches)
        else:  # OR
            return any(matches)
    
    @staticmethod
    def calculate_rule_score(rule: Dict, email: Dict) -> float:
        """
        计算规则匹配得分（用于多规则优先级排序）
        
        Args:
            rule: 规则数据
            email: 邮件数据
            
        Returns:
            float: 匹配得分（越高越优先）
        """
        score = float(rule.get('priority', 5))  # 基础优先级
        
        # 精确匹配加分
        if rule.get('sender_match_type') == 'exact':
            score += 10
        
        # 多条件匹配加分
        condition_count = 0
        
        if rule.get('sender_pattern'):
            condition_count += 1
        
        if rule.get('subject_keywords'):
            try:
                import json
                keywords = json.loads(rule.get('subject_keywords', '[]'))
                if keywords:
                    condition_count += 1
            except:
                pass
        
        if rule.get('body_keywords'):
            try:
                import json
                keywords = json.loads(rule.get('body_keywords', '[]'))
                if keywords:
                    condition_count += 1
            except:
                pass
        
        # 每个条件加5分
        score += condition_count * 5
        
        # 域名匹配加分（比包含匹配更精确）
        if rule.get('sender_match_type') == 'domain':
            score += 5
        
        return score
    
    @staticmethod
    def match_rule(rule: Dict, email: Dict) -> bool:
        """
        检查邮件是否匹配规则
        
        Args:
            rule: 规则数据
            email: 邮件数据
            
        Returns:
            bool: 是否匹配
        """
        import json
        
        # 规则必须是启用状态
        if not rule.get('is_active', True):
            return False
        
        matches = []
        
        # 1. 发件人匹配
        sender_pattern = rule.get('sender_pattern')
        if sender_pattern:
            sender = email.get('sender', '')
            match_type = rule.get('sender_match_type', 'contains')
            sender_match = RuleMatcher.match_sender(sender, sender_pattern, match_type)
            matches.append(sender_match)
            
            if not sender_match:
                logger.debug(f"规则 '{rule.get('rule_name')}' 发件人不匹配: {sender} vs {sender_pattern}")
                return False  # 发件人条件不满足，直接返回
        
        # 2. 主题关键词匹配
        subject_keywords = rule.get('subject_keywords')
        if subject_keywords:
            try:
                keywords = json.loads(subject_keywords) if isinstance(subject_keywords, str) else subject_keywords
                if keywords:
                    subject = email.get('subject', '')
                    logic = rule.get('subject_logic', 'OR')
                    subject_match = RuleMatcher.match_keywords(subject, keywords, logic)
                    matches.append(subject_match)
                    
                    if not subject_match:
                        logger.debug(f"规则 '{rule.get('rule_name')}' 主题不匹配: {subject}")
                        return False
            except Exception as e:
                logger.error(f"解析主题关键词失败: {e}")
        
        # 3. 正文关键词匹配
        body_keywords = rule.get('body_keywords')
        if body_keywords:
            try:
                keywords = json.loads(body_keywords) if isinstance(body_keywords, str) else body_keywords
                if keywords:
                    body = email.get('body', '')
                    # 正文关键词默认使用OR逻辑
                    body_match = RuleMatcher.match_keywords(body, keywords, 'OR')
                    matches.append(body_match)
                    
                    if not body_match:
                        logger.debug(f"规则 '{rule.get('rule_name')}' 正文不匹配")
                        return False
            except Exception as e:
                logger.error(f"解析正文关键词失败: {e}")
        
        # 所有条件都满足才算匹配
        result = all(matches) if matches else False
        
        if result:
            logger.info(f"✅ 邮件匹配规则 '{rule.get('rule_name')}' (优先级: {rule.get('priority')})")
        
        return result
    
    @staticmethod
    def test_rule(rule: Dict, test_email: Dict) -> Dict:
        """
        测试规则（用于前端预览）
        
        Args:
            rule: 规则数据
            test_email: 测试邮件数据
            
        Returns:
            dict: 测试结果
        """
        import json
        
        result = {
            'matched': False,
            'conditions': [],
            'score': 0
        }
        
        # 测试发件人
        if rule.get('sender_pattern'):
            sender = test_email.get('sender', '')
            pattern = rule.get('sender_pattern')
            match_type = rule.get('sender_match_type', 'contains')
            matched = RuleMatcher.match_sender(sender, pattern, match_type)
            
            result['conditions'].append({
                'type': 'sender',
                'pattern': pattern,
                'match_type': match_type,
                'value': sender,
                'matched': matched,
                'description': f"发件人 '{sender}' {'✅ 匹配' if matched else '❌ 不匹配'} 模式 '{pattern}' ({match_type})"
            })
        
        # 测试主题
        if rule.get('subject_keywords'):
            try:
                keywords = json.loads(rule['subject_keywords']) if isinstance(rule['subject_keywords'], str) else rule['subject_keywords']
                subject = test_email.get('subject', '')
                logic = rule.get('subject_logic', 'OR')
                matched = RuleMatcher.match_keywords(subject, keywords, logic)
                
                result['conditions'].append({
                    'type': 'subject',
                    'keywords': keywords,
                    'logic': logic,
                    'value': subject,
                    'matched': matched,
                    'description': f"主题 '{subject}' {'✅ 匹配' if matched else '❌ 不匹配'} 关键词 {keywords} ({logic})"
                })
            except Exception as e:
                logger.error(f"测试主题关键词失败: {e}")
        
        # 测试正文
        if rule.get('body_keywords'):
            try:
                keywords = json.loads(rule['body_keywords']) if isinstance(rule['body_keywords'], str) else rule['body_keywords']
                body = test_email.get('body', '')
                matched = RuleMatcher.match_keywords(body, keywords, 'OR')
                
                result['conditions'].append({
                    'type': 'body',
                    'keywords': keywords,
                    'value': body[:100] + '...' if len(body) > 100 else body,
                    'matched': matched,
                    'description': f"正文 {'✅ 包含' if matched else '❌ 不包含'} 关键词 {keywords}"
                })
            except Exception as e:
                logger.error(f"测试正文关键词失败: {e}")
        
        # 判断整体是否匹配
        result['matched'] = all(cond['matched'] for cond in result['conditions']) if result['conditions'] else False
        
        # 计算得分
        if result['matched']:
            result['score'] = RuleMatcher.calculate_rule_score(rule, test_email)
            result['target_category'] = rule.get('target_category')
            result['target_importance'] = rule.get('target_importance')
        
        return result


