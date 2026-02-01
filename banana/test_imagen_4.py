#!/usr/bin/env python3
"""
测试 Imagen 4 接口
"""
import requests
import json
import base64

API_BASE = "http://127.0.0.1:8080"

def test_imagen_json():
    """测试 Imagen 4 JSON 接口（文生图）"""
    print("🧪 测试 /api/imagen-json (文生图)")
    print("-" * 60)
    
    url = f"{API_BASE}/api/imagen-json"
    data = {
        "prompt": "一只可爱的猫咪坐在窗边看雨，水彩画风格",
        "aspect_ratio": "1:1",
        "image_size": "2K"
    }
    
    print(f"📝 提示词: {data['prompt']}")
    print(f"📐 参数: aspect_ratio={data['aspect_ratio']}, image_size={data['image_size']}")
    
    try:
        response = requests.post(url, json=data, timeout=60)
        print(f"📊 HTTP 状态码: {response.status_code}")
        
        result = response.json()
        print(f"✅ 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            image_url = result.get("image_url")
            if image_url:
                # 检查图片格式
                if image_url.startswith("data:image/"):
                    print(f"🖼️ 图片格式: {image_url.split(';')[0].split(':')[1]}")
                    print(f"📏 Base64 长度: {len(image_url.split(',')[1])} 字符")
                    
                    # 保存图片到文件
                    image_data = image_url.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    
                    output_file = "test_imagen_output.jpg"
                    with open(output_file, "wb") as f:
                        f.write(image_bytes)
                    print(f"💾 图片已保存到: {output_file}")
                    print(f"📦 文件大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        else:
            print(f"❌ 生成失败: {result.get('message')}")
            if "error_code" in result:
                print(f"❌ 错误代码: {result['error_code']}")
            if "error_detail" in result:
                print(f"❌ 错误详情: {result['error_detail']}")
    
    except requests.exceptions.Timeout:
        print("⏱️ 请求超时（60秒）")
    except Exception as e:
        print(f"❌ 异常: {str(e)}")

def test_imagen_form():
    """测试 Imagen 4 FormData 接口（图生图）"""
    print("\n🧪 测试 /api/imagen (FormData，图生图)")
    print("-" * 60)
    
    url = f"{API_BASE}/api/imagen"
    data = {
        "prompt": "将这张图片转换为油画风格",
        "aspect_ratio": "16:9",
        "image_size": "2K"
    }
    
    print(f"📝 提示词: {data['prompt']}")
    print(f"📐 参数: aspect_ratio={data['aspect_ratio']}, image_size={data['image_size']}")
    print(f"ℹ️ 注意: 当前版本图生图功能暂未实现，将使用纯文生图")
    
    try:
        response = requests.post(url, data=data, timeout=60)
        print(f"📊 HTTP 状态码: {response.status_code}")
        
        result = response.json()
        print(f"✅ 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            image_url = result.get("image_url")
            if image_url:
                # 检查图片格式
                if image_url.startswith("data:image/"):
                    print(f"🖼️ 图片格式: {image_url.split(';')[0].split(':')[1]}")
                    print(f"📏 Base64 长度: {len(image_url.split(',')[1])} 字符")
        else:
            print(f"❌ 生成失败: {result.get('message')}")
    
    except requests.exceptions.Timeout:
        print("⏱️ 请求超时（60秒）")
    except Exception as e:
        print(f"❌ 异常: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎨 Imagen 4 接口测试")
    print("=" * 60)
    
    # 测试 JSON 接口
    test_imagen_json()
    
    # 测试 FormData 接口
    # test_imagen_form()  # 暂时注释，因为还未实现图生图
