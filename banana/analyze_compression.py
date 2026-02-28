#!/usr/bin/env python3
"""
快速对比脚本：查看当前的质量设置和预期效果
"""
import os
import sys
from pathlib import Path

# 添加后端路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

def analyze_compression_settings():
    """分析当前压缩设置"""
    print("=" * 70)
    print("🔍 Banana Pro 图片压缩设置分析")
    print("=" * 70)
    print()
    
    # 检查 Gemini 3 Pro 配置
    print("📋 当前配置信息：")
    print("-" * 70)
    
    # 查找关键的质量设置行
    gems_3_file = Path(__file__).parent / 'backend/generators/gemini_3_pro_image.py'
    if gems_3_file.exists():
        with open(gems_3_file, 'r') as f:
            lines = f.readlines()
            
        # 查找质量设置
        print("\n1️⃣ 参考图编码质量:")
        for i, line in enumerate(lines, 1):
            if 'image.save' in line and 'quality' in line:
                print(f"   行 {i}: {line.strip()}")
        
        # 查找输出格式设置
        print("\n2️⃣ 输出格式设置:")
        for i, line in enumerate(lines, 1):
            if 'output_mime_type' in line:
                print(f"   行 {i}: {line.strip()}")
    
    print("\n" + "-" * 70)
    print("📊 预期效果对比：")
    print("-" * 70)
    
    configurations = [
        {
            "名称": "当前配置",
            "参考图": "JPEG Q85",
            "输出格式": "JPEG",
            "输出质量": "Q85",
            "文件大小": "~700KB",
            "质量跟迹": "中等（可见压缩）",
            "成本": "低 💰"
        },
        {
            "名称": "推荐配置",
            "参考图": "JPEG Q90+",
            "输出格式": "JPEG",
            "输出质量": "Q90",
            "文件大小": "~1.2MB",
            "质量跟迹": "高（几乎无损）",
            "成本": "中等 💰💰"
        },
        {
            "名称": "最高质量",
            "参考图": "PNG",
            "输出格式": "PNG",
            "输出质量": "100%（无损）",
            "文件大小": "~6-8MB",
            "质量跟迹": "完美无损 👑",
            "成本": "高 💰💰💰"
        },
    ]
    
    # 打印表格
    headers = ["配置", "参考图", "输出格式", "输出质量", "文件大小", "质量感知", "成本"]
    col_widths = [10, 12, 10, 12, 10, 18, 10]
    
    # 打印表头
    for i, header in enumerate(headers):
        print(f"{header:<{col_widths[i]}}", end="")
    print()
    print("-" * sum(col_widths))
    
    # 打印数据
    for config in configurations:
        cols = [
            config["名称"],
            config["参考图"],
            config["输出格式"],
            config["输出质量"],
            config["文件大小"],
            config["质量跟迹"],
            config["成本"]
        ]
        for i, col in enumerate(cols):
            print(f"{col:<{col_widths[i]}}", end="")
        print()
    
    print()
    print("=" * 70)
    print("💡 建议：")
    print("-" * 70)
    print("""
目前的设计是为了：
  1. 减少 API 传输数据量
  2. 降低服务成本
  3. 提高响应速度

如果你的用户对图片质量敏感，建议：
  ✅ 修改参考图质量从 85 提升到 90-95
  ✅ 保持输出格式为 JPEG（平衡选择）
  ✅ 或添加用户选择：低质量/高质量/最高质量

这样可以在不显著增加成本的情况下，提升用户体验。
    """)
    
    print("=" * 70)
    print("📖 查看详细分析：BANANA_PRO_SIZE_ANALYSIS.md")
    print("=" * 70)

if __name__ == "__main__":
    analyze_compression_settings()
