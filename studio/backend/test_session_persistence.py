#!/usr/bin/env python3
"""
测试会话持久化功能
"""

from database import (
    init_database, create_user, create_session, 
    get_user_from_session, delete_session
)
from datetime import datetime, timedelta

def test_session_persistence():
    """测试会话是否正确持久化到数据库"""
    print('=' * 70)
    print('🔐 测试会话持久化功能')
    print('=' * 70)
    print()
    
    # 1. 创建测试用户
    print('1️⃣ 创建测试用户...')
    try:
        test_email = 'test_session_' + datetime.now().isoformat().replace(':', '').replace('.', '') + '@example.com'
        user = create_user(test_email, 'password123', '会话测试用户')
        user_id = user['id']
        print(f'✅ 用户创建成功')
        print(f'   账号: {user["account"]}')
        print(f'   用户ID: {user_id}')
    except Exception as e:
        print(f'❌ 用户创建失败: {e}')
        return False
    
    print()
    
    # 2. 创建会话
    print('2️⃣ 创建会话...')
    try:
        session_token = 'test_token_session_' + datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=1)).isoformat()
        result = create_session(session_token, user_id, expires_at)
        print(f'✅ 会话创建结果: {result}')
        print(f'   Token: {session_token[:30]}...')
        print(f'   过期时间: {expires_at}')
    except Exception as e:
        print(f'❌ 会话创建失败: {e}')
        return False
    
    print()
    
    # 3. 验证会话
    print('3️⃣ 验证会话...')
    try:
        retrieved_user = get_user_from_session(session_token)
        if retrieved_user:
            print(f'✅ 会话有效')
            print(f'   用户账号: {retrieved_user["account"]}')
            print(f'   用户ID: {retrieved_user["id"]}')
        else:
            print('❌ 会话无效或已过期')
            return False
    except Exception as e:
        print(f'❌ 会话验证失败: {e}')
        return False
    
    print()
    
    # 4. 删除会话
    print('4️⃣ 删除会话...')
    try:
        delete_result = delete_session(session_token)
        print(f'✅ 会话删除结果: {delete_result}')
    except Exception as e:
        print(f'❌ 会话删除失败: {e}')
        return False
    
    print()
    
    # 5. 验证会话已删除
    print('5️⃣ 验证会话已删除...')
    try:
        retrieved_user = get_user_from_session(session_token)
        if retrieved_user:
            print('❌ 会话仍然有效（应该已删除）')
            return False
        else:
            print('✅ 会话已成功删除，无法检索')
    except Exception as e:
        print(f'❌ 验证失败: {e}')
        return False
    
    print()
    print('=' * 70)
    print('✅ 会话持久化测试通过！')
    print('=' * 70)
    return True

if __name__ == '__main__':
    import sys
    init_database()
    success = test_session_persistence()
    sys.exit(0 if success else 1)
