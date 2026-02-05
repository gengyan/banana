#!/usr/bin/env python3
"""
测试登录功能
"""

import sys
from database import get_user_by_account, verify_password, verify_user_login

def test_login(account, password):
    """测试登录"""
    print('=' * 70)
    print(f'🔐 测试登录: {account}')
    print('=' * 70)
    print()
    
    # 1. 检查账号是否存在
    print('1️⃣ 检查账号是否存在...')
    user = get_user_by_account(account)
    if not user:
        print(f'❌ 账号 {account} 不存在')
        return False
    
    print(f'✅ 账号存在')
    print(f'   ID: {user["id"]}')
    print(f'   账号: {user["account"]}')
    print(f'   昵称: {user["nickname"]}')
    print(f'   等级: {user["level"]}')
    print()
    
    # 2. 检查密码哈希
    print('2️⃣ 检查密码哈希...')
    password_hash = user['password_hash']
    hash_type = 'bcrypt' if password_hash.startswith('$') else 'sha256' if password_hash.startswith('sha256:') else '未知'
    print(f'   密码哈希类型: {hash_type}')
    print(f'   密码哈希预览: {password_hash[:60]}...')
    print()
    
    # 3. 测试密码验证
    print('3️⃣ 测试密码验证...')
    print(f'   输入的密码: {"*" * len(password)} (长度: {len(password)})')
    
    # 直接测试密码验证
    password_match = verify_password(password, password_hash)
    print(f'   密码验证结果: {"✅ 匹配" if password_match else "❌ 不匹配"}')
    print()
    
    # 4. 使用完整登录验证
    print('4️⃣ 使用完整登录验证...')
    login_result = verify_user_login(account, password)
    if login_result:
        print('✅ 登录验证成功')
        print(f'   用户ID: {login_result["id"]}')
        print(f'   账号: {login_result["account"]}')
        print(f'   昵称: {login_result["nickname"]}')
    else:
        print('❌ 登录验证失败')
    
    print()
    print('=' * 70)
    if password_match and login_result:
        print('✅ 登录测试通过！')
        return True
    else:
        print('❌ 登录测试失败！')
        print('💡 建议: 使用 reset_password.py 重置密码')
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python3 test_login.py <账号> <密码>')
        print('示例: python3 test_login.py 13333268331 123456')
        sys.exit(1)
    
    account = sys.argv[1]
    password = sys.argv[2]
    
    success = test_login(account, password)
    sys.exit(0 if success else 1)
