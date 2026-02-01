#!/usr/bin/env python3
"""
测试 manager 账号登录
"""
import requests
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

BASE_URL = "http://localhost:8080"
LOGIN_ENDPOINT = f"{BASE_URL}/api/auth/login"

def test_manager_login():
    """测试 manager 登录"""
    
    manager_account = os.getenv('MANAGER_ACCOUNT', 'manager')
    manager_password = os.getenv('MANAGER_PASSWORD')
    
    print('=' * 70)
    print(f'🔐 测试 Manager 账号登录')
    print('=' * 70)
    print(f'账号: {manager_account}')
    print(f'密码已配置: {"✅ 是" if manager_password else "❌ 否"}')
    if manager_password:
        print(f'密码长度: {len(manager_password)} 字符')
    print()
    
    if not manager_password:
        print('❌ 环境变量 MANAGER_PASSWORD 未设置')
        return False
    
    payload = {
        "account": manager_account,
        "password": manager_password
    }
    
    print(f'📤 发送登录请求...')
    print(f'📋 请求数据: account={manager_account}, password={"*" * len(manager_password)}')
    print()
    
    try:
        response = requests.post(LOGIN_ENDPOINT, json=payload, timeout=10)
        
        print(f'📥 响应状态码: {response.status_code}')
        print(f'📥 响应体:')
        
        try:
            response_json = response.json()
            print(json.dumps(response_json, ensure_ascii=False, indent=2))
        except:
            print(response.text)
        
        print()
        
        if response.status_code == 200:
            print('✅ Manager 登录成功！')
            return True
        else:
            print(f'❌ Manager 登录失败（状态码: {response.status_code}）')
            return False
            
    except Exception as e:
        print(f'❌ 错误: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_manager_login()
