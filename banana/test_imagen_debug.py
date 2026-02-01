#!/usr/bin/env python3
"""
测试 Imagen 接口并查看详细日志
"""
import requests
import json
import time

API_BASE = "http://127.0.0.1:8080"

def test_imagen():
    """测试 Imagen 接口"""
    print("🧪 测试 /api/imagen")
    print("-" * 60)
    
    url = f"{API_BASE}/api/imagen"
    data = {
        "message": "一只可爱的黑色小猫坐在窗边",
        "aspect_ratio": "1:1",
        "image_size": "2K"
    }
    
    print(f"📝 提示词: {data['message']}")
    print(f"📐 参数: aspect_ratio={data['aspect_ratio']}, image_size={data['image_size']}")
    
    try:
        print("\n⏳ 等待响应...")
        start_time = time.time()
        response = requests.post(url, data=data, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"⏱️ 耗时: {elapsed:.1f}秒")
        print(f"📊 HTTP 状态码: {response.status_code}")
        print(f"📋 响应类型: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            print(f"✅ 请求成功")
            print(f"📦 响应大小: {len(response.content)} bytes")
            
            # 判断响应是 blob 还是 JSON
            if 'image' in response.headers.get('content-type', '').lower():
                print(f"🖼️ 收到图片数据（blob）")
            else:
                try:
                    result = response.json()
                    print(f"📝 JSON 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📝 响应内容: {response.text[:500]}")
        else:
            print(f"❌ 请求失败")
            try:
                error = response.json()
                print(f"❌ 错误响应: {json.dumps(error, indent=2, ensure_ascii=False)}")
            except:
                print(f"❌ 错误响应: {response.text}")
    
    except requests.exceptions.Timeout:
        print("⏱️ 请求超时（60秒）")
    except Exception as e:
        print(f"❌ 异常: {str(e)}")

if __name__ == "__main__":
    test_imagen()
    print("\n\n⏳ 请查看后端日志中的详细信息...")
    print("命令: tail -50 /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend.log | grep -A 50 '🔍'")
