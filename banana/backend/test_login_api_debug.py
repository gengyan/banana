#!/usr/bin/env python3
"""
测试登录 API 端点 - 诊断版本
"""
import requests
import json

# API 端点
BASE_URL = "http://localhost:8080"
LOGIN_ENDPOINT = f"{BASE_URL}/api/auth/login"

def test_login_api(account, password):
    """测试登录 API"""
    print('=' * 70)
    print(f'🔐 测试登录 API: {account}')
    print('=' * 70)
    print()
    
    # 准备请求数据
    payload = {
        "account": account,
        "password": password
    }
    
    print(f'📤 发送请求到: {LOGIN_ENDPOINT}')
    print(f'📋 请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}')
    print()
    
    try:
        # 发送登录请求
        response = requests.post(LOGIN_ENDPOINT, json=payload, timeout=10)
        
        print(f'📥 响应状态码: {response.status_code}')
        print(f'📥 响应头: {dict(response.headers)}')
        print(f'📥 响应体:')
        
        try:
            response_json = response.json()
            print(json.dumps(response_json, ensure_ascii=False, indent=2))
        except:
            print(response.text)
        
        print()
        
        if response.status_code == 200:
            print('✅ 登录成功！')
            return True
        else:
            print(f'❌ 登录失败（状态码: {response.status_code}）')
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f'❌ 连接错误: {e}')
        print('💡 确保后端服务运行在 http://localhost:8080')
        return False
    except Exception as e:
        print(f'❌ 错误: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # 测试已知账号
    test_login_api('13333268331', '123456')
