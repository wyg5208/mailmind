#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 主应用
支持多邮件服务商的智能邮件收取和摘要生成
"""

import os
import threading
import time
from datetime import datetime, timedelta
import logging
import logging.handlers
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import zipfile
import tempfile
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash

from config import Config
from services.email_manager import EmailManager
from services.ai_client import AIClient
from services.translation_service import translation_service
from services.digest_generator import DigestGenerator
from services.auth_service import auth_service
# 邮件撰写和回复功能路由
from routes.compose_routes import register_compose_routes
from routes.email_reply_routes import register_reply_routes
# 邮件分类功能路由
from routes.classification_routes import register_classification_routes
from services.cache_service import cache_service
from services.cache_manager import cache_manager
from services.auto_cache_cleaner import auto_cache_cleaner
from models.database import Database
from utils.logger import setup_logger
from utils.log_filter import setup_log_filters

# 性能保护变量
current_processing_users = set()
processing_lock = threading.Lock()
MAX_CONCURRENT_USERS = 3

# 设置日志
logger = setup_logger(__name__)

# 配置Flask应用日志
def setup_flask_logging(app):
    """配置Flask应用的日志输出到文件（使用共享文件处理器）"""
    from utils.logger import add_handler_to_logger
    
    if not app.debug:
        # 使用共享的文件处理器，避免重复创建
        add_handler_to_logger(app.logger)
        app.logger.setLevel(logging.INFO)
        
        # 添加到Werkzeug日志（HTTP请求日志）
        werkzeug_logger = logging.getLogger('werkzeug')
        add_handler_to_logger(werkzeug_logger)
        werkzeug_logger.setLevel(logging.INFO)
        
        # 为Werkzeug日志添加过滤器
        setup_log_filters(werkzeug_logger)
        
        print("[日志系统] Flask应用日志已配置完成，使用共享文件处理器")

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# 配置Flask日志
setup_flask_logging(app)

# 初始化组件
db = Database()
scheduler = BackgroundScheduler()
email_manager = EmailManager()
ai_client = AIClient()
digest_generator = DigestGenerator()

# 导入并初始化调度管理器
from services.scheduler_manager import EmailSchedulerManager
scheduler_manager = EmailSchedulerManager(scheduler)

def process_emails():
    """处理所有用户的邮件（定时任务用）"""
    logger.info("开始定时处理所有用户邮件...")
    
    try:
        # 获取所有活跃用户
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE is_active = 1')
            user_ids = [row['id'] for row in cursor.fetchall()]
        
        for user_id in user_ids:
            try:
                process_user_emails(user_id)
            except Exception as e:
                logger.error(f"处理用户 {user_id} 邮件时出错: {e}")
                continue
                
    except Exception as e:
        logger.error(f"定时处理邮件时发生错误: {e}")

def process_user_emails(user_id: int, is_manual_fetch: bool = False):
    """处理指定用户的邮件
    
    Args:
        user_id: 用户ID
        is_manual_fetch: 是否为手动实时收取（True=手动收取，False=定时收取）
    """
    global current_processing_users, processing_lock
    
    # 检查并发限制
    with processing_lock:
        if len(current_processing_users) >= MAX_CONCURRENT_USERS:
            logger.info(f"达到并发限制 ({MAX_CONCURRENT_USERS})，用户 {user_id} 的任务将延后处理")
            return
        
        if user_id in current_processing_users:
            logger.warning(f"用户 {user_id} 的邮件正在处理中，跳过本次任务")
            return
        
        current_processing_users.add(user_id)
    
    start_time = time.time()
    fetch_type = "手动" if is_manual_fetch else "定时"
    logger.info(f"开始处理用户 {user_id} 的邮件（{fetch_type}收取）...")
    
    try:
        # 获取用户的邮箱账户
        user_accounts = db.get_user_email_accounts(user_id)
        if not user_accounts:
            logger.info(f"用户 {user_id} 没有配置邮箱账户")
            return
        
        # 获取用户配置
        user_configs = db.get_user_configs(user_id)
        since_days = int(user_configs.get('check_days_back', '1'))
        max_emails_per_account = int(user_configs.get('max_emails_per_account', '20'))
        
        logger.info(f"用户 {user_id} 配置 - 检查天数: {since_days}天, 每次最大处理数: {max_emails_per_account}封")
        
        all_new_emails = []
        
        # 处理用户的每个邮箱账户
        for account in user_accounts:
            if not account['is_active']:
                continue
                
            logger.info(f"处理邮箱: {account['email']}")
            try:
                # 为邮件管理器构造账户信息
                account_info = {
                    'email': account['email'],
                    'password': _get_account_password(account['id']),  # 需要单独获取密码
                    'provider': account['provider']
                }
                
                new_emails = email_manager.fetch_new_emails(
                    account_info, 
                    since_days=since_days, 
                    user_id=user_id,
                    max_emails=max_emails_per_account
                )
                if new_emails:
                    # 为每封邮件添加用户ID
                    for email in new_emails:
                        email['user_id'] = user_id
                    all_new_emails.extend(new_emails)
                    logger.info(f"从 {account['email']} 获取到 {len(new_emails)} 封新邮件")
            except Exception as e:
                logger.error(f"处理邮箱 {account['email']} 时出错: {e}")
                continue
        
        if not all_new_emails:
            logger.info(f"用户 {user_id} 没有新邮件需要处理")
            # 保存系统通知，告知用户收取结果
            db.save_notification(
                user_id=user_id,
                title="邮件收取完成",
                message="本次收取没有找到新邮件。所有邮箱均已检查完毕，暂无新邮件到达。",
                notification_type='info'
            )
            return
            
        logger.info(f"用户 {user_id} 总共发现 {len(all_new_emails)} 封新邮件，开始去重...")
        
        # 去重处理（用户隔离）
        deduplicated_emails = db.deduplicate_emails(all_new_emails, user_id=user_id)
        logger.info(f"用户 {user_id} 去重后剩余 {len(deduplicated_emails)} 封邮件")
        
        if not deduplicated_emails:
            logger.info(f"用户 {user_id} 去重后没有新邮件需要处理")
            # 保存系统通知，说明去重结果
            db.save_notification(
                user_id=user_id,
                title="邮件收取完成",
                message=f"找到 {len(all_new_emails)} 封邮件，但全部为重复邮件，已自动过滤。系统已为您去重，避免重复查看。",
                notification_type='info'
            )
            return
            
        logger.info(f"开始为用户 {user_id} 生成AI摘要...")
        
        # 生成AI摘要
        summarized_emails = ai_client.batch_summarize(deduplicated_emails)
        
        # 保存到数据库
        saved_count = 0
        for email_data in summarized_emails:
            try:
                db.save_email(email_data)
                saved_count += 1
            except Exception as e:
                logger.error(f"保存邮件失败: {e}")
                continue
        
        logger.info(f"用户 {user_id} 成功保存 {saved_count} 封邮件")
        
        # 更新每个邮箱账户的统计信息
        for account in user_accounts:
            if account['is_active']:
                account_email_count = db.get_account_email_count(user_id, account['email'])
                db.update_email_account_stats(user_id, account['email'], account_email_count)
                logger.debug(f"更新邮箱 {account['email']} 统计: {account_email_count} 封邮件")
        
        # 生成用户专属简报 - 使用已保存的邮件（包含ID）
        if saved_count > 0:
            # 获取最近保存的邮件（包含数据库ID）
            recent_emails, _ = db.get_user_emails_filtered(user_id, page=1, per_page=saved_count)
            if recent_emails:
                # 传递is_manual_fetch参数，影响AI摘要的生成风格
                digest = digest_generator.create_digest(recent_emails, is_manual_fetch=is_manual_fetch)
                db.save_digest(digest, user_id=user_id)
                logger.info(f"用户 {user_id} 简报生成完成（{fetch_type}收取）")
                
                # 保存成功通知
                db.save_notification(
                    user_id=user_id,
                    title="新邮件到达",
                    message=f"成功收取并处理了 {saved_count} 封新邮件，已生成邮件简报。去重前共发现 {len(all_new_emails)} 封邮件。",
                    notification_type='success'
                )
            else:
                logger.warning(f"用户 {user_id} 无法获取已保存的邮件用于生成简报")
        
        # 记录处理时间
        processing_time = time.time() - start_time
        logger.info(f"用户 {user_id} 邮件处理完成，耗时 {processing_time:.2f} 秒")
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"处理用户 {user_id} 邮件时发生错误（耗时 {processing_time:.2f} 秒）: {e}")
    
    finally:
        # 确保从处理中列表移除
        with processing_lock:
            current_processing_users.discard(user_id)
        
        # 添加处理间隔，避免过载
        time.sleep(1)

def _get_account_password(account_id: int) -> str:
    """获取邮箱账户密码"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password FROM email_accounts WHERE id = ?', (account_id,))
            row = cursor.fetchone()
            return row['password'] if row else ''
    except Exception as e:
        logger.error(f"获取账户密码失败: {e}")
        return ''

