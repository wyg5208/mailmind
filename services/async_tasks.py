#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - Celery异步任务
"""

from services.celery_app import celery_app
from services.email_manager import EmailManager
from services.ai_client import AIClient
from services.digest_generator import DigestGenerator
from models.database import Database
import logging
import time

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_user_emails_async(self, user_id: int):
    """
    异步处理用户邮件 - Celery任务
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 处理结果 {'success': bool, 'new_emails': int, ...}
    """
    try:
        db = Database()
        email_manager = EmailManager()
        ai_client = AIClient()
        digest_generator = DigestGenerator()
        
        logger.info(f"[Celery] 任务 {self.request.id} 开始处理用户 {user_id} 的邮件")
        
        # 更新任务状态: 获取邮件阶段
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': '正在连接邮箱服务器...'}
        )
        
        # 获取用户邮箱账户
        user_accounts = db.get_user_email_accounts(user_id)
        if not user_accounts:
            logger.warning(f"用户 {user_id} 没有配置邮箱账户")
            return {'success': False, 'message': '没有配置邮箱账户'}
        
        # 获取用户配置
        user_configs = db.get_user_configs(user_id)
        since_days = int(user_configs.get('check_days_back', '1'))
        
        all_new_emails = []
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': '正在获取新邮件...'}
        )
        
        # 获取新邮件
        for i, account in enumerate(user_accounts):
            if not account['is_active']:
                continue
            
            try:
                # 获取账户密码
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT password FROM email_accounts WHERE id = ?', (account['id'],))
                    row = cursor.fetchone()
                    password = row['password'] if row else ''
                
                account_info = {
                    'email': account['email'],
                    'password': password,
                    'provider': account['provider']
                }
                
                logger.info(f"正在获取邮箱 {account['email']} 的新邮件")
                new_emails = email_manager.fetch_new_emails(account_info, since_days, user_id)
                
                if new_emails:
                    # 为每封邮件添加用户ID
                    for email in new_emails:
                        email['user_id'] = user_id
                    all_new_emails.extend(new_emails)
                    logger.info(f"从 {account['email']} 获取到 {len(new_emails)} 封新邮件")
                
                # 更新进度
                progress = 10 + int((i + 1) / len(user_accounts) * 20)
                self.update_state(
                    state='PROGRESS',
                    meta={'current': progress, 'total': 100, 
                          'status': f'已检查 {i+1}/{len(user_accounts)} 个邮箱'}
                )
                
            except Exception as e:
                logger.error(f"获取邮箱 {account['email']} 失败: {e}")
                continue
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': f'获取到 {len(all_new_emails)} 封新邮件'}
        )
        
        if not all_new_emails:
            logger.info(f"用户 {user_id} 没有新邮件")
            db.save_notification(
                user_id=user_id,
                title="邮件收取完成",
                message="本次收取没有找到新邮件。所有邮箱均已检查完毕,暂无新邮件到达。",
                notification_type='info'
            )
            return {'success': True, 'new_emails': 0, 'message': '没有新邮件'}
        
        # 去重处理
        self.update_state(
            state='PROGRESS',
            meta={'current': 35, 'total': 100, 'status': '正在去重...'}
        )
        
        deduplicated_emails = db.deduplicate_emails(all_new_emails, user_id=user_id)
        logger.info(f"用户 {user_id} 去重后剩余 {len(deduplicated_emails)} 封邮件")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 40, 'total': 100, 'status': f'去重后剩余 {len(deduplicated_emails)} 封邮件'}
        )
        
        if not deduplicated_emails:
            logger.info(f"用户 {user_id} 去重后没有新邮件")
            db.save_notification(
                user_id=user_id,
                title="邮件收取完成",
                message=f"找到 {len(all_new_emails)} 封邮件,但全部为重复邮件,已自动过滤。",
                notification_type='info'
            )
            return {'success': True, 'new_emails': 0, 'duplicates_removed': len(all_new_emails)}
        
        # AI摘要生成阶段
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': '正在生成AI摘要...'}
        )
        
        # 批量提交AI摘要任务 (并发处理)
        logger.info(f"开始为 {len(deduplicated_emails)} 封邮件生成AI摘要")
        ai_tasks = []
        for email in deduplicated_emails:
            task = generate_email_summary_async.delay(email)
            ai_tasks.append((email, task))
        
        # 等待AI任务完成 (设置超时)
        summarized_emails = []
        for i, (email, task) in enumerate(ai_tasks):
            try:
                # 等待单个任务完成,超时30秒
                ai_summary = task.get(timeout=30)
                email['ai_summary'] = ai_summary
                email['processed'] = True
                summarized_emails.append(email)
                
                # 更新进度
                progress = 50 + int((i + 1) / len(ai_tasks) * 30)
                self.update_state(
                    state='PROGRESS',
                    meta={'current': progress, 'total': 100, 
                          'status': f'AI摘要进度 {i+1}/{len(ai_tasks)}'}
                )
            except Exception as e:
                logger.error(f"AI摘要生成失败: {e}")
                # 使用备用摘要
                email['ai_summary'] = f"来自 {email.get('sender', 'Unknown')} 的邮件"
                email['processed'] = True
                summarized_emails.append(email)
        
        logger.info(f"AI摘要生成完成,成功 {len(summarized_emails)} 封")
        
        # 保存到数据库
        self.update_state(
            state='PROGRESS',
            meta={'current': 85, 'total': 100, 'status': '正在保存邮件...'}
        )
        
        saved_count = 0
        for email_data in summarized_emails:
            try:
                db.save_email(email_data)
                saved_count += 1
            except Exception as e:
                logger.error(f"保存邮件失败: {e}")
                continue
        
        logger.info(f"用户 {user_id} 成功保存 {saved_count} 封邮件")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': f'已保存 {saved_count} 封邮件'}
        )
        
        # 更新邮箱账户统计
        for account in user_accounts:
            if account['is_active']:
                try:
                    account_email_count = db.get_account_email_count(user_id, account['email'])
                    db.update_email_account_stats(user_id, account['email'], account_email_count)
                except Exception as e:
                    logger.error(f"更新邮箱统计失败: {e}")
        
        # 异步生成简报 (不等待完成)
        if saved_count > 0:
            self.update_state(
                state='PROGRESS',
                meta={'current': 95, 'total': 100, 'status': '正在生成简报...'}
            )
            
            recent_emails, _ = db.get_user_emails_filtered(user_id, page=1, per_page=saved_count)
            if recent_emails:
                # 异步提交简报生成任务,不阻塞主流程
                digest_task = generate_digest_async.delay(recent_emails, user_id)
                logger.info(f"简报生成任务已提交: {digest_task.id}")
        
        # 保存成功通知
        db.save_notification(
            user_id=user_id,
            title="新邮件到达",
            message=f"成功收取并处理了 {saved_count} 封新邮件,已生成邮件简报。去重前共发现 {len(all_new_emails)} 封邮件。",
            notification_type='success'
        )
        
        logger.info(f"[Celery] 任务 {self.request.id} 完成,用户 {user_id} 处理了 {saved_count} 封邮件")
        
        return {
            'success': True,
            'new_emails': saved_count,
            'total_found': len(all_new_emails),
            'deduplicated': len(deduplicated_emails),
            'duplicates_removed': len(all_new_emails) - len(deduplicated_emails)
        }
        
    except Exception as e:
        logger.error(f"[Celery] 异步处理用户 {user_id} 邮件失败: {e}", exc_info=True)
        
        # 保存错误通知
        try:
            db = Database()
            db.save_notification(
                user_id=user_id,
                title="邮件收取失败",
                message=f"处理邮件时出现错误: {str(e)}",
                notification_type='error'
            )
        except:
            pass
        
        # Celery自动重试机制 (最多3次)
        raise self.retry(exc=e, countdown=60)  # 60秒后重试


@celery_app.task(bind=True)
def generate_email_summary_async(self, email_data: dict):
    """
    异步生成单封邮件摘要
    
    Args:
        email_data: 邮件数据字典
        
    Returns:
        str: AI生成的摘要
    """
    try:
        ai_client = AIClient()
        summary = ai_client.summarize_email(email_data)
        return summary
    except Exception as e:
        logger.error(f"[Celery] 生成摘要失败: {e}")
        # 返回备用摘要
        return f"来自 {email_data.get('sender', 'Unknown')} 的邮件: {email_data.get('subject', 'No subject')}"


@celery_app.task(bind=True)
def generate_digest_async(self, emails: list, user_id: int):
    """
    异步生成简报
    
    Args:
        emails: 邮件列表
        user_id: 用户ID
        
    Returns:
        dict: 生成结果 {'success': bool}
    """
    try:
        db = Database()
        digest_generator = DigestGenerator()
        
        logger.info(f"[Celery] 任务 {self.request.id} 开始为用户 {user_id} 生成简报")
        
        # 生成简报
        digest = digest_generator.create_digest(emails)
        
        # 保存简报
        db.save_digest(digest, user_id=user_id)
        
        logger.info(f"[Celery] 用户 {user_id} 简报生成完成: {digest.get('title', 'Unknown')}")
        
        # 发送简报完成通知
        db.save_notification(
            user_id=user_id,
            title="邮件简报已生成",
            message=f"最新简报已准备完成: {digest.get('title', '')}",
            notification_type='info'
        )
        
        return {'success': True, 'digest_id': digest.get('id')}
        
    except Exception as e:
        logger.error(f"[Celery] 简报生成失败: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

