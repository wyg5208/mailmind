#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - Windows Server生产环境启动脚本
使用Waitress WSGI服务器（专为Windows设计）
"""

import os
import sys
from pathlib import Path

def main():
    """主函数"""
    try:
        # 导入应用和初始化函数
        from app import app, Config, init_system, start_scheduler
        from waitress import serve
        
        print("=" * 60)
        print("AI Email Digest System - Windows Production Server")
        print("=" * 60)
        
        # 初始化系统
        print("Initializing system...")
        init_system()
        
        # 启动定时任务调度器
        print("Starting scheduler...")
        start_scheduler()
        
        # 获取端口配置
        port = getattr(Config, 'PORT', 6006)
        
        # 生产环境配置
        threads = int(os.getenv('WAITRESS_THREADS', '8'))  # 线程数
        connection_limit = int(os.getenv('WAITRESS_CONNECTION_LIMIT', '1000'))  # 连接限制
        
        print(f"Starting Waitress WSGI server...")
        print(f"Server: Waitress (Windows optimized)")
        print(f"Port: {port}")
        print(f"Threads: {threads}")
        print(f"Connection limit: {connection_limit}")
        print(f"Access URL: http://localhost:{port}")
        print(f"Health Check: http://localhost:{port}/health")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60)
        
        # 使用Waitress启动应用
        serve(
            app,
            host='0.0.0.0',
            port=port,
            threads=threads,
            connection_limit=connection_limit,
            cleanup_interval=30,
            channel_timeout=120,
            log_socket_errors=True
        )
        
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        # 停止调度器
        try:
            from app import scheduler
            if scheduler.running:
                print("Stopping scheduler...")
                scheduler.shutdown()
        except:
            pass
        print("Thank you for using AI Email Digest System!")
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
