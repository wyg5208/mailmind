#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 智能定时任务管理器
支持interval、cron、custom三种调度策略
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List
from collections import defaultdict

logger = logging.getLogger(__name__)

class EmailSchedulerManager:
    """智能邮件处理调度管理器"""
    
    # 调度类型常量
    SCHEDULE_TYPE_INTERVAL = 'interval'  # 间隔触发（如每360分钟）
    SCHEDULE_TYPE_CRON = 'cron'  # 定时触发（如每天6点）
    SCHEDULE_TYPE_CUSTOM = 'custom'  # 自定义规则（如整点、偶数整点）
    
    def __init__(self, scheduler, max_concurrent_users=3):
        self.scheduler = scheduler
        self.max_concurrent_users = max_concurrent_users
        self.current_processing: Set[int] = set()
        self.user_jobs: Dict[int, str] = {}
        self.processing_times: Dict[int, float] = {}
        self.error_counts: Dict[int, int] = defaultdict(int)
        self.last_success: Dict[int, datetime] = {}
        self.lock = threading.Lock()
    
    def create_user_schedule(self, user_id: int, schedule_config: Dict):
        """
        为用户创建个性化定时任务
        
        Args:
            user_id: 用户ID
            schedule_config: 调度配置字典，包含：
                - type: 调度类型 (interval/cron/custom)
                - interval_minutes: 间隔分钟数（interval类型）
                - cron_hours: Cron小时列表（cron类型），如[6, 18]表示每天6点和18点
                - cron_minutes: Cron分钟列表（cron类型），如[0, 15, 30, 45]
                - custom_rule: 自定义规则（custom类型），如'hourly', 'even_hours', 'odd_hours'
        """
        job_id = f'user_{user_id}_email_processing'
        schedule_type = schedule_config.get('type', self.SCHEDULE_TYPE_INTERVAL)
        
        try:
            # 移除旧任务
            if job_id in self.user_jobs and self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"移除用户 {user_id} 的旧定时任务")
            
            # 根据调度类型创建任务
            if schedule_type == self.SCHEDULE_TYPE_INTERVAL:
                self._create_interval_schedule(user_id, job_id, schedule_config)
            elif schedule_type == self.SCHEDULE_TYPE_CRON:
                self._create_cron_schedule(user_id, job_id, schedule_config)
            elif schedule_type == self.SCHEDULE_TYPE_CUSTOM:
                self._create_custom_schedule(user_id, job_id, schedule_config)
            else:
                logger.error(f"不支持的调度类型: {schedule_type}")
                return
            
            self.user_jobs[user_id] = job_id
            logger.info(f"为用户 {user_id} 创建定时任务成功: {self._format_schedule_info(schedule_config)}")
            
        except Exception as e:
            logger.error(f"创建用户 {user_id} 定时任务失败: {e}")
    
    def _create_interval_schedule(self, user_id: int, job_id: str, config: Dict):
        """创建间隔触发任务"""
        interval_minutes = int(config.get('interval_minutes', 30))
        
        # 计算错峰启动时间（避免所有用户同时处理）
        offset_minutes = (user_id * 3) % 30
        start_time = datetime.now() + timedelta(minutes=offset_minutes)
        
        self.scheduler.add_job(
            func=self._safe_process_user_emails,
            trigger="interval",
            minutes=interval_minutes,
            start_date=start_time,
            id=job_id,
            args=[user_id],
            max_instances=1,
            coalesce=True,  # 合并错过的任务
            replace_existing=True
        )
        
        logger.info(f"  └─ 间隔触发: 每 {interval_minutes} 分钟, 错峰 {offset_minutes} 分钟后首次执行")
    
    def _create_cron_schedule(self, user_id: int, job_id: str, config: Dict):
        """创建Cron定时触发任务"""
        cron_hours = config.get('cron_hours', [6])  # 默认每天6点
        cron_minutes = config.get('cron_minutes', [0])  # 默认0分
        
        # 转换为逗号分隔的字符串格式
        hour_str = ','.join(map(str, cron_hours))
        minute_str = ','.join(map(str, cron_minutes))
        
        self.scheduler.add_job(
            func=self._safe_process_user_emails,
            trigger="cron",
            hour=hour_str,
            minute=minute_str,
            id=job_id,
            args=[user_id],
            max_instances=1,
            coalesce=True,
            replace_existing=True
        )
        
        logger.info(f"  └─ Cron触发: 每天 {hour_str} 时 {minute_str} 分")
    
    def _create_custom_schedule(self, user_id: int, job_id: str, config: Dict):
        """创建自定义规则触发任务"""
        custom_rule = config.get('custom_rule', 'hourly')
        
        if custom_rule == 'hourly':
            # 每个整点
            minute = config.get('cron_minutes', [0])[0]
            self.scheduler.add_job(
                func=self._safe_process_user_emails,
                trigger="cron",
                hour='*',
                minute=str(minute),
                id=job_id,
                args=[user_id],
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info(f"  └─ 自定义触发: 每个整点的第 {minute} 分钟")
            
        elif custom_rule == 'even_hours':
            # 偶数整点
            even_hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]
            minute = config.get('cron_minutes', [0])[0]
            hour_str = ','.join(map(str, even_hours))
            self.scheduler.add_job(
                func=self._safe_process_user_emails,
                trigger="cron",
                hour=hour_str,
                minute=str(minute),
                id=job_id,
                args=[user_id],
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info(f"  └─ 自定义触发: 偶数整点的第 {minute} 分钟")
            
        elif custom_rule == 'odd_hours':
            # 奇数整点
            odd_hours = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
            minute = config.get('cron_minutes', [0])[0]
            hour_str = ','.join(map(str, odd_hours))
            self.scheduler.add_job(
                func=self._safe_process_user_emails,
                trigger="cron",
                hour=hour_str,
                minute=str(minute),
                id=job_id,
                args=[user_id],
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info(f"  └─ 自定义触发: 奇数整点的第 {minute} 分钟")
        
        elif custom_rule == 'every_n_hours':
            # 每N小时
            n_hours = config.get('n_hours', 6)
            minute = config.get('cron_minutes', [0])[0]
            hours = list(range(0, 24, n_hours))
            hour_str = ','.join(map(str, hours))
            self.scheduler.add_job(
                func=self._safe_process_user_emails,
                trigger="cron",
                hour=hour_str,
                minute=str(minute),
                id=job_id,
                args=[user_id],
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info(f"  └─ 自定义触发: 每 {n_hours} 小时 (于 {hour_str} 时的第 {minute} 分钟)")
        else:
            logger.error(f"不支持的自定义规则: {custom_rule}")
    
    def _format_schedule_info(self, config: Dict) -> str:
        """格式化调度配置信息为可读字符串"""
        schedule_type = config.get('type', self.SCHEDULE_TYPE_INTERVAL)
        
        if schedule_type == self.SCHEDULE_TYPE_INTERVAL:
            interval_minutes = config.get('interval_minutes', 30)
            return f"间隔触发 (每 {interval_minutes} 分钟)"
        
        elif schedule_type == self.SCHEDULE_TYPE_CRON:
            hours = config.get('cron_hours', [6])
            minutes = config.get('cron_minutes', [0])
            return f"定时触发 (每天 {','.join(map(str, hours))} 时 {','.join(map(str, minutes))} 分)"
        
        elif schedule_type == self.SCHEDULE_TYPE_CUSTOM:
            custom_rule = config.get('custom_rule', 'hourly')
            rule_names = {
                'hourly': '每个整点',
                'even_hours': '偶数整点',
                'odd_hours': '奇数整点',
                'every_n_hours': f"每 {config.get('n_hours', 6)} 小时"
            }
            return f"自定义触发 ({rule_names.get(custom_rule, custom_rule)})"
        
        return "未知类型"
    
    def remove_user_schedule(self, user_id: int):
        """移除用户的定时任务"""
        job_id = f'user_{user_id}_email_processing'
        
        try:
            if job_id in self.user_jobs and self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                del self.user_jobs[user_id]
                logger.info(f"移除用户 {user_id} 的定时任务")
        except Exception as e:
            logger.error(f"移除用户 {user_id} 定时任务失败: {e}")
    
    def _safe_process_user_emails(self, user_id: int):
        """安全的用户邮件处理（带并发控制和性能监控）"""
        
        # 检查并发限制
        with self.lock:
            if len(self.current_processing) >= self.max_concurrent_users:
                logger.info(f"达到并发限制 ({self.max_concurrent_users})，用户 {user_id} 的任务将延后处理")
                return
            
            # 检查该用户是否已在处理中
            if user_id in self.current_processing:
                logger.warning(f"用户 {user_id} 的邮件正在处理中，跳过本次任务")
                return
            
            # 添加到处理中列表
            self.current_processing.add(user_id)
        
        start_time = time.time()
        
        try:
            # 导入处理函数（避免循环导入）
            from app import process_user_emails
            
            logger.info(f"⏰ [定时任务] 开始处理用户 {user_id} 的邮件...")
            process_user_emails(user_id)
            
            # 记录成功处理
            processing_time = time.time() - start_time
            self.processing_times[user_id] = processing_time
            self.last_success[user_id] = datetime.now()
            self.error_counts[user_id] = 0  # 重置错误计数
            
            logger.info(f"✓ [定时任务] 用户 {user_id} 邮件处理完成，耗时 {processing_time:.2f} 秒")
            
        except Exception as e:
            # 记录错误
            self.error_counts[user_id] += 1
            processing_time = time.time() - start_time
            
            logger.error(f"✗ [定时任务] 用户 {user_id} 邮件处理失败（第 {self.error_counts[user_id]} 次错误）: {e}")
            
            # 如果连续错误过多，暂停该用户的任务
            if self.error_counts[user_id] >= 5:
                logger.warning(f"⚠ 用户 {user_id} 连续错误过多，暂停定时任务")
                self.remove_user_schedule(user_id)
        
        finally:
            # 从处理中列表移除
            with self.lock:
                self.current_processing.discard(user_id)
            
            # 添加处理间隔，避免过载
            time.sleep(2)
    
    def update_all_user_schedules(self):
        """更新所有用户的定时任务"""
        try:
            from models.database import Database
            db = Database()
            
            # 获取所有活跃用户
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE is_active = 1')
                user_ids = [row['id'] for row in cursor.fetchall()]
            
            # 为每个用户创建定时任务
            for user_id in user_ids:
                schedule_config = self._get_user_schedule_config(user_id, db)
                self.create_user_schedule(user_id, schedule_config)
                
            logger.info(f"更新了 {len(user_ids)} 个用户的定时任务")
            
        except Exception as e:
            logger.error(f"更新用户定时任务失败: {e}")
    
    def _get_user_schedule_config(self, user_id: int, db) -> Dict:
        """获取用户的调度配置"""
        try:
            user_configs = db.get_user_configs(user_id)
            
            # 获取调度类型（默认为interval）
            schedule_type = user_configs.get('schedule_type', self.SCHEDULE_TYPE_INTERVAL)
            
            config = {'type': schedule_type}
            
            if schedule_type == self.SCHEDULE_TYPE_INTERVAL:
                # 间隔触发配置
                config['interval_minutes'] = int(user_configs.get('check_interval_minutes', '30'))
                
            elif schedule_type == self.SCHEDULE_TYPE_CRON:
                # Cron定时触发配置
                # 支持格式: "6,18" 表示每天6点和18点
                hours_str = user_configs.get('cron_hours', '6')
                minutes_str = user_configs.get('cron_minutes', '0')
                
                config['cron_hours'] = [int(h.strip()) for h in hours_str.split(',')]
                config['cron_minutes'] = [int(m.strip()) for m in minutes_str.split(',')]
                
            elif schedule_type == self.SCHEDULE_TYPE_CUSTOM:
                # 自定义规则配置
                config['custom_rule'] = user_configs.get('custom_rule', 'hourly')
                config['cron_minutes'] = [int(user_configs.get('custom_minute', '0'))]
                
                if config['custom_rule'] == 'every_n_hours':
                    config['n_hours'] = int(user_configs.get('n_hours', '6'))
            
            return config
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 调度配置失败: {e}, 使用默认配置")
            return {
                'type': self.SCHEDULE_TYPE_INTERVAL,
                'interval_minutes': 30
            }
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计信息"""
        return {
            'current_processing_users': len(self.current_processing),
            'max_concurrent_users': self.max_concurrent_users,
            'total_user_jobs': len(self.user_jobs),
            'average_processing_time': sum(self.processing_times.values()) / len(self.processing_times) if self.processing_times else 0,
            'users_with_errors': len([u for u, c in self.error_counts.items() if c > 0]),
            'last_activity': max(self.last_success.values()) if self.last_success else None
        }
    
    def pause_user_schedule(self, user_id: int):
        """暂停用户的定时任务"""
        job_id = f'user_{user_id}_email_processing'
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.pause_job(job_id)
                logger.info(f"暂停用户 {user_id} 的定时任务")
        except Exception as e:
            logger.error(f"暂停用户 {user_id} 定时任务失败: {e}")
    
    def resume_user_schedule(self, user_id: int):
        """恢复用户的定时任务"""
        job_id = f'user_{user_id}_email_processing'
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.resume_job(job_id)
                logger.info(f"恢复用户 {user_id} 的定时任务")
        except Exception as e:
            logger.error(f"恢复用户 {user_id} 定时任务失败: {e}")
    
    def get_user_schedule_status(self, user_id: int) -> Dict:
        """获取用户定时任务状态"""
        job_id = f'user_{user_id}_email_processing'
        
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                # 获取触发器类型和描述
                trigger_type = type(job.trigger).__name__
                
                # 格式化下次运行时间
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
                
                # 获取触发器配置信息
                trigger_info = self._format_trigger_info(job.trigger)
                
                return {
                    'active': True,
                    'next_run': next_run,
                    'trigger_type': trigger_type,
                    'trigger_info': trigger_info,
                    'last_success': self.last_success.get(user_id).strftime('%Y-%m-%d %H:%M:%S') if user_id in self.last_success else None,
                    'error_count': self.error_counts.get(user_id, 0),
                    'avg_processing_time': round(self.processing_times.get(user_id, 0), 2)
                }
            else:
                return {'active': False}
        except Exception as e:
            logger.error(f"获取用户 {user_id} 任务状态失败: {e}")
            return {'active': False, 'error': str(e)}
    
    def _format_trigger_info(self, trigger) -> str:
        """格式化触发器信息"""
        try:
            if hasattr(trigger, 'interval'):
                # IntervalTrigger
                total_minutes = trigger.interval.total_seconds() / 60
                if total_minutes >= 60:
                    hours = total_minutes / 60
                    return f"每 {hours:.1f} 小时"
                else:
                    return f"每 {int(total_minutes)} 分钟"
            elif hasattr(trigger, 'fields'):
                # CronTrigger
                hour_field = trigger.fields[5]  # hour field
                minute_field = trigger.fields[6]  # minute field
                
                return f"每天 {hour_field} 时 {minute_field} 分"
            else:
                return str(trigger)
        except:
            return "未知触发器"

# 全局调度管理器实例
scheduler_manager = None

def init_scheduler_manager(scheduler):
    """初始化调度管理器"""
    global scheduler_manager
    scheduler_manager = EmailSchedulerManager(scheduler)
    return scheduler_manager
