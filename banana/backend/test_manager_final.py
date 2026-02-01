#!/usr/bin/env python3
"""
Manager 账号登录测试 - 完整验证
"""

import subprocess
import json

def test_manager_login_with_curl():
    """使用 curl 测试 manager 登录（避免代理问题）"""
    
    print('=' * 70)
    print('🔐 Manager 账号登录测试')
    print('=' * 70)
    print()
    
    # 读取环境变量中的密码
    result = subprocess.run(
        ['grep', 'MANAGER_PASSWORD', '.env'],
        capture_output=True,
        text=True,
        cwd='/Users/mac/Documents/ai/knowledgebase/bananas/banana/backend'
    )
    
    if result.returncode == 0:
        password_line = result.stdout.strip()
        password = password_line.split('=')[1] if '=' in password_line else None
        print(f'✅ 环境变量配置: {password_line}')
        print(f'   密码长度: {len(password)} 字符')
    else:
        print('❌ 未找到 MANAGER_PASSWORD 配置')
        return False
    
    print()
    print('📤 发送登录请求...')
    
    # 使用 curl 测试登录
    curl_cmd = [
        'curl', '-X', 'POST',
        'http://localhost:8080/api/auth/login',
        '-H', 'Content-Type: application/json',
        '-d', f'{{"account":"manager","password":"{password}"}}',
        '-s'  # silent mode
    ]
    
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    
    print(f'📥 响应状态: {result.returncode}')
    
    try:
        response_json = json.loads(result.stdout)
        print(f'📥 响应体:')
        print(json.dumps(response_json, ensure_ascii=False, indent=2))
        print()
        
        if response_json.get('success'):
            print('✅ Manager 登录成功！')
            print()
            print('📊 用户信息:')
            user = response_json.get('user', {})
            print(f'   ID: {user.get("id")}')
            print(f'   账号: {user.get("account")}')
            print(f'   昵称: {user.get("nickname")}')
            print(f'   等级: {user.get("level")}')
            print(f'   Session Token: {response_json.get("session_token")[:30]}...')
            return True
        else:
            print('❌ 登录失败')
            print(f'   错误信息: {response_json.get("detail")}')
            return False
            
    except json.JSONDecodeError as e:
        print(f'❌ 响应解析失败: {e}')
        print(f'   原始响应: {result.stdout}')
        return False

if __name__ == '__main__':
    success = test_manager_login_with_curl()
    exit(0 if success else 1)
