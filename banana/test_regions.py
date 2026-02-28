#!/usr/bin/env python3
"""
测试 Gemini 3 Pro 在不同区域的可用性
"""
import sys
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 加载环境变量
env_path = Path(__file__).parent / "backend" / ".env"
if not env_path.exists():
    env_path = find_dotenv()
load_dotenv(env_path)

# 设置凭证
cred_path = Path(__file__).parent / "backend" / "google-key.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)

PROJECT_ID = os.getenv("VERTEX_AI_PROJECT", "gen-lang-client-0801638297")
MODEL_NAME = "gemini-3-pro-image-preview"

# 待测试的区域（包括 global）
REGIONS = {
    "Americas": [
        "us-central1",  # 爱荷华州
        "us-east4",     # 北弗吉尼亚
        "us-west1",     # 俄勒冈
    ],
    "Asia Pacific": [
        "asia-east1",      # 台湾
        "asia-northeast1",  # 东京
        "asia-southeast1",  # 新加坡
    ],
    "Europe": [
        "europe-west1",  # 比利时
        "europe-west4",  # 荷兰
        "europe-west9",  # 巴黎
    ],
    "Global": [
        "global",  # 全球
    ]
}

def test_region(region: str) -> dict:
    """测试特定区域是否可用"""
    try:
        print(f"  测试 {region}...", end=" ", flush=True)
        
        # 使用与后端相同的方式创建客户端
        from google import genai
        
        try:
            client = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=region,
            )
        except TypeError as e:
            # vertexai 可能不支持某些参数
            print(f"❌ 初始化失败")
            return {
                "region": region,
                "status": "init_error",
                "error": str(e)[:150]
            }
        
        # 尝试获取模型信息
        try:
            model = client.models.get(MODEL_NAME)
            print(f"✅ 成功")
            return {
                "region": region,
                "status": "success",
            }
        except Exception as model_err:
            error_str = str(model_err)
            
            if "404" in error_str or "not found" in error_str.lower():
                print(f"❌ 模型不可用 (404)")
                status = "not_found"
            elif "permission" in error_str.lower() or "access" in error_str.lower():
                print(f"❌ 权限拒绝")
                status = "permission_denied"
            else:
                print(f"❌ {type(model_err).__name__}")
                status = "model_error"
            
            return {
                "region": region,
                "status": status,
                "error": error_str[:150]
            }
    
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}")
        return {
            "region": region,
            "status": "error",
            "error": str(e)[:150]
        }

def main():
    print(f"\n🔍 测试 Gemini 3 Pro 在各区域的可用性")
    print(f"📍 项目 ID: {PROJECT_ID}")
    print(f"🤖 模型: {MODEL_NAME}")
    print("=" * 70)
    
    successful_regions = []
    
    for region_group, regions in REGIONS.items():
        print(f"\n{region_group}:")
        
        for region in regions:
            result = test_region(region)
            
            if result["status"] == "success":
                successful_regions.append(region)
    
    # 输出总结
    print("\n" + "=" * 70)
    print("📊 测试总结:")
    print("=" * 70)
    
    if successful_regions:
        print(f"\n✅ 可用区域 ({len(successful_regions)}):")
        for region in successful_regions:
            print(f"   • {region}")
        print(f"\n💡 推荐使用: {successful_regions[0]}")
    else:
        print("\n⚠️  没有找到可用的区域")
        print("   可能的原因:")
        print("   1. 模型 (gemini-3-pro-image-preview) 当前在所有区域都不可用")
        print("   2. 项目还未获得该模型的访问权限或模型名称不正确")
        print("   3. 使用 'gemini-3-pro' 代替 'gemini-3-pro-image-preview'")
    
    return successful_regions

if __name__ == "__main__":
    successful = main()
    sys.exit(0 if successful else 1)
