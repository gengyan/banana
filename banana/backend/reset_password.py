#!/usr/bin/env python3
"""
重置用户密码脚本
"""

import sqlite3
import sys
import os
from database import hash_password, get_db_connection

def reset_user_password(account, new_password):
    """重置用户密码"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 检查账号是否存在
            cursor.execute('SELECT id, account FROM users WHERE account = ?', (account,))
            user = cursor.fetchone()
            
            if not user:
                print(f'❌ 账号 {account} 不存在')
                return False
            
            # 生成新的密码哈希
            new_password_hash = hash_password(new_password)
            
            # 更新密码
            cursor.execute('''
                UPDATE users 
                SET password_hash = ?, updated_at = datetime('now')
                WHERE account = ?
            ''', (new_password_hash, account))
            
            print(f'✅ 密码重置成功')
            print(f'   账号: {account}')
            print(f'   新密码: {new_password}')
            print(f'   用户ID: {user["id"]}')
            
            return True
            
    except Exception as e:
        print(f'❌ 重置密码失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print('用法: python3 reset_password.py <账号> <新密码>')
        print('示例: python3 reset_password.py 13333268331 123456')
        sys.exit(1)
    
    account = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 6:
        print('❌ 密码长度至少6位')
        sys.exit(1)
    
    print('=' * 70)
    print('🔐 重置用户密码')
    print('=' * 70)
    print()
    
    success = reset_user_password(account, new_password)
    
    if success:
        print()
        print('=' * 70)
        print('✅ 操作完成')
        print('=' * 70)
    else:
        print()
        print('=' * 70)
        print('❌ 操作失败')
        print('=' * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
