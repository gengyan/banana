#!/usr/bin/env python3
"""
测试登录 API 端点
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
          #!/usr/bin/env python3
"""
测试登录 API 端点
"""
import requests
import json

# API 端点
BAnd"""
测试登录 API t:? """
import requests
ime.imxtimport json

#  
# API 端
  BASE  
      LOGIN_ENDPOINT tatus_code == 200:
 
def test_login_api(account, password):
           """测试登录 API"""
    print(      print('=' * 70)
    p败（状态码: {resp    print('=' * 70)
    print()
    
    # ?e
            
    except request   xc    payload = {
        a        "accouri        "password": passwo')    }
    
    print(f'📤?   ?  ??   print(f'📋 请求数据0')
        return False    print()
    
    try:
        # 发送登录请求
        response = requests.
i    
    t =   __       :
        response = requests          
        print(f'?', '123456')
