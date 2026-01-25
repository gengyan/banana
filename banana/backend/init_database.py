#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据库表并创建 manager 账号
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from database import init_database, create_manager_account

def main():
    """初始化数据库"""
    print("=" * 50)
    print("🚀 初始化数据库")
    print("=" * 50)
    print("")
    
    try:
        # 1. 初始化数据库表
        print("步骤 1: 初始化数据库表...")
        init_database()
        print("✅ 数据库表初始化完成")
        print("")
        
        # 2. 创建 manager 账号
        print("步骤 2: 创建 manager 管理员账号...")
        manager = create_manager_account()
        print(f"✅ manager 账号创建成功")
        print(f"   账号: manager")
        print(f"   密码: 075831")
        print("")
        
        print("=" * 50)
        print("✅ 数据库初始化完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
