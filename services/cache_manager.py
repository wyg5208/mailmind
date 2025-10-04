#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 缓存管理器
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from services.cache_service import cache_service
from config import Config

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器 - 提供高级缓存管理功能"""
    
    def __init__(self):
        self.cache = cache_service
    
    def get_cache_health(self) -> Dict:
        """获取缓存健康状态"""
        if not self.cache.is_connected():
            return {
                'status': 'disconnected',
                'healthy': False,
                'message': 'Redis服务不可用'
            }
        
        try:
            stats = self.cache.get_cache_stats()
            
            # 计算健康指标
            hit_rate = float(stats.get('hit_rate', '0%').replace('%', ''))
            healthy = hit_rate > 50.0  # 命中率大于50%认为健康
            
            return {
                'status': 'connected',
                'healthy': healthy,
                'hit_rate': stats.get('hit_rate'),
                'used_memory': stats.get('used_memory'),
                'connected_clients': stats.get('connected_clients'),
                'message': '缓存服务正常' if healthy else '缓存命中率较低'
            }
            
        except Exception as e:
            logger.error(f"获取缓存健康状态失败: {e}")
            return {
                'status': 'error',
                'healthy': False,
                'message': f'缓存状态检查失败: {str(e)}'
            }
    
    def warm_up_user_cache(self, user_id: int) -> Dict:
        """预热用户缓存"""
        if not self.cache.is_connected():
            return {'success': False, 'message': 'Redis服务不可用'}
        
        try:
            from models.database import Database
            db = Database()
            
            warmed_items = []
            
            # 预热用户统计
            stats = db.get_user_stats(user_id)
            if stats:
                warmed_items.append('user_stats')
            
            # 预热第一页邮件列表
            emails, total = db.get_user_emails_filtered(user_id, page=1, per_page=20)
            if emails:
                warmed_items.append('email_list_page1')
            
            # 预热用户配置
            configs = db.get_user_configs(user_id)
            if configs:
                cache_key = self.cache.generate_cache_key('config:user', user_id)
                self.cache.set(cache_key, configs, Config.CACHE_TTL['user_config'])
                warmed_items.append('user_config')
            
            return {
                'success': True,
                'message': f'用户 {user_id} 缓存预热完成',
                'warmed_items': warmed_items,
                'count': len(warmed_items)
            }
            
        except Exception as e:
            logger.error(f"用户缓存预热失败 user_id={user_id}: {e}")
            return {
                'success': False,
                'message': f'缓存预热失败: {str(e)}'
            }
    
    def clear_user_cache(self, user_id: int) -> Dict:
        """清除用户所有缓存"""
        if not self.cache.is_connected():
            return {'success': False, 'message': 'Redis服务不可用'}
        
        try:
            # 清除所有用户相关缓存
            patterns = [
                f'emails:user:{user_id}:*',
                f'stats:user:{user_id}',
                f'digests:user:{user_id}:*',
                f'config:user:{user_id}:*'
            ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = self.cache.delete_pattern(pattern)
                total_cleared += cleared
            
            return {
                'success': True,
                'message': f'用户 {user_id} 缓存清除完成',
                'cleared_count': total_cleared
            }
            
        except Exception as e:
            logger.error(f"清除用户缓存失败 user_id={user_id}: {e}")
            return {
                'success': False,
                'message': f'缓存清除失败: {str(e)}'
            }
    
    def get_cache_keys_info(self, pattern: str = '*') -> Dict:
        """获取缓存键信息"""
        if not self.cache.is_connected():
            return {'success': False, 'message': 'Redis服务不可用'}
        
        try:
            keys = self.cache.redis_client.keys(pattern)
            
            key_info = []
            for key in keys[:50]:  # 限制显示前50个键
                ttl = self.cache.ttl(key)
                key_info.append({
                    'key': key,
                    'ttl': ttl,
                    'expires_in': f"{ttl}秒" if ttl > 0 else "永不过期" if ttl == -1 else "已过期"
                })
            
            return {
                'success': True,
                'total_keys': len(keys),
                'showing': len(key_info),
                'keys': key_info
            }
            
        except Exception as e:
            logger.error(f"获取缓存键信息失败: {e}")
            return {
                'success': False,
                'message': f'获取缓存键失败: {str(e)}'
            }
    
    def optimize_cache(self) -> Dict:
        """缓存优化建议"""
        if not self.cache.is_connected():
            return {'success': False, 'message': 'Redis服务不可用'}
        
        try:
            stats = self.cache.get_cache_stats()
            hit_rate = float(stats.get('hit_rate', '0%').replace('%', ''))
            
            suggestions = []
            
            # 命中率分析
            if hit_rate < 30:
                suggestions.append({
                    'type': 'warning',
                    'message': '缓存命中率过低，建议检查缓存策略',
                    'action': '增加缓存时间或预热热点数据'
                })
            elif hit_rate < 60:
                suggestions.append({
                    'type': 'info',
                    'message': '缓存命中率中等，有优化空间',
                    'action': '分析访问模式，优化缓存键设计'
                })
            else:
                suggestions.append({
                    'type': 'success',
                    'message': '缓存命中率良好',
                    'action': '保持当前缓存策略'
                })
            
            # 内存使用分析
            used_memory = stats.get('used_memory', 'N/A')
            if 'MB' in str(used_memory) and float(str(used_memory).replace('MB', '')) > 100:
                suggestions.append({
                    'type': 'warning',
                    'message': '缓存内存使用较高',
                    'action': '考虑清理过期缓存或调整TTL'
                })
            
            return {
                'success': True,
                'hit_rate': f"{hit_rate}%",
                'used_memory': used_memory,
                'suggestions': suggestions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"缓存优化分析失败: {e}")
            return {
                'success': False,
                'message': f'缓存分析失败: {str(e)}'
            }
    
    def batch_warm_up(self, user_ids: List[int]) -> Dict:
        """批量预热用户缓存"""
        if not self.cache.is_connected():
            return {'success': False, 'message': 'Redis服务不可用'}
        
        results = {
            'success': True,
            'total_users': len(user_ids),
            'warmed_users': 0,
            'failed_users': 0,
            'details': []
        }
        
        for user_id in user_ids:
            try:
                result = self.warm_up_user_cache(user_id)
                if result['success']:
                    results['warmed_users'] += 1
                    results['details'].append({
                        'user_id': user_id,
                        'status': 'success',
                        'items': result.get('count', 0)
                    })
                else:
                    results['failed_users'] += 1
                    results['details'].append({
                        'user_id': user_id,
                        'status': 'failed',
                        'error': result.get('message', 'Unknown error')
                    })
            except Exception as e:
                results['failed_users'] += 1
                results['details'].append({
                    'user_id': user_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results

# 全局缓存管理器实例
cache_manager = CacheManager()

if __name__ == "__main__":
    # 测试缓存管理器
    print("测试缓存管理器...")
    
    # 健康检查
    health = cache_manager.get_cache_health()
    print(f"缓存健康状态: {health}")
    
    # 缓存键信息
    keys_info = cache_manager.get_cache_keys_info("*email*")
    print(f"邮件相关缓存键: {keys_info}")
    
    # 优化建议
    optimization = cache_manager.optimize_cache()
    print(f"缓存优化建议: {optimization}")
