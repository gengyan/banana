#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据库表并创建管理员账号
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
from config import validate_config, MANAGER_ACCOUNT, MANAGER_PASSWORD, MANAGER_NICKNAME

def main():
    """初始化数据库"""
    print("=" * 60)
    print("🚀 初始化数据库")
    print("=" * 60)
    print("")
    
    try:
        # 1. 验证配置
        print("步骤 1: 验证配置...")
        is_valid, errors = validate_config()
        
        if not is_valid:
            print("⚠️  配置验证失败:")
            for error in errors:
                print(f"   {error}")
            print("")
            print("初始化已取消")
            sys.exit(1)
        
        print("✅ 配置验证通过")
        print("")
        
        # 2. 初始化数据库表
        print("步骤 2: 初始化数据库表...")
        init_database()
        print("✅ 数据库表初始化完成")
        print("")
        
        # 3. 创建管理员账号
        print("步骤 3: 创建管理员账号...")
        manager = create_manager_account()
        print(f"✅ 管理员账号创建成功")
        print(f"   账号: {MANAGER_ACCOUNT}")
        print(f"   昵称: {MANAGER_NICKNAME}")
        print(f"   用户ID: {manager['id']}")
        print("")
        
        print("=" * 60)
        print("✅ 数据库初始化完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