@app.route('/')
@auth_service.require_login
def index():
    """首页 - 显示最新简报"""
    try:
        user = auth_service.get_current_user()
        logger.info(f"[首页访问] 用户ID: {user['id']}, 用户名: {user.get('username', 'N/A')}")
        
        # 获取用户专属的最新简报和统计信息
        latest_digest = db.get_user_latest_digest(user['id'])
        logger.info(f"[简报查询] 用户{user['id']} - 找到简报: {latest_digest is not None}")
        if latest_digest:
            logger.info(f"[简报详情] ID: {latest_digest['id']}, 标题: {latest_digest.get('title', 'N/A')}, 邮件数: {latest_digest.get('email_count', 0)}")
        
        stats = db.get_user_stats(user['id'])
        
        # 获取用户配置（用于系统信息显示）
        user_configs = db.get_user_configs(user['id'])
        
        return render_template('index.html', 
                             digest=latest_digest, 
                             stats=stats, 
                             config=Config, 
                             user=user,
                             user_configs=user_configs)
    except Exception as e:
        logger.error(f"加载首页时出错: {e}")
        flash('加载数据时出错，请稍后重试', 'error')
        return render_template('index.html', 
                             digest=None, 
                             stats=None, 
                             config=Config, 
                             user=None,
                             user_configs={})

@app.route('/classification/rules')
@auth_service.require_login
def classification_rules():
    """邮件分类规则管理页面"""
    try:
        user = auth_service.get_current_user()
        return render_template('classification_rules.html', user=user, config=Config)
    except Exception as e:
        logger.error(f"加载分类规则页面时出错: {e}")
        flash('加载页面失败，请稍后重试', 'error')
        return redirect(url_for('emails'))

@app.route('/emails')
@auth_service.require_login
def emails():
    """邮件列表页面"""
    try:
        user = auth_service.get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 获取筛选参数
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '')
        provider = request.args.get('provider', '')
        processed = request.args.get('processed', '')
        
        # 获取用户邮件（带筛选）
        all_emails, total = db.get_user_emails_filtered(
            user['id'], 
            page=page, 
            per_page=per_page,
            search=search,
            category=category,
            provider=provider,
            processed=processed
        )
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        return render_template('emails.html', emails=all_emails, pagination=pagination, user=user)
    except Exception as e:
        logger.error(f"加载邮件列表时出错: {e}")
        flash('加载邮件列表时出错，请稍后重试', 'error')
        return render_template('emails.html', emails=[], pagination={}, user=None)

@app.route('/settings')
@auth_service.require_login
def settings():
    """设置页面"""
    try:
        user = auth_service.get_current_user()
        accounts = db.get_user_email_accounts(user['id'])
        
        # 获取用户配置
        user_configs = db.get_user_configs(user['id'])
        
        # 获取系统配置（仅管理员可见）
        system_configs = {}
        if user.get('is_admin'):
            system_configs = {
                'ai_provider': db.get_system_config('ai_provider', Config.AI_PROVIDER),
                'glm_model': db.get_system_config('glm_model', Config.GLM_MODEL),
                'summary_max_length': db.get_system_config('summary_max_length', str(Config.SUMMARY_MAX_LENGTH)),
                'summary_temperature': db.get_system_config('summary_temperature', str(Config.SUMMARY_TEMPERATURE))
            }
        
        return render_template('settings.html', 
                             accounts=accounts, 
                             user=user, 
                             user_configs=user_configs,
                             system_configs=system_configs)
    except Exception as e:
        logger.error(f"加载设置页面时出错: {e}")
        flash('加载设置时出错，请稍后重试', 'error')
        return render_template('settings.html', accounts=[], user=None, user_configs={}, system_configs={})

@app.route('/add_account', methods=['POST'])
@auth_service.require_login
def add_account():
    """添加邮箱账户"""
    try:
        user = auth_service.get_current_user()
        email = request.form.get('email')
        password = request.form.get('password')
        provider = request.form.get('provider')
        
        logger.info(f"用户 {user['id']} 尝试添加邮箱账户: {email} (服务商: {provider})")
        
        if not all([email, password, provider]):
            logger.warning(f"添加邮箱账户失败: 缺少必需字段")
            flash('请填写所有必需字段', 'error')
            return redirect(url_for('settings'))
        
        # 测试连接
        logger.info(f"开始测试邮箱连接: {email}")
        success, message = email_manager.test_connection(email, password, provider)
        
        if not success:
            logger.error(f"邮箱连接测试失败 - 邮箱: {email}, 服务商: {provider}, 错误: {message}")
            flash(f'邮箱连接测试失败: {message}', 'error')
            return redirect(url_for('settings'))
        
        logger.info(f"邮箱连接测试成功: {email}")
        
        # 保存账户配置到当前用户
        success = db.save_user_email_account(user['id'], email, password, provider)
        if success:
            logger.info(f"邮箱账户添加成功: 用户 {user['id']}, 邮箱 {email}")
            flash('邮箱账户添加成功', 'success')
        else:
            logger.error(f"保存邮箱账户失败: 用户 {user['id']}, 邮箱 {email}")
            flash('保存邮箱账户失败', 'error')
        
    except Exception as e:
        logger.error(f"添加邮箱账户时出错: {e}", exc_info=True)
        flash('添加邮箱账户时出错，请稍后重试', 'error')
    
    return redirect(url_for('settings'))

