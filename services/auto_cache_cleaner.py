#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动缓存清理服务
定期清理过期和无用的缓存数据
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
from services.cache_service import cache_service
from models.database import Database

logger = logging.getLogger(__name__)

class AutoCacheCleaner:
    """自动缓存清理器"""
    
    def __init__(self):
        self.db = Database()
        self.cache = cache_service
        
    def run_daily_cleanup(self) -> Dict:
        """执行每日缓存清理"""
        logger.info("开始执行每日缓存清理...")
        
        cleanup_stats = {
            'start_time': datetime.now().isoformat(),
            'total_cleared': 0,
            'categories': {},
            'errors': []
        }
        
        try:
            # 1. 清理过期的邮件列表缓存
            email_cleared = self._clean_expired_email_cache()
            cleanup_stats['categories']['email_cache'] = email_cleared
            cleanup_stats['total_cleared'] += email_cleared
            
            # 2. 清理过期的统计缓存
            stats_cleared = self._clean_expired_stats_cache()
            cleanup_stats['categories']['stats_cache'] = stats_cleared
            cleanup_stats['total_cleared'] += stats_cleared
            
            # 3. 清理过期的简报缓存
            digest_cleared = self._clean_expired_digest_cache()
            cleanup_stats['categories']['digest_cache'] = digest_cleared
            cleanup_stats['total_cleared'] += digest_cleared
            
            # 4. 清理孤立的缓存键（对应的用户不存在）
            orphan_cleared = self._clean_orphan_cache()
            cleanup_stats['categories']['orphan_cache'] = orphan_cleared
            cleanup_stats['total_cleared'] += orphan_cleared
            
            # 5. 清理超大缓存键（防止内存溢出）
            oversized_cleared = self._clean_oversized_cache()
            cleanup_stats['categories']['oversized_cache'] = oversized_cleared
            cleanup_stats['total_cleared'] += oversized_cleared
            
            cleanup_stats['end_time'] = datetime.now().isoformat()
            cleanup_stats['success'] = True
            
            logger.info(f"每日缓存清理完成，共清理 {cleanup_stats['total_cleared']} 个缓存项")
            
        except Exception as e:
            cleanup_stats['success'] = False
            cleanup_stats['errors'].append(str(e))
            logger.error(f"每日缓存清理失败: {e}")
        
        return cleanup_stats
    
    def _clean_expired_email_cache(self, retention_days: int = 3) -> int:
        """清理过期的邮件缓存"""
        if not self.cache or not self.cache.is_connected():
            return 0
        
        try:
            # 获取所有邮件缓存键
            email_keys = self.cache.redis_client.keys('emails:*')
            cleared_count = 0
            
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            for key in email_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    
                    # 检查缓存的TTL
                    ttl = self.cache.redis_client.ttl(key)
                    
                    # 如果TTL为-1（永不过期）或TTL过长，检查是否需要清理
                    if ttl == -1 or ttl > retention_days * 24 * 3600:
                        # 获取缓存创建时间（如果有的话）
                        cache_data = self.cache.get(key_str)
                        if cache_data and isinstance(cache_data, dict):
                            created_at = cache_data.get('created_at')
                            if created_at:
                                try:
                                    created_time = datetime.fromisoformat(created_at)
                                    if created_time < cutoff_time:
                                        self.cache.redis_client.delete(key)
                                        cleared_count += 1
                                        logger.debug(f"清理过期邮件缓存: {key_str}")
                                except (ValueError, TypeError):
                                    pass
                    
                    # 如果TTL已过期但仍存在，直接删除
                    elif ttl == -2:  # 键不存在
                        continue
                    elif ttl > 0 and ttl < 60:  # 即将过期
                        self.cache.redis_client.delete(key)
                        cleared_count += 1
                        logger.debug(f"清理即将过期邮件缓存: {key_str}")
                        
                except Exception as e:
                    logger.warning(f"清理邮件缓存键 {key} 时出错: {e}")
                    continue
            
            logger.info(f"清理过期邮件缓存完成，清理了 {cleared_count} 个键")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期邮件缓存失败: {e}")
            return 0
    
    def _clean_expired_stats_cache(self, retention_days: int = 1) -> int:
        """清理过期的统计缓存"""
        if not self.cache or not self.cache.is_connected():
            return 0
        
        try:
            # 统计缓存通常更新频繁，保留时间较短
            stats_keys = self.cache.redis_client.keys('stats:*')
            cleared_count = 0
            
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            for key in stats_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    
                    # 检查缓存的最后修改时间
                    last_modified = self.cache.redis_client.object('IDLETIME', key)
                    if last_modified and last_modified > retention_days * 24 * 3600:
                        self.cache.redis_client.delete(key)
                        cleared_count += 1
                        logger.debug(f"清理过期统计缓存: {key_str}")
                        
                except Exception as e:
                    logger.warning(f"清理统计缓存键 {key} 时出错: {e}")
                    continue
            
            logger.info(f"清理过期统计缓存完成，清理了 {cleared_count} 个键")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期统计缓存失败: {e}")
            return 0
    
    def _clean_expired_digest_cache(self, retention_days: int = 7) -> int:
        """清理过期的简报缓存"""
        if not self.cache or not self.cache.is_connected():
            return 0
        
        try:
            # 简报缓存可以保留较长时间
            digest_keys = self.cache.redis_client.keys('digests:*')
            cleared_count = 0
            
            for key in digest_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    
                    # 检查TTL
                    ttl = self.cache.redis_client.ttl(key)
                    if ttl == -1:  # 永不过期的键，检查内容
                        cache_data = self.cache.get(key_str)
                        if not cache_data:  # 空缓存
                            self.cache.redis_client.delete(key)
                            cleared_count += 1
                            logger.debug(f"清理空简报缓存: {key_str}")
                    elif ttl > retention_days * 24 * 3600:  # TTL过长
                        # 可以选择重新设置TTL或删除
                        self.cache.redis_client.expire(key, retention_days * 24 * 3600)
                        
                except Exception as e:
                    logger.warning(f"清理简报缓存键 {key} 时出错: {e}")
                    continue
            
            logger.info(f"清理过期简报缓存完成，清理了 {cleared_count} 个键")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期简报缓存失败: {e}")
            return 0
    
    def _clean_orphan_cache(self) -> int:
        """清理孤立的缓存（对应的用户不存在）"""
        if not self.cache or not self.cache.is_connected():
            return 0
        
        try:
            # 获取所有活跃用户ID
            active_users = set()
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE is_active = 1')
                    active_users = {row['id'] for row in cursor.fetchall()}
            except Exception as e:
                logger.error(f"获取活跃用户列表失败: {e}")
                return 0
            
            # 检查用户相关的缓存键
            user_cache_patterns = ['emails:user:*', 'stats:user:*', 'digests:user:*', 'config:user:*']
            cleared_count = 0
            
            for pattern in user_cache_patterns:
                keys = self.cache.redis_client.keys(pattern)
                
                for key in keys:
                    try:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        
                        # 从键名中提取用户ID
                        parts = key_str.split(':')
                        if len(parts) >= 3 and parts[1] == 'user':
                            try:
                                user_id = int(parts[2])
                                if user_id not in active_users:
                                    self.cache.redis_client.delete(key)
                                    cleared_count += 1
                                    logger.debug(f"清理孤立缓存: {key_str} (用户 {user_id} 不存在)")
                            except ValueError:
                                # 无法解析用户ID，跳过
                                continue
                                
                    except Exception as e:
                        logger.warning(f"清理孤立缓存键 {key} 时出错: {e}")
                        continue
            
            logger.info(f"清理孤立缓存完成，清理了 {cleared_count} 个键")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理孤立缓存失败: {e}")
            return 0
    
    def _clean_oversized_cache(self, max_size_mb: int = 10) -> int:
        """清理超大缓存键"""
        if not self.cache or not self.cache.is_connected():
            return 0
        
        try:
            all_keys = self.cache.redis_client.keys('*')
            cleared_count = 0
            max_size_bytes = max_size_mb * 1024 * 1024
            
            for key in all_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    
                    # 检查键的内存使用
                    memory_usage = self.cache.redis_client.memory_usage(key)
                    if memory_usage and memory_usage > max_size_bytes:
                        self.cache.redis_client.delete(key)
                        cleared_count += 1
                        logger.warning(f"清理超大缓存: {key_str} ({memory_usage / 1024 / 1024:.2f}MB)")
                        
                except Exception as e:
                    logger.warning(f"检查缓存键 {key} 大小时出错: {e}")
                    continue
            
            logger.info(f"清理超大缓存完成，清理了 {cleared_count} 个键")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理超大缓存失败: {e}")
            return 0
    
    def get_cache_health_report(self) -> Dict:
        """获取缓存健康报告"""
        if not self.cache or not self.cache.is_connected():
            return {
                'status': 'disconnected',
                'message': 'Redis缓存未连接'
            }
        
        try:
            # Redis信息
            info = self.cache.redis_client.info()
            
            # 内存使用情况
            used_memory = info.get('used_memory', 0)
            used_memory_human = info.get('used_memory_human', '0B')
            max_memory = info.get('maxmemory', 0)
            
            # 键统计
            total_keys = self.cache.redis_client.dbsize()
            
            # 各类缓存统计
            email_keys = len(self.cache.redis_client.keys('emails:*'))
            stats_keys = len(self.cache.redis_client.keys('stats:*'))
            digest_keys = len(self.cache.redis_client.keys('digests:*'))
            config_keys = len(self.cache.redis_client.keys('config:*'))
            other_keys = total_keys - email_keys - stats_keys - digest_keys - config_keys
            
            # 计算健康分数
            health_score = 100
            warnings = []
            
            # 内存使用率检查
            if max_memory > 0:
                memory_usage_ratio = used_memory / max_memory
                if memory_usage_ratio > 0.9:
                    health_score -= 30
                    warnings.append(f"内存使用率过高: {memory_usage_ratio:.1%}")
                elif memory_usage_ratio > 0.7:
                    health_score -= 10
                    warnings.append(f"内存使用率较高: {memory_usage_ratio:.1%}")
            
            # 键数量检查
            if total_keys > 10000:
                health_score -= 20
                warnings.append(f"缓存键数量过多: {total_keys}")
            elif total_keys > 5000:
                health_score -= 10
                warnings.append(f"缓存键数量较多: {total_keys}")
            
            # 确定健康状态
            if health_score >= 80:
                status = 'healthy'
            elif health_score >= 60:
                status = 'warning'
            else:
                status = 'critical'
            
            return {
                'status': status,
                'health_score': health_score,
                'memory': {
                    'used': used_memory,
                    'used_human': used_memory_human,
                    'max': max_memory,
                    'usage_ratio': used_memory / max_memory if max_memory > 0 else 0
                },
                'keys': {
                    'total': total_keys,
                    'email_cache': email_keys,
                    'stats_cache': stats_keys,
                    'digest_cache': digest_keys,
                    'config_cache': config_keys,
                    'other': other_keys
                },
                'warnings': warnings,
                'redis_info': {
                    'version': info.get('redis_version', 'unknown'),
                    'uptime_days': info.get('uptime_in_days', 0),
                    'connected_clients': info.get('connected_clients', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"获取缓存健康报告失败: {e}")
            return {
                'status': 'error',
                'message': f'获取缓存健康报告失败: {str(e)}'
            }

# 全局实例
auto_cache_cleaner = AutoCacheCleaner()

