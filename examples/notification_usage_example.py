#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知系统使用示例
展示如何在其他模块中使用通知功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database

# 初始化数据库
db = Database()

# ============================================================
# 示例1: 发送信息通知
# ============================================================
def send_info_notification(user_id: int):
    """发送一条信息通知"""
    db.save_notification(
        user_id=user_id,
        title="系统提示",
        message="您的账户设置已更新",
        notification_type='info'
    )
    print("✅ 信息通知已发送")

# ============================================================
# 示例2: 发送成功通知
# ============================================================
def send_success_notification(user_id: int):
    """发送一条成功通知"""
    db.save_notification(
        user_id=user_id,
        title="操作成功",
        message="您的邮箱账户已成功添加",
        notification_type='success'
    )
    print("✅ 成功通知已发送")

# ============================================================
# 示例3: 发送警告通知
# ============================================================
def send_warning_notification(user_id: int):
    """发送一条警告通知"""
    db.save_notification(
        user_id=user_id,
        title="存储空间警告",
        message="您的邮件附件存储空间已使用80%，请及时清理",
        notification_type='warning'
    )
    print("⚠️  警告通知已发送")

# ============================================================
# 示例4: 发送错误通知
# ============================================================
def send_error_notification(user_id: int):
    """发送一条错误通知"""
    db.save_notification(
        user_id=user_id,
        title="邮件发送失败",
        message="由于网络问题，邮件发送失败，请稍后重试",
        notification_type='error'
    )
    print("❌ 错误通知已发送")

# ============================================================
# 示例5: 邮件收取场景 - 没有新邮件
# ============================================================
def notify_no_new_emails(user_id: int):
    """通知用户没有新邮件"""
    db.save_notification(
        user_id=user_id,
        title="邮件收取完成",
        message="本次收取没有找到新邮件。所有邮箱均已检查完毕，暂无新邮件到达。",
        notification_type='info'
    )
    print("📭 无新邮件通知已发送")

# ============================================================
# 示例6: 邮件收取场景 - 全部重复
# ============================================================
def notify_all_duplicates(user_id: int, found_count: int):
    """通知用户找到的邮件全部重复"""
    db.save_notification(
        user_id=user_id,
        title="邮件收取完成",
        message=f"找到 {found_count} 封邮件，但全部为重复邮件，已自动过滤。系统已为您去重，避免重复查看。",
        notification_type='info'
    )
    print(f"🔄 重复邮件通知已发送 (发现{found_count}封重复)")

# ============================================================
# 示例7: 邮件收取场景 - 成功收取
# ============================================================
def notify_emails_received(user_id: int, new_count: int, total_found: int):
    """通知用户成功收取新邮件"""
    db.save_notification(
        user_id=user_id,
        title="新邮件到达",
        message=f"成功收取并处理了 {new_count} 封新邮件，已生成邮件简报。去重前共发现 {total_found} 封邮件。",
        notification_type='success'
    )
    print(f"📬 新邮件通知已发送 (新邮件{new_count}封，总共发现{total_found}封)")

# ============================================================
# 示例8: 获取未读通知数量
# ============================================================
def check_unread_count(user_id: int):
    """检查用户未读通知数量"""
    count = db.get_unread_notification_count(user_id)
    print(f"🔔 用户 {user_id} 有 {count} 条未读通知")
    return count

# ============================================================
# 示例9: 获取通知列表
# ============================================================
def get_latest_notifications(user_id: int, limit: int = 5):
    """获取用户最新的通知"""
    notifications, total = db.get_user_notifications(user_id, page=1, per_page=limit)
    
    print(f"\n📋 用户 {user_id} 的最新通知 (共{total}条):")
    print("=" * 60)
    
    for i, notif in enumerate(notifications, 1):
        status = "🔵 未读" if not notif['is_read'] else "⚪ 已读"
        type_icon = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }.get(notif['type'], 'ℹ️')
        
        print(f"\n{i}. {type_icon} {notif['title']} - {status}")
        print(f"   {notif['message']}")
        print(f"   时间: {notif['created_at']}")
    
    print("=" * 60)
    
    return notifications

# ============================================================
# 示例10: 标记所有通知为已读
# ============================================================
def mark_all_as_read(user_id: int):
    """标记用户所有通知为已读"""
    success = db.mark_all_notifications_as_read(user_id)
    if success:
        print(f"✅ 用户 {user_id} 的所有通知已标记为已读")
    else:
        print(f"❌ 标记失败")

# ============================================================
# 完整示例流程
# ============================================================
def demo_notification_flow():
    """演示完整的通知流程"""
    print("\n" + "=" * 60)
    print("通知系统使用示例")
    print("=" * 60)
    
    # 使用测试用户ID
    test_user_id = 1
    
    print("\n【步骤1】发送各种类型的通知...")
    send_info_notification(test_user_id)
    send_success_notification(test_user_id)
    send_warning_notification(test_user_id)
    send_error_notification(test_user_id)
    
    print("\n【步骤2】模拟邮件收取场景...")
    notify_no_new_emails(test_user_id)
    notify_all_duplicates(test_user_id, found_count=5)
    notify_emails_received(test_user_id, new_count=3, total_found=8)
    
    print("\n【步骤3】检查未读通知数量...")
    unread_count = check_unread_count(test_user_id)
    
    print("\n【步骤4】获取最新通知列表...")
    notifications = get_latest_notifications(test_user_id, limit=5)
    
    print("\n【步骤5】标记所有通知为已读...")
    mark_all_as_read(test_user_id)
    
    print("\n【步骤6】再次检查未读数量...")
    check_unread_count(test_user_id)
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    demo_notification_flow()