@app.route('/api/email-account/delete/<int:account_id>', methods=['DELETE'])
@auth_service.require_login
def delete_email_account(account_id):
    """删除邮箱账户"""
    try:
        user = auth_service.get_current_user()
        success = db.delete_user_email_account(account_id, user['id'])
        
        if success:
            logger.info(f"用户 {user['id']} 成功删除邮箱账户 ID: {account_id}")
            return jsonify({
                'success': True,
                'message': '邮箱账户删除成功'
            })
        else:
            logger.warning(f"用户 {user['id']} 删除邮箱账户失败 ID: {account_id}")
            return jsonify({
                'success': False,
                'message': '账户不存在或删除失败'
            }), 404
            
    except Exception as e:
        logger.error(f"删除邮箱账户时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

@app.route('/api/email-account/transfer/<int:account_id>', methods=['POST'])
@auth_service.require_login
def transfer_email_account(account_id):
    """转移邮箱账户到其他用户"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        if not data or 'target_username' not in data:
            return jsonify({
                'success': False,
                'message': '缺少目标用户名'
            }), 400
        
        target_username = data['target_username'].strip()
        
        if not target_username:
            return jsonify({
                'success': False,
                'message': '目标用户名不能为空'
            }), 400
        
        # 防止转移给自己
        if target_username == user['username']:
            return jsonify({
                'success': False,
                'message': '不能转移给自己'
            }), 400
        
        success, message = db.transfer_email_account(account_id, user['id'], target_username)
        
        if success:
            logger.info(f"用户 {user['id']} 成功转移邮箱账户 ID: {account_id} 到用户: {target_username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"用户 {user['id']} 转移邮箱账户失败: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"转移邮箱账户时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'转移失败: {str(e)}'
        }), 500

@app.route('/trigger', methods=['POST'])
@auth_service.require_login
def trigger_processing():
    """手动触发邮件处理 - 智能选择Celery或线程模式"""
    user = auth_service.get_current_user()
    
    # ⚠️ 首先检查用户是否配置了邮箱账户
    user_accounts = db.get_user_email_accounts(user['id'])
    if not user_accounts:
        logger.warning(f"用户 {user['id']} ({user['username']}) 尝试收取邮件，但未配置邮箱账户")
        return jsonify({
            'success': False,
            'message': '您还没有配置任何邮箱账户！',
            'action': 'redirect',
            'redirect_url': '/settings',
            'prompt': '请先在设置页面添加您的邮箱账户，然后再进行邮件收取。'
        }), 400
    
    # 检查是否有激活的账户
    active_accounts = [acc for acc in user_accounts if acc.get('is_active', True)]
    if not active_accounts:
        logger.warning(f"用户 {user['id']} ({user['username']}) 的所有邮箱账户都已停用")
        return jsonify({
            'success': False,
            'message': '您的所有邮箱账户都已停用！',
            'action': 'redirect',
            'redirect_url': '/settings',
            'prompt': '请在设置页面启用至少一个邮箱账户，然后再进行邮件收取。'
        }), 400
    
    logger.info(f"用户 {user['id']} ({user['username']}) 发起邮件收取，配置了 {len(active_accounts)} 个活跃邮箱账户")
    
    # 尝试使用Celery（如果可用）
    try:
        # 检查Celery是否可用
        from services.celery_app import celery_app
        from services.async_tasks import process_user_emails_async
        
        # 尝试ping Celery
        celery_app.control.inspect().ping()
        
        # Celery可用，提交异步任务
        task = process_user_emails_async.delay(user['id'])
        logger.info(f"✅ 用户 {user['id']} 使用Celery处理邮件,任务ID: {task.id}")
        
        return jsonify({
            'success': True,
            'message': '邮件处理已启动（异步模式）',
            'task_id': task.id,
            'use_celery': True
        })
        
    except Exception as celery_error:
        # Celery不可用，降级到线程模式
        logger.warning(f"⚠️ Celery不可用: {celery_error}, 使用线程模式")
        
        try:
            # 使用daemon线程处理（不阻塞主进程）
            # 手动触发时传递is_manual_fetch=True
            thread = threading.Thread(
                target=process_user_emails, 
                args=(user['id'], True),  # True表示手动收取
                daemon=True,
                name=f"EmailProcessing-User{user['id']}"
            )
            thread.start()
            
            logger.info(f"✅ 用户 {user['id']} 使用线程处理邮件（手动触发）")
            
            return jsonify({
                'success': True,
                'message': '邮件处理已启动（快速模式）',
                'use_celery': False
            })
            
        except Exception as thread_error:
            logger.error(f"❌ 线程处理也失败: {thread_error}")
            return jsonify({
                'success': False,
                'message': f'处理失败: {str(thread_error)}'
            })

@app.route('/api/task-status/<task_id>')
@auth_service.require_login
def get_task_status(task_id):
    """
    查询Celery任务状态
    
    Args:
        task_id: Celery任务ID
        
    Returns:
        JSON: 任务状态信息
    """
    try:
        from celery.result import AsyncResult
        from services.celery_app import celery_app
        
        task = AsyncResult(task_id, app=celery_app)
        
        if task.state == 'PENDING':
            # 任务等待中
            response = {
                'state': task.state,
                'status': '任务等待中...',
                'current': 0,
                'total': 100
            }
        elif task.state == 'PROGRESS':
            # 任务进行中
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 100),
                'status': task.info.get('status', '处理中...')
            }
        elif task.state == 'SUCCESS':
            # 任务成功
            response = {
                'state': task.state,
                'result': task.info,
                'status': '处理完成',
                'current': 100,
                'total': 100
            }
        elif task.state == 'FAILURE':
            # 任务失败
            response = {
                'state': task.state,
                'status': '处理失败',
                'error': str(task.info),
                'current': 0,
                'total': 100
            }
        elif task.state == 'RETRY':
            # 任务重试中
            response = {
                'state': task.state,
                'status': '任务重试中...',
                'current': task.info.get('current', 0),
                'total': 100
            }
        else:
            # 其他状态
            response = {
                'state': task.state,
                'status': str(task.info),
                'current': 0,
                'total': 100
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        return jsonify({
            'state': 'UNKNOWN',
            'status': '无法查询任务状态',
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """健康检查"""
    try:
        db_status = db.check_connection()
        cache_status = cache_service.is_connected()
        
        # 获取性能信息
        with processing_lock:
            current_processing_count = len(current_processing_users)
            processing_users_list = list(current_processing_users)
        
        health_info = {
            'status': 'healthy' if db_status else 'unhealthy',
            'scheduler_running': scheduler.running if scheduler else False,
            'database_connected': db_status,
            'cache_connected': cache_status,
            'current_time': datetime.now().isoformat(),
            'version': '1.0.0',
            'performance': {
                'current_processing_users': current_processing_count,
                'max_concurrent_users': MAX_CONCURRENT_USERS,
                'processing_user_ids': processing_users_list
            }
        }
        
        # 添加缓存统计信息
        if cache_status:
            cache_stats = cache_service.get_cache_stats()
            health_info['cache_stats'] = cache_stats
        
        return jsonify(health_info)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'current_time': datetime.now().isoformat()
        })

@app.route('/api/system/performance')
@auth_service.require_admin
def system_performance():
    """系统性能监控（仅管理员）"""
    try:
        with processing_lock:
            current_processing_count = len(current_processing_users)
            processing_users_list = list(current_processing_users)
        
        # 获取调度器信息
        jobs_info = []
        if scheduler.running:
            for job in scheduler.get_jobs():
                jobs_info.append({
                    'id': job.id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'func_name': job.func.__name__ if hasattr(job, 'func') else 'unknown'
                })
        
        return jsonify({
            'current_processing': {
                'count': current_processing_count,
                'user_ids': processing_users_list,
                'max_concurrent': MAX_CONCURRENT_USERS
            },
            'scheduler': {
                'running': scheduler.running,
                'jobs_count': len(jobs_info),
                'jobs': jobs_info
            },
            'database': {
                'connected': db.check_connection()
            }
        })
        
    except Exception as e:
        logger.error(f"获取系统性能信息失败: {e}")
        return jsonify({'error': '获取性能信息失败'}), 500

@app.route('/api/stats')

@app.route('/api/user/email-accounts')
@auth_service.require_login
def get_user_email_accounts():
    """获取用户的邮箱账户列表API"""
    try:
        user = auth_service.get_current_user()
        accounts = db.get_user_email_accounts(user['id'])
        
        # 过滤敏感信息
        safe_accounts = []
        for account in accounts:
            safe_account = {
                'id': account['id'],
                'email': account['email'],
                'provider': account['provider'],
                'is_active': account['is_active']
            }
            safe_accounts.append(safe_account)
        
        return jsonify({
            'success': True,
            'accounts': safe_accounts
        })
        
    except Exception as e:
        logger.error(f"获取用户邮箱账户失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取邮箱账户失败: {str(e)}'
        }), 500

def api_stats():
    """获取系统统计信息"""
    try:
        stats = db.get_system_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取统计信息时出错: {e}")
        return jsonify({'error': '获取统计信息失败'}), 500

@app.route('/api/emails/<int:email_id>')
@auth_service.require_login
def get_email_detail(email_id):
    """获取邮件详情"""
    try:
        user = auth_service.get_current_user()
        email_detail = db.get_email_by_id(email_id)
        
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        return jsonify(email_detail)
        
    except Exception as e:
        logger.error(f"获取邮件详情时出错: {e}")
        return jsonify({'error': '获取邮件详情失败'}), 500

@app.route('/api/emails/<int:email_id>/classification', methods=['PUT'])
@auth_service.require_login
def update_email_classification(email_id):
    """
    更新邮件分类（用户手动修改）
    支持智能学习：记录用户行为以生成规则建议
    """
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        data = request.json
        old_category = data.get('old_category')
        new_category = data.get('new_category')
        old_importance = data.get('old_importance')
        new_importance = data.get('new_importance')
        
        # 1. 获取邮件信息
        email = db.get_email_by_id(email_id)
        if not email or email.get('user_id') != user_id:
            return jsonify({'success': False, 'error': '邮件不存在或无权限'}), 404
        
        # 2. 更新邮件分类
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE emails 
                SET category = ?, importance = ?, 
                    classification_method = 'manual',
                    updated_at = ?
                WHERE id = ? AND user_id = ?
            ''', (new_category, new_importance, 
                  datetime.now().isoformat(), 
                  email_id, user_id))
            conn.commit()
        
        # 3. 记录用户行为（关键步骤！用于智能学习）
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO manual_classification_history 
                    (user_id, email_id, original_category, new_category,
                     original_importance, new_importance, 
                     sender, subject, action_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, email_id, old_category, new_category,
                      old_importance, new_importance,
                      email['sender'], email['subject'],
                      'manual_change', datetime.now().isoformat()))
                conn.commit()
            
            logger.info(f"用户 {user_id} 手动修改邮件 {email_id} 分类: {old_category} -> {new_category}")
        except Exception as e:
            logger.error(f"记录用户行为失败（非致命）: {e}")
        
        # 4. 检查是否需要触发智能建议生成（可选，后台执行）
        # 这里可以异步触发，不阻塞用户操作
        
        return jsonify({
            'success': True,
            'message': '分类已更新'
        })
        
    except Exception as e:
        logger.error(f"更新邮件分类失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/emails/<int:email_id>/reprocess', methods=['POST'])
def reprocess_email(email_id):
    """重新处理邮件摘要"""
    try:
        email_detail = db.get_email_by_id(email_id)
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 重新生成AI摘要
        ai_summary = ai_client.summarize_email(email_detail)
        
        # 更新数据库
        success = db.update_email_summary(email_id, ai_summary)
        if success:
            return jsonify({'success': True, 'ai_summary': ai_summary})
        else:
            return jsonify({'error': '更新摘要失败'}), 500
            
    except Exception as e:
        logger.error(f"重新处理邮件时出错: {e}")
        return jsonify({'error': '重新处理失败'}), 500

@app.route('/api/emails/<int:email_id>/translate', methods=['POST'])
@auth_service.require_login
def translate_email_summary(email_id):
    """翻译邮件摘要为中文"""
    try:
        user = auth_service.get_current_user()
        email_detail = db.get_email_by_id(email_id)
        
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        # 检查翻译服务是否可用
        if not translation_service.is_translation_available():
            return jsonify({'error': '翻译服务不可用，请检查GLM API配置'}), 503
        
        # 获取当前摘要
        current_summary = email_detail.get('ai_summary') or email_detail.get('summary', '')
        
        if not current_summary:
            return jsonify({'error': '邮件没有摘要可以翻译'}), 400
        
        # 翻译摘要
        translated_summary = translation_service.translate_to_chinese(current_summary)
        
        if translated_summary == current_summary:
            return jsonify({
                'success': True,
                'message': '摘要已经是中文或无需翻译',
                'summary': current_summary,
                'translated': False
            })
        
        # 更新数据库中的摘要
        db.update_email_summary(email_id, translated_summary)
        
        logger.info(f"邮件摘要翻译完成: {email_id}")
        
        return jsonify({
            'success': True,
            'message': '摘要翻译完成',
            'summary': translated_summary,
            'original_summary': current_summary,
            'translated': True
        })
        
    except Exception as e:
        logger.error(f"翻译邮件摘要时出错: {e}")
        return jsonify({'error': '翻译失败'}), 500

@app.route('/api/emails/batch-translate', methods=['POST'])
@auth_service.require_login
def batch_translate_email_summaries():
    """批量翻译邮件摘要为中文"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json() or {}
        email_ids = data.get('email_ids', [])
        
        if not email_ids:
            return jsonify({'error': '请选择要翻译的邮件'}), 400
        
        # 检查翻译服务是否可用
        if not translation_service.is_translation_available():
            return jsonify({'error': '翻译服务不可用，请检查GLM API配置'}), 503
        
        success_count = 0
        failed_count = 0
        results = []
        
        for email_id in email_ids:
            try:
                email_detail = db.get_email_by_id(email_id)
                
                if not email_detail or email_detail.get('user_id') != user['id']:
                    failed_count += 1
                    results.append({
                        'email_id': email_id,
                        'success': False,
                        'error': '邮件不存在或没有权限'
                    })
                    continue
                
                # 获取当前摘要
                current_summary = email_detail.get('ai_summary') or email_detail.get('summary', '')
                
                if not current_summary:
                    failed_count += 1
                    results.append({
                        'email_id': email_id,
                        'success': False,
                        'error': '邮件没有摘要可以翻译'
                    })
                    continue
                
                # 翻译摘要
                translated_summary = translation_service.translate_to_chinese(current_summary)
                
                if translated_summary != current_summary:
                    # 更新数据库中的摘要
                    db.update_email_summary(email_id, translated_summary)
                    success_count += 1
                    results.append({
                        'email_id': email_id,
                        'success': True,
                        'translated': True,
                        'summary': translated_summary
                    })
                else:
                    success_count += 1
                    results.append({
                        'email_id': email_id,
                        'success': True,
                        'translated': False,
                        'message': '摘要已经是中文或无需翻译'
                    })
                    
            except Exception as e:
                logger.error(f"翻译邮件 {email_id} 摘要时出错: {e}")
                failed_count += 1
                results.append({
                    'email_id': email_id,
                    'success': False,
                    'error': '翻译失败'
                })
        
        logger.info(f"批量翻译完成: 成功 {success_count}, 失败 {failed_count}")
        
        return jsonify({
            'success': True,
            'message': f'批量翻译完成: 成功 {success_count}, 失败 {failed_count}',
            'summary': {
                'total': len(email_ids),
                'success': success_count,
                'failed': failed_count
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"批量翻译邮件摘要时出错: {e}")
        return jsonify({'error': '批量翻译失败'}), 500

@app.route('/api/translate-text', methods=['POST'])
@auth_service.require_login
def translate_text():
    """通用文本翻译API"""
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': '未提供要翻译的文本'}), 400
        
        # 检查翻译服务是否可用
        if not translation_service.is_translation_available():
            return jsonify({'error': '翻译服务不可用，请检查GLM API配置'}), 503
        
        # 翻译文本
        translated_text = translation_service.translate_to_chinese(text)
        
        if translated_text == text:
            return jsonify({
                'success': True,
                'message': '文本已经是中文或无需翻译',
                'original_text': text,
                'translated_text': text,
                'translated': False
            })
        else:
            logger.info(f"文本翻译完成: {len(text)} 字符")
            return jsonify({
                'success': True,
                'message': '文本翻译完成',
                'original_text': text,
                'translated_text': translated_text,
                'translated': True
            })
            
    except Exception as e:
        logger.error(f"翻译文本时出错: {e}")
        return jsonify({'error': '翻译失败'}), 500

@app.route('/api/emails/<int:email_id>/translate-body', methods=['POST'])
@auth_service.require_login
def translate_email_body(email_id):
    """翻译邮件正文API"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json() or {}
        target_language = data.get('target_language', 'chinese')  # chinese 或 english
        
        # 获取邮件详情
        email_detail = db.get_email_by_id(email_id)
        
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        # 首先检查数据库中是否已有翻译结果
        existing_translation = db.get_email_translation(email_id, target_language)
        
        if existing_translation:
            logger.info(f"使用数据库中的翻译结果: email_id={email_id}, language={target_language}")
            return jsonify({
                'success': True,
                'message': f'邮件正文翻译完成（{target_language}）',
                'original_body': email_detail.get('body', ''),
                'translated_body': existing_translation,
                'target_language': target_language,
                'translated': True,
                'from_cache': True  # 标识来自数据库缓存
            })
        
        # 检查翻译服务是否可用
        if not translation_service.is_translation_available():
            return jsonify({'error': '翻译服务不可用，请检查GLM API配置'}), 503
        
        # 获取邮件正文
        email_body = email_detail.get('body', '')
        
        if not email_body:
            return jsonify({'error': '邮件正文为空'}), 400
        
        # 根据目标语言进行翻译
        if target_language == 'chinese':
            translated_body = translation_service.smart_translate_to_chinese(email_body)
        elif target_language == 'english':
            translated_body = translation_service.smart_translate_to_english(email_body)
        else:
            return jsonify({'error': '不支持的目标语言'}), 400
        
        # 保存翻译结果到数据库
        if translated_body != email_body:
            save_success = db.save_email_translation(email_id, target_language, translated_body)
            if save_success:
                logger.info(f"翻译结果已保存到数据库: email_id={email_id}, language={target_language}")
            else:
                logger.warning(f"翻译结果保存失败: email_id={email_id}, language={target_language}")
        
        logger.info(f"邮件正文翻译完成: {email_id}, 目标语言: {target_language}")
        
        return jsonify({
            'success': True,
            'message': f'邮件正文翻译完成（{target_language}）',
            'original_body': email_body,
            'translated_body': translated_body,
            'target_language': target_language,
            'translated': translated_body != email_body,
            'from_cache': False  # 标识为新翻译
        })
        
    except Exception as e:
        logger.error(f"翻译邮件正文时出错: {e}")
        return jsonify({'error': '翻译失败'}), 500

@app.route('/api/emails/<int:email_id>/clear-translations', methods=['POST'])
@auth_service.require_login
def clear_email_translations(email_id):
    """清除邮件的所有翻译结果"""
    try:
        user = auth_service.get_current_user()
        
        # 获取邮件详情
        email_detail = db.get_email_by_id(email_id)
        
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        # 清除翻译结果
        success = db.clear_email_translations(email_id)
        
        if success:
            logger.info(f"邮件翻译已清除: email_id={email_id}, user_id={user['id']}")
            return jsonify({
                'success': True,
                'message': '翻译结果已清除'
            })
        else:
            return jsonify({'error': '清除翻译失败'}), 500
        
    except Exception as e:
        logger.error(f"清除邮件翻译时出错: {e}")
        return jsonify({'error': '清除翻译失败'}), 500

@app.route('/api/emails/<int:email_id>/attachments/<path:attachment_filename>')
@auth_service.require_login
def download_attachment(email_id, attachment_filename):
    """下载邮件附件"""
    try:
        user = auth_service.get_current_user()
        
        # URL解码文件名，处理特殊字符
        from urllib.parse import unquote
        decoded_filename = unquote(attachment_filename)
        
        # 获取邮件详情
        email_detail = db.get_email_by_id(email_id)
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        # 获取附件列表
        attachments = email_detail.get('attachments', [])
        if not attachments:
            return jsonify({'error': '该邮件没有附件'}), 404
        
        # 查找指定的附件
        target_attachment = None
        for attachment in attachments:
            if attachment.get('stored_filename') == decoded_filename:
                target_attachment = attachment
                break
        
        if not target_attachment:
            logger.error(f"附件不存在: {decoded_filename}, 可用附件: {[a.get('stored_filename') for a in attachments]}")
            return jsonify({'error': '附件不存在'}), 404
        
        # 构建附件文件路径
        user_attachment_dir = os.path.join('email_attachments', f'user_{user["id"]}')
        file_path = os.path.join(user_attachment_dir, decoded_filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"附件文件不存在: {file_path}")
            return jsonify({'error': '附件文件不存在'}), 404
        
        # 发送文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=target_attachment.get('original_filename', decoded_filename),
            mimetype=target_attachment.get('content_type', 'application/octet-stream')
        )
        
    except Exception as e:
        logger.error(f"下载附件时出错: {e}")
        return jsonify({'error': '下载附件失败'}), 500

@app.route('/api/emails/<int:email_id>/attachments/download-all')
@auth_service.require_login
def download_all_attachments(email_id):
    """批量下载邮件的所有附件（打包成ZIP）"""
    try:
        user = auth_service.get_current_user()
        
        # 获取邮件详情
        email_detail = db.get_email_by_id(email_id)
        if not email_detail:
            return jsonify({'error': '邮件不存在'}), 404
        
        # 检查邮件是否属于当前用户
        if email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限'}), 404
        
        # 获取附件列表
        attachments = email_detail.get('attachments', [])
        if not attachments:
            return jsonify({'error': '该邮件没有附件'}), 404
        
        # 构建用户附件目录路径
        user_attachment_dir = os.path.join('email_attachments', f'user_{user["id"]}')
        
        # 创建临时ZIP文件
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                added_files = 0
                
                for attachment in attachments:
                    stored_filename = attachment.get('stored_filename')
                    original_filename = attachment.get('original_filename', stored_filename)
                    
                    if not stored_filename:
                        continue
                    
                    file_path = os.path.join(user_attachment_dir, stored_filename)
                    
                    # 检查文件是否存在
                    if os.path.exists(file_path):
                        # 添加文件到ZIP，使用原始文件名
                        zipf.write(file_path, original_filename)
                        added_files += 1
                        logger.info(f"添加附件到ZIP: {original_filename}")
                    else:
                        logger.warning(f"附件文件不存在: {file_path}")
                
                if added_files == 0:
                    os.unlink(temp_zip.name)
                    return jsonify({'error': '没有可用的附件文件'}), 404
            
            # 生成下载文件名
            email_subject = email_detail.get('subject', 'Unknown')[:50]  # 限制长度
            # 清理文件名中的特殊字符
            safe_subject = "".join(c for c in email_subject if c.isalnum() or c in (' ', '-', '_')).strip()
            download_filename = f"邮件附件_{safe_subject}_{email_id}.zip"
            
            # 发送ZIP文件
            logger.info(f"批量下载附件: 邮件ID={email_id}, 文件数={added_files}")
            
            # 使用Flask的send_file直接发送，让操作系统处理临时文件清理
            # 或者使用定时清理机制
            response = send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=download_filename,
                mimetype='application/zip'
            )
            
            # 延迟删除临时文件（给下载一些时间）
            import threading
            def delayed_cleanup():
                import time
                time.sleep(10)  # 等待10秒让下载完成
                try:
                    os.unlink(temp_zip.name)
                    logger.debug(f"清理临时ZIP文件: {temp_zip.name}")
                except:
                    pass
            
            # 在后台线程中清理
            cleanup_thread = threading.Thread(target=delayed_cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
            return response
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_zip.name)
            except:
                pass
            raise e
        
    except Exception as e:
        logger.error(f"批量下载附件时出错: {e}")
        return jsonify({'error': '批量下载失败'}), 500

@app.route('/api/user/stats')
@auth_service.require_login
def api_user_stats():
    """获取当前用户统计信息"""
    try:
        user = auth_service.get_current_user()
        stats = db.get_user_stats(user['id'])
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取用户统计信息时出错: {e}")
        return jsonify({'error': '获取统计信息失败'}), 500

@app.route('/api/user/change-password', methods=['POST'])
@auth_service.require_login
def change_password():
    """修改用户密码"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not all([old_password, new_password, confirm_password]):
            return jsonify({'error': '请填写所有必需字段'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': '两次输入的新密码不一致'}), 400
        
        success, message = auth_service.change_password(user['id'], old_password, new_password)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"修改密码时出错: {e}")
        return jsonify({'error': '系统错误，请稍后重试'}), 500

@app.route('/api/user/update-profile', methods=['POST'])
@auth_service.require_login
def update_profile():
    """更新用户个人资料"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        email = data.get('email', '').strip() if data.get('email') else None
        full_name = data.get('full_name', '').strip() if data.get('full_name') else None
        
        success, message = auth_service.update_profile(user['id'], email, full_name)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"更新个人资料时出错: {e}")
        return jsonify({'error': '系统错误，请稍后重试'}), 500

@app.route('/api/user/schedule-status', methods=['GET'])
@auth_service.require_login
def get_schedule_status():
    """获取用户的定时任务状态"""
    try:
        user = auth_service.get_current_user()
        status = scheduler_manager.get_user_schedule_status(user['id'])
        return jsonify(status)
    except Exception as e:
        logger.error(f"获取定时任务状态时出错: {e}")
        return jsonify({'error': '获取状态失败'}), 500

@app.route('/api/user/config', methods=['GET', 'POST'])
@auth_service.require_login
def handle_user_config():
    """处理用户配置的GET和POST请求"""
    if request.method == 'GET':
        # 获取用户配置
        try:
            user = auth_service.get_current_user()
            configs = db.get_user_configs(user['id'])
            
            # 添加调度状态信息
            schedule_status = scheduler_manager.get_user_schedule_status(user['id'])
            configs['schedule_status'] = schedule_status
            
            return jsonify(configs)
        except Exception as e:
            logger.error(f"获取用户配置时出错: {e}")
            return jsonify({'error': '获取配置失败'}), 500
    
    else:  # POST
        return save_user_config()

def save_user_config():
    """保存用户配置"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        # 用户可配置的项目
        allowed_user_configs = [
            'check_interval_minutes',
            'max_emails_per_account',
            'email_body_max_length',
            'email_subject_max_length',
            'check_days_back',
            'duplicate_check_days',
            # 新增调度配置项
            'schedule_type',
            'cron_hours',
            'cron_minutes',
            'custom_rule',
            'custom_minute',
            'n_hours'
        ]
        
        saved_count = 0
        schedule_config_updated = False
        
        for key, value in data.items():
            if key in allowed_user_configs:
                if db.set_user_config(user['id'], key, str(value)):
                    saved_count += 1
                    # 检查是否更新了调度相关配置
                    if key in ['check_interval_minutes', 'schedule_type', 'cron_hours', 'cron_minutes', 'custom_rule', 'custom_minute', 'n_hours']:
                        schedule_config_updated = True
        
        # 如果调度配置被更新，重新创建用户的定时任务
        if schedule_config_updated:
            try:
                schedule_config = scheduler_manager._get_user_schedule_config(user['id'], db)
                scheduler_manager.create_user_schedule(user['id'], schedule_config)
                logger.info(f"用户 {user['id']} 的定时任务已更新")
            except Exception as e:
                logger.error(f"更新用户 {user['id']} 定时任务失败: {e}")
        
        return jsonify({'success': True, 'message': f'保存了 {saved_count} 项配置'})
        
    except Exception as e:
        logger.error(f"保存用户配置时出错: {e}")
        return jsonify({'error': '保存配置失败'}), 500

@app.route('/api/system/config', methods=['POST'])
@auth_service.require_admin
def save_system_config():
    """保存系统配置（仅管理员）"""
    try:
        data = request.get_json()
        
        # 系统级配置项目
        allowed_system_configs = [
            'ai_provider',
            'glm_api_key',
            'glm_model',
            'openai_api_key', 
            'openai_model',
            'summary_max_length',
            'summary_temperature'
        ]
        
        saved_count = 0
        for key, value in data.items():
            if key in allowed_system_configs:
                if db.set_system_config(key, str(value)):
                    saved_count += 1
        
        return jsonify({'success': True, 'message': f'保存了 {saved_count} 项系统配置'})
        
    except Exception as e:
        logger.error(f"保存系统配置时出错: {e}")
        return jsonify({'error': '保存配置失败'}), 500

@app.route('/api/user/clear-emails', methods=['POST'])
@auth_service.require_login
def clear_user_emails():
    """清空用户所有邮件（物理删除，保留邮件账户）"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 获取确认码
        data = request.get_json() or {}
        confirmation = data.get('confirmation', '')
        
        # 验证确认码（必须是"CLEAR_ALL_EMAILS"）
        if confirmation != 'CLEAR_ALL_EMAILS':
            return jsonify({
                'success': False, 
                'error': '确认码不正确，请输入 CLEAR_ALL_EMAILS'
            }), 400
        
        # 执行清空操作
        success, deleted_count = db.clear_user_emails(user_id)
        
        if success:
            logger.info(f"用户 {user['username']} (ID: {user_id}) 清空了所有邮件，共删除 {deleted_count} 封")
            return jsonify({
                'success': True,
                'message': f'成功清空 {deleted_count} 封邮件及其附件',
                'deleted_count': deleted_count
            })
        else:
            return jsonify({
                'success': False,
                'error': '清空邮件失败，请稍后重试'
            }), 500
        
    except Exception as e:
        logger.error(f"清空用户邮件时出错: {e}")
        return jsonify({
            'success': False,
            'error': '系统错误，请稍后重试'
        }), 500

@app.route('/api/user/clear-digests', methods=['POST'])
@auth_service.require_login
def clear_user_digests():
    """清空用户所有简报（物理删除）"""
    try:
        user = auth_service.get_current_user()
        user_id = user['id']
        
        # 获取确认码
        data = request.get_json() or {}
        confirmation = data.get('confirmation', '')
        
        # 验证确认码（必须是"CLEAR_ALL_DIGESTS"）
        if confirmation != 'CLEAR_ALL_DIGESTS':
            return jsonify({
                'success': False, 
                'error': '确认码不正确，请输入 CLEAR_ALL_DIGESTS'
            }), 400
        
        # 执行清空操作
        success, deleted_count = db.clear_user_digests(user_id)
        
        if success:
            logger.info(f"用户 {user['username']} (ID: {user_id}) 清空了所有简报，共删除 {deleted_count} 份")
            return jsonify({
                'success': True,
                'message': f'成功清空 {deleted_count} 份简报',
                'deleted_count': deleted_count
            })
        else:
            return jsonify({
                'success': False,
                'error': '清空简报失败，请稍后重试'
            }), 500
        
    except Exception as e:
        logger.error(f"清空用户简报时出错: {e}")
        return jsonify({
            'success': False,
            'error': '系统错误，请稍后重试'
        }), 500

@app.route('/api/digests')
@auth_service.require_login
def api_user_digests():
    """获取用户简报列表API"""
    try:
        user = auth_service.get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        digests, total = db.get_user_digests_paginated(user['id'], page=page, per_page=per_page)
        
        return jsonify({
            'digests': digests,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户简报列表时出错: {e}")
        return jsonify({'error': '获取简报列表失败'}), 500

@app.route('/api/digests/<int:digest_id>')
@auth_service.require_login
def api_digest_detail(digest_id):
    """获取简报详情API"""
    try:
        user = auth_service.get_current_user()
        digest = db.get_digest_by_id(digest_id, user['id'])
        
        if digest:
            return jsonify(digest)
        else:
            return jsonify({'error': '简报不存在或您没有权限查看'}), 404
            
    except Exception as e:
        logger.error(f"获取简报详情时出错: {e}")
        return jsonify({'error': '获取简报详情失败'}), 500

@app.route('/api/accounts/refresh-stats', methods=['POST'])
@auth_service.require_login
def refresh_account_stats():
    """刷新邮箱账户统计信息"""
    try:
        user = auth_service.get_current_user()
        user_accounts = db.get_user_email_accounts(user['id'])
        
        updated_count = 0
        for account in user_accounts:
            # 计算该邮箱的邮件数量
            email_count = db.get_account_email_count(user['id'], account['email'])
            
            # 更新统计信息
            if db.update_email_account_stats(user['id'], account['email'], email_count):
                updated_count += 1
        
        return jsonify({
            'success': True, 
            'message': f'已更新 {updated_count} 个邮箱账户的统计信息'
        })
        
    except Exception as e:
        logger.error(f"刷新邮箱账户统计时出错: {e}")
        return jsonify({'error': '刷新统计信息失败'}), 500

@app.route('/api/emails/<int:email_id>/delete', methods=['POST'])
@auth_service.require_login
def soft_delete_email(email_id):
    """软删除邮件（标记为删除）"""
    try:
        user = auth_service.get_current_user()
        
        # 验证邮件属于当前用户
        email_detail = db.get_email_by_id(email_id)
        if not email_detail or email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限删除'}), 404
        
        # 软删除（标记为删除状态）
        success = db.soft_delete_email(email_id, user['id'])
        if success:
            return jsonify({'success': True, 'message': '邮件已删除'})
        else:
            return jsonify({'error': '删除失败'}), 500
            
    except Exception as e:
        logger.error(f"软删除邮件时出错: {e}")
        return jsonify({'error': '删除失败'}), 500

@app.route('/api/emails/<int:email_id>/purge', methods=['POST'])
@auth_service.require_login
def purge_email(email_id):
    """彻底删除邮件（物理删除）"""
    try:
        user = auth_service.get_current_user()
        
        # 验证邮件属于当前用户
        email_detail = db.get_email_by_id(email_id)
        if not email_detail or email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限删除'}), 404
        
        # 物理删除
        success = db.purge_email(email_id, user['id'])
        if success:
            return jsonify({'success': True, 'message': '邮件已彻底删除'})
        else:
            return jsonify({'error': '删除失败'}), 500
            
    except Exception as e:
        logger.error(f"彻底删除邮件时出错: {e}")
        return jsonify({'error': '删除失败'}), 500

@app.route('/api/emails/batch-delete', methods=['POST'])
@auth_service.require_login
def batch_delete_emails():
    """批量删除邮件"""
    try:
        user = auth_service.get_current_user()
        data = request.get_json()
        
        email_ids = data.get('email_ids', [])
        delete_type = data.get('type', 'soft')  # soft 或 purge
        
        if not email_ids:
            return jsonify({'error': '请选择要删除的邮件'}), 400
        
        success_count = 0
        for email_id in email_ids:
            try:
                if delete_type == 'purge':
                    success = db.purge_email(email_id, user['id'])
                else:
                    success = db.soft_delete_email(email_id, user['id'])
                
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"批量删除邮件 {email_id} 失败: {e}")
                continue
        
        message = f"成功删除 {success_count}/{len(email_ids)} 封邮件"
        return jsonify({'success': True, 'message': message, 'deleted_count': success_count})
        
    except Exception as e:
        logger.error(f"批量删除邮件时出错: {e}")
        return jsonify({'error': '批量删除失败'}), 500

@app.route('/api/emails/<int:email_id>/restore', methods=['POST'])
@auth_service.require_login
def restore_email(email_id):
    """恢复软删除的邮件"""
    try:
        user = auth_service.get_current_user()
        
        # 验证邮件属于当前用户
        email_detail = db.get_email_by_id(email_id)
        if not email_detail or email_detail.get('user_id') != user['id']:
            return jsonify({'error': '邮件不存在或您没有权限恢复'}), 404
        
        # 检查邮件是否已删除
        if not email_detail.get('deleted'):
            return jsonify({'error': '邮件未被删除，无需恢复'}), 400
        
        # 恢复邮件
        success = db.restore_email(email_id, user['id'])
        if success:
            return jsonify({'success': True, 'message': '邮件已恢复'})
        else:
            return jsonify({'error': '恢复失败'}), 500
            
    except Exception as e:
        logger.error(f"恢复邮件时出错: {e}")
        return jsonify({'error': '恢复失败'}), 500

@app.route('/recycle_bin')
@auth_service.require_login
def recycle_bin():
    """回收站页面"""
    try:
        user = auth_service.get_current_user()
        
        # 获取筛选参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        provider = request.args.get('provider', '').strip()
        processed = request.args.get('processed', '').strip()
        
        # 获取已删除邮件列表
        emails, total = db.get_user_deleted_emails_filtered(
            user['id'], page, per_page, search, category, provider, processed
        )
        
        # 计算分页信息
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        # 获取筛选选项
        categories = ['工作', '财务', '社交', '购物', '资讯', '通知', '其他']
        providers = ['Gmail', '126', '163', 'QQ', 'Hotmail', 'Yahoo', 'Outlook']
        
        return render_template('recycle_bin.html',
                             emails=emails,
                             total=total,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             has_prev=has_prev,
                             has_next=has_next,
                             search=search,
                             category=category,
                             provider=provider,
                             processed=processed,
                             categories=categories,
                             providers=providers)
        
    except Exception as e:
        logger.error(f"获取回收站页面时出错: {e}")
        flash('获取回收站失败', 'error')
        return redirect(url_for('index'))

# 认证相关路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('请填写用户名和密码', 'error')
            return render_template('auth/login.html')
        
        success, message, user = auth_service.login_user(username_or_email, password)
        if success:
            flash(f'欢迎回来，{user["username"]}！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash(message, 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # 验证输入
        if not all([username, email, password, confirm_password]):
            flash('请填写所有必需字段', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/register.html')
        
        success, message, user_id = auth_service.register_user(username, email, password, full_name)
        if success and user_id:
            # 为新用户创建默认定时任务
            try:
                check_interval = Config.CHECK_INTERVAL_MINUTES
                scheduler_manager.create_user_schedule(user_id, check_interval)
                logger.info(f"已为新用户 {user_id} 创建定时任务: {check_interval} 分钟")
            except Exception as e:
                logger.error(f"为新用户 {user_id} 创建定时任务失败: {e}")
            
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    """用户登出"""
    auth_service.logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
@auth_service.require_login
def profile():
    """用户个人资料"""
    user = auth_service.get_current_user()
    return render_template('auth/profile.html', user=user)

@app.route('/digests')
@auth_service.require_login
def digests_history():
    """简报历史页面"""
    try:
        user = auth_service.get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 获取用户的历史简报
        digests, total = db.get_user_digests_paginated(user['id'], page=page, per_page=per_page)
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        return render_template('digests_history.html', digests=digests, pagination=pagination, user=user)
        
    except Exception as e:
        logger.error(f"加载简报历史时出错: {e}")
        flash('加载简报历史时出错，请稍后重试', 'error')
        return render_template('digests_history.html', digests=[], pagination={}, user=None)

@app.route('/digests/<int:digest_id>')
@auth_service.require_login
def digest_detail(digest_id):
    """简报详情页面"""
    try:
        user = auth_service.get_current_user()
        digest = db.get_digest_by_id(digest_id, user['id'])
        
        if not digest:
            flash('简报不存在或您没有权限查看', 'error')
            return redirect(url_for('digests_history'))
        
        return render_template('digest_detail.html', digest=digest, user=user)
        
    except Exception as e:
        logger.error(f"加载简报详情时出错: {e}")
        flash('加载简报详情时出错，请稍后重试', 'error')
        return redirect(url_for('digests_history'))

def init_system():
    """初始化系统"""
    try:
        # 清理过期会话
        auth_service.cleanup_sessions()
        
        # 检查是否有管理员账户，如果没有则创建默认管理员
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = 1')
            admin_count = cursor.fetchone()['count']
            
            if admin_count == 0:
                # 创建默认管理员账户
                admin_password = "admin123"  # 生产环境应该使用更强的密码
                password_hash = auth_service.hash_password(admin_password)
                
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, full_name, is_admin)
                    VALUES (?, ?, ?, ?, ?)
                ''', ("admin", "admin@email.wyg.life", password_hash, "系统管理员", True))
                
                conn.commit()
                logger.info("创建默认管理员账户: admin / admin123")
        
        # 初始化系统配置
        try:
            # 如果环境变量中有GLM API密钥，保存到数据库
            if Config.GLM_API_KEY and Config.GLM_API_KEY != 'your_glm_api_key_here':
                if not db.get_system_config('glm_api_key'):
                    db.set_system_config('glm_api_key', Config.GLM_API_KEY)
                    logger.info("GLM API密钥已保存到数据库")
            
            # 设置其他默认系统配置
            if not db.get_system_config('ai_provider'):
                db.set_system_config('ai_provider', Config.AI_PROVIDER)
            if not db.get_system_config('glm_model'):
                db.set_system_config('glm_model', Config.GLM_MODEL)
            if not db.get_system_config('summary_max_length'):
                db.set_system_config('summary_max_length', str(Config.SUMMARY_MAX_LENGTH))
            if not db.get_system_config('summary_temperature'):
                db.set_system_config('summary_temperature', str(Config.SUMMARY_TEMPERATURE))
                
        except Exception as e:
            logger.error(f"初始化系统配置失败: {e}")
                
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")

def start_scheduler():
    """启动定时任务"""
    if not scheduler.running:
        try:
            # 添加会话清理任务
            scheduler.add_job(
                func=auth_service.cleanup_sessions,
                trigger="interval",
                hours=1,  # 每小时清理一次过期会话
                id='session_cleanup',
                max_instances=1
            )
            
            # 添加自动缓存清理任务
            scheduler.add_job(
                func=auto_cache_cleaner.run_daily_cleanup,
                trigger="cron",
                hour=2,  # 每天凌晨2点执行
                minute=0,
                id='cache_cleanup',
                max_instances=1
            )
            
            # 添加旧通知清理任务
            scheduler.add_job(
                func=lambda: db.clear_old_notifications(days=30),
                trigger="cron",
                hour=3,  # 每天凌晨3点执行
                minute=0,
                id='notification_cleanup',
                max_instances=1
            )
            
            # 启动调度器
            scheduler.start()
            logger.info("定时任务调度器已启动")
            
            # 为所有活跃用户创建个性化定时任务
            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE is_active = 1')
                    user_ids = [row['id'] for row in cursor.fetchall()]
                
                for user_id in user_ids:
                    try:
                        # 获取用户的调度配置
                        schedule_config = scheduler_manager._get_user_schedule_config(user_id, db)
                        
                        # 为用户创建定时任务
                        scheduler_manager.create_user_schedule(user_id, schedule_config)
                    except Exception as e:
                        logger.error(f"为用户 {user_id} 创建定时任务失败: {e}")
                        
            except Exception as e:
                logger.error(f"初始化用户定时任务失败: {e}")
                
        except Exception as e:
            logger.error(f"启动定时任务失败: {e}")

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message='服务器内部错误'), 500

# ==================== 缓存管理API ====================

@app.route('/api/cache/health')
@auth_service.require_admin
def cache_health():
    """缓存健康检查（仅管理员）"""
    try:
        health_info = cache_manager.get_cache_health()
        return jsonify(health_info)
    except Exception as e:
        logger.error(f"缓存健康检查失败: {e}")
        return jsonify({
            'success': False,
            'message': f'缓存健康检查失败: {str(e)}'
        })

@app.route('/api/cache/user/<int:user_id>/warm-up', methods=['POST'])
@auth_service.require_admin
def warm_up_user_cache(user_id):
    """预热用户缓存（仅管理员）"""
    try:
        result = cache_manager.warm_up_user_cache(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"用户缓存预热失败: {e}")
        return jsonify({
            'success': False,
            'message': f'缓存预热失败: {str(e)}'
        })

@app.route('/api/cache/user/<int:user_id>/clear', methods=['DELETE'])
@auth_service.require_admin
def clear_user_cache(user_id):
    """清除用户缓存（仅管理员）"""
    try:
        result = cache_manager.clear_user_cache(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"清除用户缓存失败: {e}")
        return jsonify({
            'success': False,
            'message': f'缓存清除失败: {str(e)}'
        })

@app.route('/api/cache/keys')
@auth_service.require_admin
def get_cache_keys():
    """获取缓存键信息（仅管理员）"""
    try:
        pattern = request.args.get('pattern', '*')
        result = cache_manager.get_cache_keys_info(pattern)
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取缓存键失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取缓存键失败: {str(e)}'
        })

@app.route('/api/cache/optimize')
@auth_service.require_admin
def cache_optimization():
    """缓存优化建议（仅管理员）"""
    try:
        result = cache_manager.optimize_cache()
        return jsonify(result)
    except Exception as e:
        logger.error(f"缓存优化分析失败: {e}")
        return jsonify({
            'success': False,
            'message': f'缓存优化分析失败: {str(e)}'
        })

# 用户级缓存管理API
@app.route('/api/my-cache/clear', methods=['POST'])
@auth_service.require_login
def clear_my_cache():
    """清除当前用户缓存"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({'success': False, 'message': '用户未登录'})
        
        result = cache_manager.clear_user_cache(user['id'])
        return jsonify(result)
    except Exception as e:
        logger.error(f"清除用户缓存失败: {e}")
        return jsonify({
            'success': False,
            'message': f'缓存清除失败: {str(e)}'
        })

# 新的缓存管理API端点
@app.route('/api/cache/stats')
@auth_service.require_login
def get_cache_stats():
    """获取缓存统计信息"""
    try:
        if not cache_service or not cache_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Redis缓存未连接'
            })
        
        # 获取各类缓存的数量
        email_keys = cache_service.redis_client.keys('emails:*')
        stats_keys = cache_service.redis_client.keys('stats:*')
        digest_keys = cache_service.redis_client.keys('digests:*')
        config_keys = cache_service.redis_client.keys('config:*')
        
        stats = {
            'email_cache': len(email_keys),
            'stats_cache': len(stats_keys),
            'digest_cache': len(digest_keys),
            'config_cache': len(config_keys),
            'total_cache': len(email_keys) + len(stats_keys) + len(digest_keys) + len(config_keys)
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取缓存统计失败: {str(e)}'
        })

@app.route('/api/cache/clear/user', methods=['POST'])
@auth_service.require_login
def clear_user_cache_api():
    """清理当前用户的缓存"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': '用户未登录'
            })
        
        if not cache_service or not cache_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Redis缓存未连接'
            })
        
        # 清理用户相关缓存
        user_id = user['id']
        patterns = [
            f'emails:user:{user_id}:*',
            f'stats:user:{user_id}',
            f'digests:user:{user_id}:*',
            f'config:user:{user_id}:*'
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = cache_service.delete_pattern(pattern)
            total_cleared += cleared
        
        logger.info(f"用户 {user_id} 缓存清理完成，清除了 {total_cleared} 个缓存项")
        
        return jsonify({
            'success': True,
            'cleared_count': total_cleared,
            'message': f'成功清理了 {total_cleared} 个缓存项'
        })
        
    except Exception as e:
        logger.error(f"清理用户缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': f'清理用户缓存失败: {str(e)}'
        })

@app.route('/api/cache/clear/all', methods=['POST'])
@auth_service.require_login
def clear_all_cache_api():
    """清理所有缓存（需要管理员权限）"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': '用户未登录'
            })
        
        # 检查管理员权限
        if not user.get('is_admin', False):
            return jsonify({
                'success': False,
                'error': '需要管理员权限'
            })
        
        if not cache_service or not cache_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Redis缓存未连接'
            })
        
        # 清理所有应用相关缓存
        patterns = ['emails:*', 'stats:*', 'digests:*', 'config:*']
        
        total_cleared = 0
        for pattern in patterns:
            cleared = cache_service.delete_pattern(pattern)
            total_cleared += cleared
        
        logger.info(f"管理员 {user['id']} 执行全局缓存清理，清除了 {total_cleared} 个缓存项")
        
        return jsonify({
            'success': True,
            'cleared_count': total_cleared,
            'message': f'成功清理了 {total_cleared} 个缓存项'
        })
        
    except Exception as e:
        logger.error(f"清理所有缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': f'清理所有缓存失败: {str(e)}'
        })

