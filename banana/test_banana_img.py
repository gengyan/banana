#!/usr/bin/env python3
"""
测试 /api/banana-img 生图功能的诊断脚本
"""
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8080"
API_ENDPOINT = f"{BASE_URL}/api/banana-img"

def test_banana_img():
    """测试生图接口"""
    print("=" * 60)
    print("🧪 开始测试 /api/banana-img")
    print("=" * 60)
    
    # 测试 1: 简单的文生图
    print("\n📝 测试 1: 文生图 (JSON 请求)")
    print("-" * 60)
    
    payload = {
        "message": "一只可爱的红色小狐狸",
        "mode": "banana",
        "aspect_ratio": "1:1"
    }
    
    print(f"📤 发送请求: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            timeout=120,
            stream=False
        )
        elapsed = time.time() - start_time
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📊 响应耗时: {elapsed:.2f}s")
        print(f"📊 响应头信息:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        if response.status_code == 200:
            # 返回二进制图片
            if response.content:
                print(f"✅ 成功！收到 {len(response.content)} 字节的图片数据")
                # 保存到本地
                with open('/tmp/test_image.jpg', 'wb') as f:
                    f.write(response.content)
                print(f"💾 已保存到 /tmp/test_image.jpg")
            else:
                print("❌ 错误：响应为空")
        else:
            # 返回 JSON 错误
            try:
                error_data = response.json()
                print(f"❌ 错误响应:")
                print(json.dumps(error_data, ensure_ascii=False, indent=2))
            except:
                print(f"❌ 错误响应文本: {response.text[:500]}")
    
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接失败: {e}")
        print("⚠️  后端服务可能未运行，请先执行: python backend/main.py")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ 请求超时: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_banana_img()
    sys.exit(0 if success else 1)
