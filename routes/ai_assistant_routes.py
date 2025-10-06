#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - AI助手路由
提供对话API和流式响应
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
import logging
import json
from typing import Dict, Generator

from services.auth_service import auth_service
# 使用新的V2服务（基于Function Call）
from services.ai_assistant_service_v2 import AIAssistantServiceV2

logger = logging.getLogger(__name__)

# 创建蓝图
assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/api/ai-assistant')

# 初始化AI助手服务V2（Function Call版本）
ai_assistant = AIAssistantServiceV2()
logger.info("AI助手服务V2已初始化（基于Function Call）")


@assistant_bp.route('/chat', methods=['POST'])
@auth_service.require_login
def chat():
    """
    AI助手对话API
    
    请求体:
    {
        "message": "用户消息",
        "context": {
            "selected_email_ids": [123, 456],
            "conversation_history": [...]
        }
    }
    
    返回:
    {
        "success": true,
        "response": "AI回复",
        "emails": [...],
        "intent": "意图类型",
        "actions": [...],
        "statistics": {...}  // 可选
    }
    """
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数：message'
            }), 400
        
        message = data['message']
        context = data.get('context', {})
        
        logger.info(f"AI助手收到消息: 用户={user['username']}, 消息={message}")
        
        # 处理消息
        result = ai_assistant.process_message(user['id'], message, context)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"AI助手对话处理失败: {e}")
        return jsonify({
            'success': False,
            'response': '抱歉，处理您的请求时出现了错误。',
            'message': str(e)
        }), 500


@assistant_bp.route('/chat/stream', methods=['POST'])
@auth_service.require_login
def chat_stream():
    """
    流式对话API (Server-Sent Events)
    
    用于实时显示AI思考和响应过程
    """
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数：message'
            }), 400
        
        message = data['message']
        context = data.get('context', {})
        
        def generate() -> Generator[str, None, None]:
            """生成流式响应"""
            try:
                # 1. 发送思考状态
                yield f"data: {json.dumps({'type': 'status', 'message': '正在分析您的需求...', 'icon': 'fa-brain'})}\n\n"
                
                # 2. 处理消息（这里使用同步处理，未来可改为真正的流式）
                result = ai_assistant.process_message(user['id'], message, context)
                
                # 3. 发送搜索状态（如果是搜索类请求）
                if result.get('intent') == 'search_emails':
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在搜索相关邮件...', 'icon': 'fa-search'})}\n\n"
                
                # 4. 逐字发送响应文本（模拟打字效果）
                response_text = result.get('response', '')
                for i, char in enumerate(response_text):
                    yield f"data: {json.dumps({'type': 'text', 'content': char})}\n\n"
                    # 可以添加小延迟使效果更真实
                
                # 5. 发送完整响应数据
                yield f"data: {json.dumps({'type': 'complete', 'data': result})}\n\n"
                
                # 6. 结束标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"流式响应生成失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"流式对话处理失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@assistant_bp.route('/quick-commands', methods=['GET'])
@auth_service.require_login
def get_quick_commands():
    """
    获取快捷指令列表
    
    返回常用的预定义指令，方便用户快速操作
    """
    commands = [
        {
            'id': 'today_emails',
            'text': '今天的邮件',
            'icon': 'fa-calendar-day',
            'color': 'primary'
        },
        {
            'id': 'important_emails',
            'text': '重要邮件',
            'icon': 'fa-star',
            'color': 'danger'
        },
        {
            'id': 'week_stats',
            'text': '本周统计',
            'icon': 'fa-chart-bar',
            'color': 'success'
        },
        {
            'id': 'recent_3days',
            'text': '近三天邮件',
            'icon': 'fa-clock',
            'color': 'info'
        },
        {
            'id': 'work_emails',
            'text': '工作邮件',
            'icon': 'fa-briefcase',
            'color': 'secondary'
        }
    ]
    
    return jsonify({
        'success': True,
        'commands': commands
    })


@assistant_bp.route('/conversation/history', methods=['GET'])
@auth_service.require_login
def get_conversation_history():
    """
    获取对话历史
    
    查询参数:
    - limit: 返回最近N条记录，默认20
    """
    try:
        user = auth_service.get_current_user()
        limit = request.args.get('limit', 20, type=int)
        
        # TODO: 从数据库或缓存中获取对话历史
        # 目前返回空列表，后续可实现持久化
        
        return jsonify({
            'success': True,
            'history': []
        })
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@assistant_bp.route('/conversation/clear', methods=['POST'])
@auth_service.require_login
def clear_conversation():
    """清空对话历史"""
    try:
        user = auth_service.get_current_user()
        
        # TODO: 清空数据库或缓存中的对话历史
        
        return jsonify({
            'success': True,
            'message': '对话历史已清空'
        })
        
    except Exception as e:
        logger.error(f"清空对话历史失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def register_ai_assistant_routes(app):
    """注册AI助手路由到Flask应用"""
    app.register_blueprint(assistant_bp)
    logger.info("AI助手路由已注册")