@app.route('/api/cache/health')
@auth_service.require_login
def get_cache_health():
    """获取缓存健康报告"""
    try:
        health_report = auto_cache_cleaner.get_cache_health_report()
        return jsonify({
            'success': True,
            'health': health_report
        })
    except Exception as e:
        logger.error(f"获取缓存健康报告失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取缓存健康报告失败: {str(e)}'
        })

@app.route('/api/cache/cleanup/manual', methods=['POST'])
@auth_service.require_login
def manual_cache_cleanup():
    """手动执行缓存清理"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': '用户未登录'
            })
        
        # 检查管理员权限
        if not user.get('is_admin', False):
            return jsonify({
                'success': False,
                'error': '需要管理员权限'
            })
        
        # 执行清理
        cleanup_result = auto_cache_cleaner.run_daily_cleanup()
        
        logger.info(f"管理员 {user['id']} 手动执行缓存清理")
        
        return jsonify({
            'success': True,
            'cleanup_result': cleanup_result
        })
        
    except Exception as e:
        logger.error(f"手动缓存清理失败: {e}")
        return jsonify({
            'success': False,
            'error': f'手动缓存清理失败: {str(e)}'
        })

# 注册邮件撰写和回复路由
register_compose_routes(app)
register_reply_routes(app)

# 注册邮件分类路由
register_classification_routes(app)

@app.route('/sent')
@auth_service.require_login
def sent_emails():
    """已发送邮件页面"""
    return render_template('sent_emails.html')

@app.route('/notifications')
@auth_service.require_login
def notification_center():
    """通知中心页面"""
    try:
        user = auth_service.get_current_user()
        return render_template('notification_center.html', user=user)
    except Exception as e:
        logger.error(f"加载通知中心页面时出错: {e}")
        flash('加载通知中心失败，请稍后重试', 'error')
        return redirect(url_for('index'))

# ==================== 系统通知相关API ====================

@app.route('/api/notifications')
@auth_service.require_login
def get_notifications():
    """获取用户通知列表"""
    try:
        user = auth_service.get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications, total = db.get_user_notifications(user['id'], page, per_page, unread_only)
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"获取通知列表失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取通知列表失败: {str(e)}'
        }), 500

@app.route('/api/notifications/unread-count')
@auth_service.require_login
def get_unread_notification_count():
    """获取未读通知数量"""
    try:
        user = auth_service.get_current_user()
        count = db.get_unread_notification_count(user['id'])
        
        return jsonify({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"获取未读通知数量失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取未读通知数量失败: {str(e)}'
        }), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@auth_service.require_login
def mark_notification_read(notification_id):
    """标记通知为已读"""
    try:
        user = auth_service.get_current_user()
        success = db.mark_notification_as_read(notification_id, user['id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': '已标记为已读'
            })
        else:
            return jsonify({
                'success': False,
                'message': '通知不存在或没有权限'
            }), 404
        
    except Exception as e:
        logger.error(f"标记通知为已读失败: {e}")
        return jsonify({
            'success': False,
            'message': f'标记失败: {str(e)}'
        }), 500

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@auth_service.require_login
def mark_all_notifications_read():
    """标记所有通知为已读"""
    try:
        user = auth_service.get_current_user()
        success = db.mark_all_notifications_as_read(user['id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': '所有通知已标记为已读'
            })
        else:
            return jsonify({
                'success': False,
                'message': '标记失败'
            }), 500
        
    except Exception as e:
        logger.error(f"标记所有通知为已读失败: {e}")
        return jsonify({
            'success': False,
            'message': f'标记失败: {str(e)}'
        }), 500

@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@auth_service.require_login
def delete_notification_api(notification_id):
    """删除通知"""
    try:
        user = auth_service.get_current_user()
        success = db.delete_notification(notification_id, user['id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': '通知已删除'
            })
        else:
            return jsonify({
                'success': False,
                'message': '通知不存在或没有权限'
            }), 404
        
    except Exception as e:
        logger.error(f"删除通知失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

@app.route('/api/user/sent-emails')
@auth_service.require_login
def get_sent_emails():
    """获取用户已发送邮件API"""
    try:
        user = auth_service.get_current_user()
        
        # 从数据库获取已发送邮件
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, to_addresses, cc_addresses, bcc_addresses, subject, 
                       body, sent_at, created_at
                FROM sent_emails 
                WHERE user_id = ? 
                ORDER BY sent_at DESC 
                LIMIT 50
            ''', (user['id'],))
            
            sent_emails = []
            for row in cursor.fetchall():
                email_dict = dict(row)
                sent_emails.append(email_dict)
        
        return jsonify({
            'success': True,
            'emails': sent_emails
        })
        
    except Exception as e:
        logger.error(f"获取已发送邮件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取已发送邮件失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 初始化系统
    init_system()
    
    # 启动定时任务
    start_scheduler()
    
    try:
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
    finally:
        if scheduler.running:
            scheduler.shutdown()
