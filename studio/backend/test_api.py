#!/usr/bin/env python3
"""
测试后端 API 的脚本
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    """测试根路径"""
    print("测试根路径...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_chat():
    """测试聊天接口"""
    print("\n测试聊天接口...")
    try:
        data = {
            "message": "你好，请用一句话介绍你自己",
            "mode": "chat",
            "history": []
        }
        response = requests.post(f"{BASE_URL}/api/chat", json=data)
        print(f"✅ 状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 响应: {result.get('response', '')[:100]}...")
            print(f"✅ 成功: {result.get('success', False)}")
        else:
            print(f"❌ 错误响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_process():
    """测试统一处理接口"""
    print("\n测试统一处理接口...")
    try:
        data = {
            "message": "你好",
            "mode": "chat",
            "history": []
        }
        response = requests.post(f"{BASE_URL}/api/process", json=data)
        print(f"✅ 状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 响应: {result.get('response', '')[:100]}...")
        else:
            print(f"❌ 错误响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("后端 API 测试")
    print("=" * 50)
    
    results = []
    results.append(test_root())
    results.append(test_chat())
    results.append(test_process())
    
    print("\n" + "=" * 50)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 50)

