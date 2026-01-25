#!/usr/bin/env python3
"""
测试后端图片生成的完整流程
"""

import requests
import json
import base64
from pathlib import Path
import sys

# 配置
BACKEND_URL = "http://localhost:8000"
API_ENDPOINT = "/api/process-json3"

def test_image_generation():
    """测试图片生成"""
    print("=" * 80)
    print("测试 Gemini 3 Pro 图片生成")
    print("=" * 80)
    
    # 测试请求
    payload = {
        "message": "a beautiful sunset",
        "mode": "banana_pro",
        "temperature": 0.8
    }
    
    print(f"\n📤 发送请求到: {BACKEND_URL}{API_ENDPOINT}")
    print(f"📝 请求数据: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        # 发送请求
        response = requests.post(
            f"{BACKEND_URL}{API_ENDPOINT}",
            json=payload,
            timeout=600,
            stream=False
        )
        
        print(f"✅ HTTP 状态码: {response.status_code}")
        print(f"📋 响应头:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()
        
        # 检查状态码
        if response.status_code != 200:
            print(f"❌ HTTP 错误: {response.status_code}")
            print(f"响应体: {response.text[:500]}")
            return False
        
        # 检查 Content-Type
        content_type = response.headers.get('content-type', '')
        print(f"🔍 Content-Type: {content_type}")
        
        if 'application/json' in content_type:
            print("⚠️ 响应是 JSON（可能是错误）")
            try:
                error_data = response.json()
                print(f"错误信息: {json.dumps(error_data, indent=2)}")
            except:
                print(f"无法解析 JSON: {response.text[:500]}")
            return False
        
        elif 'image' in content_type:
            print("✅ 响应是图片")
            
            # 获取图片数据
            image_data = response.content
            print(f"📏 图片大小: {len(image_data)} bytes ({len(image_data) / 1024 / 1024:.2f} MB)")
            
            # 检查文件头
            print(f"\n🔍 文件头检查:")
            print(f"  前 20 字节（16进制）: {image_data[:20].hex()}")
            
            # 识别格式
            if image_data.startswith(b'\x89PNG'):
                print("  ✅ 识别为 PNG")
                format_ext = 'png'
            elif image_data.startswith(b'\xff\xd8\xff'):
                print("  ✅ 识别为 JPEG")
                format_ext = 'jpg'
            else:
                print(f"  ❌ 未知格式！")
                format_ext = 'bin'
            
            # 保存图片
            output_path = Path(f"/tmp/test_image.{format_ext}")
            output_path.write_bytes(image_data)
            print(f"\n💾 图片已保存到: {output_path}")
            
            # 尝试用 PIL 验证
            try:
                from PIL import Image
                import io
                
                img = Image.open(io.BytesIO(image_data))
                print(f"✅ PIL 验证成功")
                print(f"  格式: {img.format}")
                print(f"  尺寸: {img.size}")
                print(f"  模式: {img.mode}")
                
                return True
                
            except Exception as pil_error:
                print(f"❌ PIL 验证失败: {pil_error}")
                return False
        
        else:
            print(f"❌ 未知的 Content-Type: {content_type}")
            print(f"响应体（前 500 字节）: {response.text[:500]}")
            return False
    
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        print("请确保后端服务已启动（python main.py）")
        return False
    
    except requests.exceptions.Timeout:
        print("❌ 请求超时（超过 600 秒）")
        return False
    
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_image_generation()
    sys.exit(0 if success else 1)
