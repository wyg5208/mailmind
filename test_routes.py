#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试路由是否正确加载
"""

from app import app

print("=" * 60)
print("检查 API 路由")
print("=" * 60)

# 获取所有路由
routes = []
for rule in app.url_map.iter_rules():
    if '/api/user/import' in rule.rule:
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(rule.methods),
            'rule': rule.rule
        })

if routes:
    print(f"\n✅ 找到 {len(routes)} 个导入相关路由:\n")
    for route in routes:
        print(f"  路径: {route['rule']}")
        print(f"  方法: {route['methods']}")
        print(f"  端点: {route['endpoint']}")
        print()
else:
    print("\n❌ 未找到导入相关路由！")
    print("\n所有 /api/user/ 路由:")
    for rule in app.url_map.iter_rules():
        if '/api/user/' in rule.rule:
            print(f"  {rule.rule} - {','.join(rule.methods)}")

print("=" * 60)


