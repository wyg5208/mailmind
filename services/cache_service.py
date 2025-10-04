#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - Redis缓存服务
"""

import redis
import json
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps

from config import Config

logger = logging.getLogger(__name__)

class CacheService:
    """Redis缓存服务"""
    
    def __init__(self):
        self.redis_client = None
        self.is_available = False
        self.connect()
    
    def connect(self):
        """连接Redis服务器"""
        try:
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=Config.REDIS_DECODE_RESPONSES,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # 测试连接
            self.redis_client.ping()
            self.is_available = True
            logger.info(f"Redis缓存服务连接成功: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
            
        except Exception as e:
            self.is_available = False
            logger.warning(f"Redis缓存服务连接失败: {e}")
            logger.info("系统将在无缓存模式下运行")
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self.is_available:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis连接检查失败: {e}")
            self.is_available = False
            return False
    
    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数转换为字符串并排序
        key_parts = [prefix]
        
        # 添加位置参数
        for arg in args:
            key_parts.append(str(arg))
        
        # 添加关键字参数（排序确保一致性）
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = ':'.join([f"{k}={v}" for k, v in sorted_kwargs])
            if kwargs_str:
                # 对长参数进行哈希处理
                if len(kwargs_str) > 100:
                    kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
                    key_parts.append(f"hash:{kwargs_hash}")
                else:
                    key_parts.append(kwargs_str)
        
        return ':'.join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if not self.is_connected():
            return None
        
        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
                
        except Exception as e:
            logger.warning(f"获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        if not self.is_connected():
            return False
        
        try:
            # 序列化数据
            if isinstance(value, (dict, list, tuple)):
                data = json.dumps(value, ensure_ascii=False, default=str)
            else:
                data = str(value)
            
            # 设置缓存
            if ttl:
                result = self.redis_client.setex(key, ttl, data)
            else:
                result = self.redis_client.set(key, data)
            
            return bool(result)
            
        except Exception as e:
            logger.warning(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.warning(f"删除缓存失败 {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """批量删除匹配模式的缓存"""
        if not self.is_connected():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                result = self.redis_client.delete(*keys)
                logger.debug(f"删除缓存模式 {pattern}: {result} 个键")
                return result
            return 0
        except Exception as e:
            logger.warning(f"批量删除缓存失败 {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.warning(f"检查缓存存在性失败 {key}: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取缓存剩余时间"""
        if not self.is_connected():
            return -1
        
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.warning(f"获取缓存TTL失败 {key}: {e}")
            return -1
    
    def invalidate_user_cache(self, user_id: int, action_type: str = 'all'):
        """智能缓存失效"""
        if not self.is_connected():
            return
        
        try:
            patterns_to_clear = []
            
            if action_type in ['all', 'new_email', 'delete_email', 'update_email']:
                # 清除邮件相关缓存
                patterns_to_clear.extend([
                    f'emails:user:{user_id}:*',
                    f'stats:user:{user_id}',
                    f'email:detail:*'  # 可能影响邮件详情
                ])
            
            if action_type in ['all', 'new_digest', 'delete_digest']:
                # 清除简报相关缓存
                patterns_to_clear.append(f'digests:user:{user_id}:*')
            
            if action_type in ['all', 'config_change']:
                # 清除配置相关缓存
                patterns_to_clear.append(f'config:user:{user_id}:*')
            
            # 执行清除
            total_cleared = 0
            for pattern in patterns_to_clear:
                cleared = self.delete_pattern(pattern)
                total_cleared += cleared
            
            if total_cleared > 0:
                logger.info(f"用户 {user_id} 缓存失效: {action_type}, 清除 {total_cleared} 个缓存项")
                
        except Exception as e:
            logger.warning(f"缓存失效失败 user_id={user_id}, action={action_type}: {e}")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        if not self.is_connected():
            return {'status': 'disconnected'}
        
        try:
            info = self.redis_client.info()
            return {
                'status': 'connected',
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0), 
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.warning(f"获取缓存统计失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> str:
        """计算缓存命中率"""
        total = hits + misses
        if total == 0:
            return "0.00%"
        return f"{(hits / total * 100):.2f}%"

# 全局缓存服务实例
cache_service = CacheService()

def cached(key_prefix: str, ttl: Optional[int] = None, user_specific: bool = True):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 如果缓存不可用，直接执行函数
            if not cache_service.is_connected():
                return func(*args, **kwargs)
            
            # 生成缓存键
            cache_key_parts = [key_prefix]
            
            # 如果是用户特定的缓存，添加用户ID
            if user_specific and 'user_id' in kwargs:
                cache_key_parts.append(f"user:{kwargs['user_id']}")
            elif user_specific and len(args) > 0:
                # 假设第一个参数是user_id
                cache_key_parts.append(f"user:{args[0]}")
            
            cache_key = cache_service.generate_cache_key(*cache_key_parts, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            
            # 设置缓存
            cache_ttl = ttl or Config.CACHE_TTL.get('email_list', 300)
            cache_service.set(cache_key, result, cache_ttl)
            logger.debug(f"缓存设置: {cache_key}, TTL: {cache_ttl}s")
            
            return result
        
        return wrapper
    return decorator

# 常用缓存键模板
class CacheKeys:
    """缓存键模板"""
    
    # 邮件相关
    EMAIL_LIST = "emails:user:{user_id}:page:{page}"
    EMAIL_LIST_FILTERED = "emails:user:{user_id}:filtered"
    EMAIL_DETAIL = "email:detail:{email_id}"
    
    # 用户统计
    USER_STATS = "stats:user:{user_id}"
    
    # 简报相关
    DIGEST_LIST = "digests:user:{user_id}:page:{page}"
    DIGEST_DETAIL = "digest:detail:{digest_id}"
    
    # 用户配置
    USER_CONFIG = "config:user:{user_id}"
    USER_ACCOUNTS = "accounts:user:{user_id}"
    
    # 系统级缓存
    SYSTEM_STATS = "stats:system"
    ACTIVE_USERS = "users:active"

if __name__ == "__main__":
    # 测试缓存服务
    print("测试Redis缓存服务...")
    
    # 连接测试
    if cache_service.is_connected():
        print("✅ Redis连接成功")
        
        # 基本操作测试
        test_key = "test:cache:service"
        test_data = {"message": "Hello Redis!", "timestamp": datetime.now().isoformat()}
        
        # 设置缓存
        if cache_service.set(test_key, test_data, 60):
            print("✅ 缓存设置成功")
            
            # 获取缓存
            cached_data = cache_service.get(test_key)
            if cached_data == test_data:
                print("✅ 缓存获取成功")
            else:
                print("❌ 缓存数据不匹配")
            
            # 删除缓存
            if cache_service.delete(test_key):
                print("✅ 缓存删除成功")
            else:
                print("❌ 缓存删除失败")
        else:
            print("❌ 缓存设置失败")
        
        # 统计信息
        stats = cache_service.get_cache_stats()
        print(f"📊 缓存统计: {stats}")
        
    else:
        print("❌ Redis连接失败")
