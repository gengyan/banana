#!/usr/bin/env python3
"""
详细诊断密码验证问题
"""

from database import get_user_by_account, verify_password, verify_user_login
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG, format='[%(name)s] %(message)s')

def diagnose_login(account, password):
    """诊断登录问题"""
    print('=' * 70)
    print(f'🔍 诊断登录问题: {account}')
    print('=' * 70)
    print()
    
    # 第1步：查询用户
    print('【第1步】查询用户账号...')
    user = get_user_by_account(account)
    if not user:
        print(f'❌ 账号 {account} 不存在')
        return
    
    print(f'✅ 找到用户:')
    print(f'   ID: {user["id"]}')
    print(f'   账号: {user["account"]}')
    print(f'   昵称: {user["nickname"]}')
    print(f'   密码哈希: {user["password_hash"][:80]}...')
    print()
    
    # 第2步：分析密码哈希
    print('【第2步】分析密码哈希...')
    password_hash = user['password_hash']
    
    if password_hash.startswith('$2b$'):
        print('✅ 使用 bcrypt 算法')
    elif password_hash.startswith('sha256:'):
        print('✅ 使用 SHA256 算法')
    else:
        print(f'⚠️ 未知的哈希格式: {password_hash[:20]}')
    print()
    
    # 第3步：尝试验证密码
    print('【第3步】验证密码...')
    print(f'   输入账号: {account}')
    print(f'   输入密码: {password}')
    print(f'   密码长度: {len(password)} 字符')
    print()
    
    # 直接测试密码验证
    print('【第3-1步】直接测试 verify_password()...')
    password_match = verify_password(password, password_hash)
    print(f'✅ 验证结果: {password_match}')
    print()
    
    # 完整登录验证
    print('【第4步】完整登录验证 verify_user_login()...')
    login_result = verify_user_login(account, password)
    if login_result:
        print('✅ 登录成功！')
        print(f'   用户ID: {login_result["id"]}')
    else:
        print('❌ 登录失败')
    print()
    
    # 总结
    print('=' * 70)
    print('📊 诊断总结:')
    print('=' * 70)
    if password_match and login_result:
        print('✅ 所有检查通过，登录应该成功')
    elif not password_match:
        print('❌ 密码验证失败')
        print('   可能原因:')
        print('   1. 密码输入错误')
        print('   2. 数据库中的密码哈希损坏')
        print('   3. bcrypt库版本不兼容')
        print()
        print('   尝试以下操作:')
        print('   1. 检查bcrypt是否已安装: pip install bcrypt')
        print('   2. 使用 reset_password.py 重置密码')
    else:
        print('❌ 登录验证函数有问题')
    print()

if __name__ == '__main__':
    diagnose_login('13333268331', '123456')
