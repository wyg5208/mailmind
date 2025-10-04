#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI邮件简报系统 - 应用启动脚本
"""

import os
import sys
from pathlib import Path

def main():
    """主函数"""
    try:
        # 导入应用和初始化函数
        from app import app, Config, init_system, start_scheduler
        
        print("=" * 50)
        print("AI Email Digest System Starting...")
        print("=" * 50)
        
        # 初始化系统
        print("Initializing system...")
        init_system()
        
        # 启动定时任务调度器
        print("Starting scheduler...")
        start_scheduler()
        
        # 获取端口配置
        port = getattr(Config, 'PORT', 6006)
        
        print(f"Starting server on port {port}")
        print(f"Access URL: http://localhost:{port}")
        print(f"Health Check: http://localhost:{port}/health")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 50)
        
        # 启动应用
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
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
