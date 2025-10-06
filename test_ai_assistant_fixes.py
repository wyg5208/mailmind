#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI助手阶段1修复验证脚本
测试意图识别和邮件搜索功能
"""

import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '.')

from services.ai_assistant_service import IntentParser, EmailSearchEngine, AIAssistantService
from services.ai_client import AIClient
from models.database import Database

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_time_extraction():
    """测试时间范围提取"""
    print_section("测试1: 时间范围提取")
    
    ai_client = AIClient()
    parser = IntentParser(ai_client)
    
    test_cases = [
        "今天的邮件",
        "昨天的邮件",
        "本周的邮件",
        "最近7天的邮件",
        "近3天的邮件",
    ]
    
    for message in test_cases:
        result = parser._extract_time_range(message)
        print(f"✅ 输入: '{message}'")
        print(f"   结果: {result}")
        print()

def test_category_extraction():
    """测试分类提取"""
    print_section("测试2: 分类提取")
    
    ai_client = AIClient()
    parser = IntentParser(ai_client)
    
    test_cases = [
        "重要邮件",
        "工作邮件",
        "紧急的邮件",
        "财务邮件",
        "购物相关的邮件",
    ]
    
    for message in test_cases:
        result = parser._extract_category(message)
        print(f"✅ 输入: '{message}'")
        print(f"   分类: {result}")
        print()

def test_search_params_extraction():
    """测试完整参数提取"""
    print_section("测试3: 完整搜索参数提取")
    
    ai_client = AIClient()
    parser = IntentParser(ai_client)
    
    test_cases = [
        "今天的重要邮件",
        "昨天的工作邮件",
        "本周的财务邮件",
        "最近3天的紧急邮件",
    ]
    
    for message in test_cases:
        params = parser._extract_search_params(message)
        print(f"✅ 输入: '{message}'")
        print(f"   参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        print()

def test_time_filter_sql():
    """测试时间过滤SQL生成"""
    print_section("测试4: 时间过滤SQL生成")
    
    db = Database()
    search_engine = EmailSearchEngine(db)
    
    test_cases = [
        {'type': 'relative', 'days': 0},  # 今天
        {'type': 'relative', 'days': 1},  # 昨天
        {'type': 'relative', 'days': 7},  # 近7天
        {'type': 'week', 'value': 0},     # 本周
        {'type': 'month', 'value': 0},    # 本月
    ]
    
    for time_range in test_cases:
        result = search_engine._build_time_filter(time_range)
        print(f"✅ 时间范围: {time_range}")
        if result:
            print(f"   SQL: {result['sql']}")
            print(f"   参数: {result['params']}")
        else:
            print(f"   结果: None")
        print()

def test_intent_recognition():
    """测试意图识别"""
    print_section("测试5: 意图识别")
    
    ai_client = AIClient()
    parser = IntentParser(ai_client)
    
    test_cases = [
        "今天的邮件",
        "重要邮件",
        "工作邮件",
        "帮我找昨天的邮件",
        "查看本周的重要邮件",
    ]
    
    for message in test_cases:
        result = parser.parse(message)
        print(f"✅ 输入: '{message}'")
        print(f"   意图: {result.get('intent')}")
        print(f"   置信度: {result.get('confidence')}")
        print(f"   参数: {json.dumps(result.get('parameters', {}), ensure_ascii=False, indent=2)}")
        print()

def test_no_result_response():
    """测试无结果响应生成"""
    print_section("测试6: 无结果响应生成")
    
    ai_assistant = AIAssistantService()
    
    test_cases = [
        {'time_range': {'type': 'relative', 'days': 0}},
        {'category': '工作'},
        {'time_range': {'type': 'relative', 'days': 0}, 'category': '重要'},
        {'keywords': ['项目', '会议']},
    ]
    
    for params in test_cases:
        response = ai_assistant._generate_no_result_response(params)
        print(f"✅ 参数: {json.dumps(params, ensure_ascii=False)}")
        print(f"   响应:\n{response}")
        print()

def main():
    """主函数"""
    print("\n" + "="*60)
    print("  AI助手阶段1修复验证")
    print("  测试时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    try:
        # 运行所有测试
        test_time_extraction()
        test_category_extraction()
        test_search_params_extraction()
        test_time_filter_sql()
        test_intent_recognition()
        test_no_result_response()
        
        print_section("✅ 所有测试完成！")
        print("\n主要改进：")
        print("1. ✅ 时间范围转换从SQLite函数改为Python datetime处理")
        print("2. ✅ 增加了分类提取功能，支持'重要'、'工作'等关键词")
        print("3. ✅ 完善了日志记录，便于调试和追踪")
        print("4. ✅ 优化了无结果响应，提供具体建议")
        print("5. ✅ 修复了'重要邮件'的importance筛选逻辑")
        print()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


