#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件分类系统 - API路由
提供分类规则管理的RESTful API
"""

from flask import Blueprint, request, jsonify
import logging

from services.classification_service import ClassificationService
from services.auth_service import auth_service
from services.intelligence.rule_suggestion_service import RuleSuggestionService

logger = logging.getLogger(__name__)

# 创建Blueprint
classification_bp = Blueprint('classification', __name__, url_prefix='/api/classification')

# 初始化服务
classification_service = ClassificationService()
suggestion_service = RuleSuggestionService()

# ========== 规则管理API ==========

@classification_bp.route('/rules', methods=['GET'])
@auth_service.require_login
def get_rules():
    """获取用户的分类规则"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        rules = classification_service.get_user_rules(user_id, active_only)
        
        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        })
        
    except Exception as e:
        logger.error(f"获取规则列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules', methods=['POST'])
@auth_service.require_login
def create_rule():
    """创建分类规则"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        rule_data = request.json
        
        # 验证必需字段
        if not rule_data.get('rule_name'):
            return jsonify({
                'success': False,
                'error': '规则名称不能为空'
            }), 400
        
        if not rule_data.get('target_category'):
            return jsonify({
                'success': False,
                'error': '目标分类不能为空'
            }), 400
        
        # 创建规则
        result = classification_service.create_rule(user_id, rule_data)
        
        return jsonify({
            'success': True,
            'rule': result,
            'message': '规则创建成功'
        })
        
    except Exception as e:
        logger.error(f"创建规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules/<int:rule_id>', methods=['GET'])
@auth_service.require_login
def get_rule(rule_id):
    """获取单个规则详情"""
    try:
        rule = classification_service.get_rule_by_id(rule_id)
        
        if not rule:
            return jsonify({
                'success': False,
                'error': '规则不存在'
            }), 404
        
        # 验证权限
        user = auth_service.get_current_user()
        user_id = user['id']
        if rule['user_id'] != user_id:
            return jsonify({
                'success': False,
                'error': '无权访问此规则'
            }), 403
        
        return jsonify({
            'success': True,
            'rule': rule
        })
        
    except Exception as e:
        logger.error(f"获取规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@auth_service.require_login
def update_rule(rule_id):
    """更新规则"""
    try:
        # 验证权限
        rule = classification_service.get_rule_by_id(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '规则不存在'
            }), 404
        
        user = auth_service.get_current_user()
        user_id = user['id']
        if rule['user_id'] != user_id:
            return jsonify({
                'success': False,
                'error': '无权修改此规则'
            }), 403
        
        # 更新规则
        rule_data = request.json
        success = classification_service.update_rule(rule_id, rule_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': '规则更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '规则更新失败'
            }), 500
            
    except Exception as e:
        logger.error(f"更新规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@auth_service.require_login
def delete_rule(rule_id):
    """删除规则"""
    try:
        # 验证权限
        rule = classification_service.get_rule_by_id(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '规则不存在'
            }), 404
        
        user = auth_service.get_current_user()
        user_id = user['id']
        if rule['user_id'] != user_id:
            return jsonify({
                'success': False,
                'error': '无权删除此规则'
            }), 403
        
        # 删除规则
        success = classification_service.delete_rule(rule_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '规则删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '规则删除失败'
            }), 500
            
    except Exception as e:
        logger.error(f"删除规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules/test', methods=['POST'])
@auth_service.require_login
def test_rule():
    """测试规则"""
    try:
        data = request.json
        rule_data = data.get('rule')
        test_email = data.get('test_email')
        
        if not rule_data or not test_email:
            return jsonify({
                'success': False,
                'error': '缺少规则或测试邮件数据'
            }), 400
        
        result = classification_service.test_rule(rule_data, test_email)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"测试规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/rules/<int:rule_id>/apply', methods=['POST'])
@auth_service.require_login
def apply_rule_to_existing(rule_id):
    """将规则应用到现有邮件"""
    try:
        # 验证权限
        rule = classification_service.get_rule_by_id(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': '规则不存在'
            }), 404
        
        user = auth_service.get_current_user()
        user_id = user['id']
        if rule['user_id'] != user_id:
            return jsonify({
                'success': False,
                'error': '无权使用此规则'
            }), 403
        
        # 应用规则
        result = classification_service.apply_rules_to_existing_emails(user_id, rule_id)
        
        return jsonify({
            'success': True,
            'result': result,
            'message': f"已重新分类 {result['success_count']} 封邮件"
        })
        
    except Exception as e:
        logger.error(f"应用规则失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 批量操作API ==========

@classification_bp.route('/reclassify', methods=['POST'])
@auth_service.require_login
def reclassify_emails():
    """批量重新分类"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        email_ids = request.json.get('email_ids', [])
        
        if not email_ids:
            return jsonify({
                'success': False,
                'error': '邮件ID列表不能为空'
            }), 400
        
        result = classification_service.batch_reclassify(user_id, email_ids)
        
        return jsonify({
            'success': True,
            'result': result,
            'message': f"批量重分类完成: 成功 {result['success_count']}, 失败 {result['fail_count']}"
        })
        
    except Exception as e:
        logger.error(f"批量重分类失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 智能建议API ==========

@classification_bp.route('/suggestions', methods=['GET'])
@auth_service.require_login
def get_suggestions():
    """获取用户的智能建议列表"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 从数据库获取已保存的建议
        suggestions = suggestion_service.get_user_suggestions(user_id)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        })
        
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/suggestions/generate', methods=['POST'])
@auth_service.require_login
def generate_suggestions():
    """分析用户行为并生成新的智能建议"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 分析用户行为
        suggestions = suggestion_service.analyze_user_behavior(user_id)
        
        # 保存到数据库
        saved_count = suggestion_service.save_suggestions_to_db(suggestions)
        
        return jsonify({
            'success': True,
            'message': f'成功生成 {len(suggestions)} 条建议，保存了 {saved_count} 条新建议',
            'suggestions': suggestions,
            'count': len(suggestions),
            'saved_count': saved_count
        })
        
    except Exception as e:
        logger.error(f"生成建议失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/suggestions/<int:suggestion_id>/apply', methods=['POST'])
@auth_service.require_login
def apply_suggestion(suggestion_id):
    """应用建议，自动创建规则"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 应用建议
        rule_id = suggestion_service.apply_suggestion(suggestion_id, user_id)
        
        if rule_id:
            return jsonify({
                'success': True,
                'message': '建议已应用，规则创建成功',
                'rule_id': rule_id
            })
        else:
            return jsonify({
                'success': False,
                'error': '应用建议失败'
            }), 400
        
    except Exception as e:
        logger.error(f"应用建议失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@classification_bp.route('/suggestions/<int:suggestion_id>', methods=['DELETE'])
@auth_service.require_login
def ignore_suggestion(suggestion_id):
    """忽略建议"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        from models.database import Database
        db = Database()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE classification_suggestions
                SET is_applied = -1
                WHERE id = ? AND user_id = ?
            ''', (suggestion_id, user_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '建议已忽略'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '建议不存在'
                }), 404
        
    except Exception as e:
        logger.error(f"忽略建议失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 统计分析API ==========

@classification_bp.route('/stats', methods=['GET'])
@auth_service.require_login
def get_classification_stats():
    """获取分类统计"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 获取用户规则统计
        rules = classification_service.get_user_rules(user_id, active_only=False)
        active_rules = [r for r in rules if r.get('is_active')]
        
        # 获取分类分布
        from models.database import Database
        db = Database()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT category, COUNT(*) as count, classification_method
                FROM emails 
                WHERE user_id = ? AND (deleted IS NULL OR deleted = 0)
                GROUP BY category, classification_method
            ''', (user_id,))
            
            category_stats = []
            for row in cursor.fetchall():
                category_stats.append({
                    'category': row['category'],
                    'count': row['count'],
                    'method': row['classification_method']
                })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_rules': len(rules),
                'active_rules': len(active_rules),
                'category_distribution': category_stats
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_classification_routes(app):
    """注册分类路由到Flask应用"""
    app.register_blueprint(classification_bp)
    logger.info("✅ 邮件分类路由已注册")

