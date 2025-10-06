#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Function Call完整流程
诊断AI助手对话问题
"""

import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ai_assistant_service_v2 import AIAssistantServiceV2
from services.ai_client import AIClient
from services.email_tools import EMAIL_TOOLS
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_function_call():
    """测试基础Function Call流程"""
    print("\n" + "=" * 80)
    print("测试1: 基础Function Call流程")
    print("=" * 80)
    
    ai_client = AIClient()
    
    # 构建测试消息
    messages = [
        {
            "role": "system",
            "content": "你是一个邮件助手，帮助用户查询邮件。如果用户问今天的邮件，请调用search_emails函数。"
        },
        {
            "role": "user",
            "content": "帮我看下今天的邮件"
        }
    ]
    
    print("\n📤 第一次AI调用（决策阶段）...")
    response1 = ai_client.chat_with_tools(messages, EMAIL_TOOLS, temperature=0.3)
    
    print(f"\n✅ 第一次响应:")
    print(f"  - content: {response1.get('content', '(空)')}")
    print(f"  - tool_calls数量: {len(response1.get('tool_calls', []))}")
    print(f"  - finish_reason: {response1.get('finish_reason', '')}")
    
    if response1.get('tool_calls'):
        print(f"\n🔧 工具调用:")
        for tool_call in response1['tool_calls']:
            print(f"  - 工具: {tool_call['function']['name']}")
            print(f"  - 参数: {tool_call['function']['arguments']}")
    
    # 模拟工具执行结果
    tool_result = {
        "success": True,
        "count": 5,
        "emails": [
            {
                "id": 1,
                "subject": "测试邮件1",
                "sender": "test@example.com",
                "date": "2025-10-05 10:00:00"
            }
        ]
    }
    
    # 添加工具结果到消息
    if response1.get('tool_calls'):
        tool_call = response1['tool_calls'][0]
        messages.append({
            "role": "assistant",
            "content": response1.get('content', ''),
            "tool_calls": response1['tool_calls']
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call['id'],
            "name": tool_call['function']['name'],
            "content": json.dumps(tool_result, ensure_ascii=False)
        })
        
        print(f"\n📤 第二次AI调用（生成回复阶段）...")
        response2 = ai_client.chat_with_tools(messages, EMAIL_TOOLS, temperature=0.7)
        
        print(f"\n✅ 第二次响应:")
        print(f"  - content: {response2.get('content', '(空)')}")
        print(f"  - content长度: {len(response2.get('content', ''))}")
        print(f"  - tool_calls数量: {len(response2.get('tool_calls', []))}")
        print(f"  - finish_reason: {response2.get('finish_reason', '')}")
        
        if response2.get('content'):
            print(f"\n💬 最终回复内容:")
            print(f"  {response2['content']}")
        else:
            print(f"\n⚠️  警告: 第二次调用没有返回content!")


def test_assistant_service():
    """测试完整的Assistant Service"""
    print("\n" + "=" * 80)
    print("测试2: 完整的Assistant Service流程")
    print("=" * 80)
    
    ai_assistant = AIAssistantServiceV2()
    
    test_cases = [
        "帮我看下今天的邮件",
        "近三天邮件",
        "本周有多少封工作邮件"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试用例 {i}: {message}")
        print(f"{'=' * 60}")
        
        result = ai_assistant.process_message(user_id=1, message=message)
        
        print(f"\n✅ 处理结果:")
        print(f"  - success: {result.get('success')}")
        print(f"  - response: {result.get('response', '(空)')}")
        print(f"  - response长度: {len(result.get('response', ''))}")
        print(f"  - 邮件数量: {len(result.get('emails', []))}")
        print(f"  - 工具调用数: {len(result.get('tool_calls', []))}")
        
        if result.get('tool_calls'):
            print(f"\n🔧 工具调用记录:")
            for tool_call in result['tool_calls']:
                print(f"  - {tool_call['function']['name']}: {tool_call['function']['arguments']}")
        
        if not result.get('response') or result['response'] == '':
            print(f"\n❌ 错误: 没有生成最终回复!")
        
        # 检查response是否只是工具调用格式
        if result.get('response') and 'search_emails' in result['response']:
            print(f"\n⚠️  警告: response似乎只包含工具调用信息，而不是自然语言回复")
            print(f"  实际内容: {result['response']}")


def test_messages_format():
    """测试消息格式"""
    print("\n" + "=" * 80)
    print("测试3: 检查消息格式")
    print("=" * 80)
    
    # 模拟完整的消息序列
    messages = [
        {
            "role": "system",
            "content": "你是邮件助手"
        },
        {
            "role": "user",
            "content": "今天的邮件"
        },
        {
            "role": "assistant",
            "content": "",  # 可能是空的
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "search_emails",
                        "arguments": '{"time_range": "today"}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "name": "search_emails",
            "content": '{"success": true, "count": 5, "emails": [...]}'
        }
    ]
    
    print("\n📋 消息序列:")
    for i, msg in enumerate(messages, 1):
        print(f"\n消息 {i}:")
        print(f"  role: {msg['role']}")
        if 'content' in msg:
            content_preview = msg['content'][:50] if msg['content'] else "(空)"
            print(f"  content: {content_preview}")
        if 'tool_calls' in msg:
            print(f"  tool_calls: {len(msg['tool_calls'])} 个")
        if 'tool_call_id' in msg:
            print(f"  tool_call_id: {msg['tool_call_id']}")
    
    print("\n✅ 消息格式检查完成")


if __name__ == "__main__":
    print("\n" + "🔍 " * 20)
    print("AI邮件助手 Function Call 诊断工具")
    print("🔍 " * 20)
    
    try:
        # 运行测试
        test_basic_function_call()
        test_messages_format()
        test_assistant_service()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

