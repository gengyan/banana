#!/usr/bin/env python3
"""
测试用户认证 API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """测试注册"""
    print("测试注册...")
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "account": "test@example.com",
        "password": "123456",
        "nickname": "测试用户"
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_login():
    """测试登录"""
    print("\n测试登录 manager...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "account": "manager",
        "password": "075831"
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    if response.status_code == 200:
        return response.json().get("session_token")
    return None

def test_get_me(session_token):
    """测试获取用户信息"""
    print(f"\n测试获取用户信息 (session_token: {session_token[:20]}...)")
    response = requests.post(f"{BASE_URL}/api/auth/me", json={
        "session_token": session_token
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("=" * 50)
    print("测试用户认证 API")
    print("=" * 50)
    
    # 测试注册
    # test_register()
    
    # 测试登录
    token = test_login()
    
    # 测试获取用户信息
    if token:
        test_get_me(token)
    
    print("\n" + "=" * 50)
