#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件分类系统 - 分类服务核心
提供完整的邮件智能分类功能
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from models.database import Database
from services.ai_client import AIClient
from services.rule_matcher import RuleMatcher

logger = logging.getLogger(__name__)

class ClassificationService:
    """邮件分类服务"""
    
    def __init__(self):
        self.db = Database()
        self.ai_client = AIClient()
        self.rule_matcher = RuleMatcher()
        
        # 扩展分类定义（12个类别）
        self.categories = {
            'work': '工作邮件',
            'finance': '财务邮件',
            'social': '社交邮件',
            'shopping': '购物邮件',
            'news': '资讯邮件',
            'education': '教育学习',
            'travel': '旅行出行',
            'health': '健康医疗',
            'system': '系统通知',
            'advertising': '广告邮件',  # 新增：正规商业推广
            'spam': '垃圾邮件',        # 显式：骚扰和诈骗信息
            'general': '其他邮件'
        }
        
        # 扩展关键词库（现有逻辑的增强版）
        self.category_keywords = {
            'work': ['工作', 'work', '项目', 'project', '任务', 'task', '会议', 'meeting', '报告', 'report'],
            'finance': ['账单', 'bill', '付款', 'payment', '银行', 'bank', '财务', 'finance', '发票', 'invoice'],
            'social': ['朋友', 'friend', '社交', 'social', '聚会', 'party', '生日', 'birthday'],
            'shopping': ['订单', 'order', '购买', 'purchase', '商品', 'product', '快递', 'delivery', '物流', 'shipping'],
            'news': ['新闻', 'news', '资讯', 'information', '更新', 'update', '订阅', 'newsletter'],
            'education': ['课程', 'course', '培训', 'training', '学习', 'study', '教育', 'education', '考试', 'exam'],
            'travel': ['机票', 'flight', '酒店', 'hotel', '旅行', 'travel', '行程', 'itinerary', '签证', 'visa'],
            'health': ['医院', 'hospital', '体检', 'checkup', '健康', 'health', '医疗', 'medical', '药品', 'medicine'],
            'system': ['验证码', 'code', '密码', 'password', '账号', 'account', '注册', 'register', '通知', 'notification'],
            'advertising': ['广告', 'ad', '推广', 'promotion', '营销', 'marketing', '促销', '优惠', 'discount', '折扣', 'sale', '特价', '限时', '秒杀', '活动', 'campaign', 'offer', 'deal'],
            'spam': ['中奖', 'prize', '恭喜', 'congratulations', '免费领取', 'free gift', '点击领取', 'click here', '立即查看', 'view now', '紧急', 'urgent', '重要通知', '账号异常', '验证身份', 'verify account', 'suspended', 'unusual activity']
        }
    
    # ========== 规则管理 ==========
    
    def create_rule(self, user_id: int, rule_data: dict) -> dict:
        """创建分类规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 准备数据
                subject_keywords = rule_data.get('subject_keywords')
                if isinstance(subject_keywords, list):
                    subject_keywords = json.dumps(subject_keywords, ensure_ascii=False)
                
                body_keywords = rule_data.get('body_keywords')
                if isinstance(body_keywords, list):
                    body_keywords = json.dumps(body_keywords, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT INTO classification_rules 
                    (user_id, rule_name, sender_pattern, sender_match_type, 
                     subject_keywords, subject_logic, body_keywords,
                     target_category, target_importance, priority, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    rule_data.get('rule_name'),
                    rule_data.get('sender_pattern'),
                    rule_data.get('sender_match_type', 'contains'),
                    subject_keywords,
                    rule_data.get('subject_logic', 'OR'),
                    body_keywords,
                    rule_data.get('target_category'),
                    rule_data.get('target_importance', 1),
                    rule_data.get('priority', 5),
                    rule_data.get('is_active', True)
                ))
                
                conn.commit()
                rule_id = cursor.lastrowid
                
                logger.info(f"用户 {user_id} 创建规则: {rule_data.get('rule_name')} (ID: {rule_id})")
                
                # 返回创建的规则
                return self.get_rule_by_id(rule_id)
                
        except Exception as e:
            logger.error(f"创建规则失败: {e}")
            raise
    
    def update_rule(self, rule_id: int, rule_data: dict) -> bool:
        """更新规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 准备数据
                subject_keywords = rule_data.get('subject_keywords')
                if isinstance(subject_keywords, list):
                    subject_keywords = json.dumps(subject_keywords, ensure_ascii=False)
                
                body_keywords = rule_data.get('body_keywords')
                if isinstance(body_keywords, list):
                    body_keywords = json.dumps(body_keywords, ensure_ascii=False)
                
                cursor.execute('''
                    UPDATE classification_rules 
                    SET rule_name = ?, sender_pattern = ?, sender_match_type = ?,
                        subject_keywords = ?, subject_logic = ?, body_keywords = ?,
                        target_category = ?, target_importance = ?, priority = ?,
                        is_active = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    rule_data.get('rule_name'),
                    rule_data.get('sender_pattern'),
                    rule_data.get('sender_match_type', 'contains'),
                    subject_keywords,
                    rule_data.get('subject_logic', 'OR'),
                    body_keywords,
                    rule_data.get('target_category'),
                    rule_data.get('target_importance', 1),
                    rule_data.get('priority', 5),
                    rule_data.get('is_active', True),
                    datetime.now().isoformat(),
                    rule_id
                ))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"规则更新成功: ID={rule_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            return False
    
    def delete_rule(self, rule_id: int) -> bool:
        """删除规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM classification_rules WHERE id = ?', (rule_id,))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"规则删除成功: ID={rule_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"删除规则失败: {e}")
            return False
    
    def get_user_rules(self, user_id: int, active_only: bool = True) -> List[dict]:
        """获取用户的所有规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if active_only:
                    cursor.execute('''
                        SELECT * FROM classification_rules 
                        WHERE user_id = ? AND is_active = 1
                        ORDER BY priority DESC, created_at DESC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM classification_rules 
                        WHERE user_id = ?
                        ORDER BY priority DESC, created_at DESC
                    ''', (user_id,))
                
                rules = []
                for row in cursor.fetchall():
                    rules.append(dict(row))
                
                return rules
                
        except Exception as e:
            logger.error(f"获取用户规则失败: {e}")
            return []
    
    def get_rule_by_id(self, rule_id: int) -> Optional[dict]:
        """根据ID获取规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM classification_rules WHERE id = ?', (rule_id,))
                row = cursor.fetchone()
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"获取规则失败: {e}")
            return None
    
    def test_rule(self, rule_data: dict, test_email: dict) -> dict:
        """测试规则（预览效果）"""
        return self.rule_matcher.test_rule(rule_data, test_email)
    
    # ========== 规则匹配 ==========
    
    def find_matching_rule(self, email: dict, user_id: int) -> Optional[dict]:
        """为邮件找到匹配的规则（按优先级）"""
        rules = self.get_user_rules(user_id, active_only=True)
        
        if not rules:
            return None
        
        # 找出所有匹配的规则
        matched_rules = []
        for rule in rules:
            if self.rule_matcher.match_rule(rule, email):
                score = self.rule_matcher.calculate_rule_score(rule, email)
                matched_rules.append((rule, score))
        
        if not matched_rules:
            return None
        
        # 按得分排序，返回最高分的规则
        matched_rules.sort(key=lambda x: x[1], reverse=True)
        best_rule = matched_rules[0][0]
        
        logger.info(f"找到最佳匹配规则: {best_rule['rule_name']} (得分: {matched_rules[0][1]})")
        
        return best_rule
    
    # ========== 分类执行 ==========
    
    def classify_email(self, email: dict, user_id: int) -> Tuple[str, int, str]:
        """
        邮件分类主函数（四层策略）
        
        Returns:
            Tuple[str, int, str]: (category, importance, method)
        """
        
        # Layer 1: 自定义规则（最高优先级）
        rule = self.find_matching_rule(email, user_id)
        if rule:
            self._update_rule_stats(rule['id'])
            return (
                rule['target_category'],
                rule['target_importance'],
                'rule'
            )
        
        # Layer 2: AI分析（智能分类，暂时跳过以加快开发）
        # if self._should_use_ai(email):
        #     ai_result = self.classify_with_ai(email)
        #     if ai_result and ai_result.get('confidence', 0) > 0.7:
        #         return (
        #             ai_result['category'],
        #             ai_result['importance'],
        #             'ai'
        #         )
        
        # Layer 3: 关键词规则（现有逻辑）
        category, importance = self._classify_with_keywords(email)
        if category != 'general':
            return (category, importance, 'keyword')
        
        # Layer 4: 默认分类
        return ('general', 1, 'default')
    
    def _update_rule_stats(self, rule_id: int):
        """更新规则统计信息"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE classification_rules 
                    SET match_count = match_count + 1,
                        last_matched_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), rule_id))
                conn.commit()
        except Exception as e:
            logger.error(f"更新规则统计失败: {e}")
    
    def _classify_with_keywords(self, email: dict) -> Tuple[str, int]:
        """关键词分类（现有逻辑的增强版）"""
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        body = email.get('body', '')[:500].lower()  # 只检查前500字符
        
        text_to_check = f"{subject} {sender} {body}"
        
        # 重要性关键词
        high_importance_keywords = [
            'urgent', '紧急', '重要', 'important', '急', '立即', 'asap',
            '截止', 'deadline', '会议', 'meeting', '面试', 'interview'
        ]
        
        medium_importance_keywords = [
            '通知', 'notice', '公告', 'announcement', '更新', 'update',
            '邀请', 'invitation', '确认', 'confirmation'
        ]
        
        # 计算重要性
        importance = 1  # 默认普通
        if any(keyword in text_to_check for keyword in high_importance_keywords):
            importance = 3  # 高重要性
        elif any(keyword in text_to_check for keyword in medium_importance_keywords):
            importance = 2  # 中等重要性
        
        # 确定分类（按优先级检查）
        for category, keywords in self.category_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                return (category, importance)
        
        return ('general', importance)
    
    # ========== 批量操作 ==========
    
    def batch_reclassify(self, user_id: int, email_ids: List[int]) -> dict:
        """批量重新分类"""
        success_count = 0
        fail_count = 0
        results = []
        
        for email_id in email_ids:
            try:
                # 获取邮件
                email = self.db.get_email_by_id(email_id)
                if not email or email.get('user_id') != user_id:
                    fail_count += 1
                    continue
                
                # 重新分类
                category, importance, method = self.classify_email(email, user_id)
                
                # 更新数据库
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE emails 
                        SET category = ?, importance = ?, 
                            classification_method = ?, updated_at = ?
                        WHERE id = ?
                    ''', (category, importance, method, datetime.now().isoformat(), email_id))
                    conn.commit()
                
                success_count += 1
                results.append({
                    'email_id': email_id,
                    'category': category,
                    'importance': importance,
                    'method': method
                })
                
            except Exception as e:
                logger.error(f"重新分类邮件 {email_id} 失败: {e}")
                fail_count += 1
        
        logger.info(f"批量重分类完成: 成功 {success_count}, 失败 {fail_count}")
        
        return {
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results
        }
    
    def apply_rules_to_existing_emails(self, user_id: int, rule_id: int = None):
        """将规则应用到现有邮件"""
        try:
            # 获取用户所有邮件
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM emails 
                    WHERE user_id = ? AND (deleted IS NULL OR deleted = 0)
                ''', (user_id,))
                
                email_ids = [row['id'] for row in cursor.fetchall()]
            
            # 批量重新分类
            return self.batch_reclassify(user_id, email_ids)
            
        except Exception as e:
            logger.error(f"应用规则到现有邮件失败: {e}")
            return {'success_count': 0, 'fail_count': 0, 'results': []}
    
    # ========== 学习与建议（预留） ==========
    
    def record_manual_change(self, user_id: int, email_id: int, 
                            old_category: str, new_category: str,
                            old_importance: int, new_importance: int):
        """记录用户手动修改"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_classification_history 
                    (user_id, email_id, original_category, new_category,
                     original_importance, new_importance, action_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, email_id, old_category, new_category,
                      old_importance, new_importance, 'manual_change'))
                conn.commit()
                
                logger.info(f"记录用户手动分类: {old_category} -> {new_category}")
                
        except Exception as e:
            logger.error(f"记录手动分类失败: {e}")
    
    def analyze_user_behavior(self, user_id: int) -> List[dict]:
        """分析用户行为，生成建议（后续实现）"""
        # TODO: 分析用户历史操作，生成规则建议
        return []


