#!/usr/bin/env python3
"""
查询数据库中的用户账号信息
"""

import sqlite3
import sys
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def query_all_users():
    """查询所有用户账号"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print('=' * 70)
        print('📋 数据库中的所有账号:')
        print('=' * 70)
        
        cursor.execute('''
            SELECT id, account, nickname, level, created_at, updated_at 
            FROM users 
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        
        if rows:
            print(f'总共找到 {len(rows)} 个账号:\n')
            for i, row in enumerate(rows, 1):
                print(f'{i}. 账号: {row["account"]}')
                print(f'   ID: {row["id"]}')
                print(f'   昵称: {row["nickname"] or "(无)"}')
                print(f'   等级: {row["level"]}')
                print(f'   创建时间: {row["created_at"]}')
                print(f'   更新时间: {row["updated_at"]}')
                print()
        else:
            print('❌ 数据库中没有用户')
        
        conn.close()
        return rows
        
    except Exception as e:
        print(f'❌ 查询失败: {e}')
        import traceback
        traceback.print_exc()
        return None


def query_user_by_account(account):
    """查询指定账号的详细信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print('=' * 70)
        print(f'🔍 查询账号: {account}')
        print('=' * 70)
        
        cursor.execute('SELECT * FROM users WHERE account = ?', (account,))
        row = cursor.fetchone()
        
        if row:
            print(f'✅ 找到账号: {row["account"]}')
            print(f'   ID: {row["id"]}')
            print(f'   昵称: {row["nickname"] or "(无)"}')
            print(f'   等级: {row["level"]}')
            print(f'   头像: {row["avatar"] or "(无)"}')
            print(f'   创建时间: {row["created_at"]}')
            print(f'   更新时间: {row["updated_at"]}')
            print()
            
            # 显示密码哈希信息（不显示完整哈希，只显示类型和部分信息）
            password_hash = row["password_hash"]
            if password_hash.startswith('$2'):
                hash_type = 'bcrypt'
                hash_preview = password_hash[:30] + '...'
            elif password_hash.startswith('sha256:'):
                hash_type = 'sha256'
                parts = password_hash.split(':')
                hash_preview = f'sha256:{parts[1][:10]}...:{parts[2][:20]}...'
            else:
                hash_type = '未知'
                hash_preview = password_hash[:50] + '...'
            
            print(f'   密码哈希类型: {hash_type}')
            print(f'   密码哈希预览: {hash_preview}')
            print()
            print('⚠️  注意: 密码是加密存储的，无法直接查看明文密码')
            print('💡 如果需要重置密码，可以:')
            print('   1. 使用注册功能重新注册（如果账号不存在）')
            print('   2. 使用管理员功能重置密码')
            print('   3. 直接修改数据库（不推荐）')
            
            return row
        else:
            print(f'❌ 账号 {account} 不存在于数据库中')
            return None
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 查询失败: {e}')
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    # 检查数据库文件是否存在
    if not os.path.exists(DB_PATH):
        print(f'❌ 数据库文件不存在: {DB_PATH}')
        sys.exit(1)
    
    print('🔍 用户账号查询工具')
    print('=' * 70)
    print()
    
    # 查询所有账号
    all_users = query_all_users()
    
    print()
    
    # 查询特定账号
    target_account = '13333268331'
    user = query_user_by_account(target_account)
    
    print()
    print('=' * 70)
    print('✅ 查询完成')
    print('=' * 70)


if __name__ == '__main__':
    main()
