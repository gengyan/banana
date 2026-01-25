"""
生成器模块

包含不同模型的生成函数：
- imagen_4: Imagen 4.0 模型（文生图）
- gemini_3_pro_image: Gemini 3 Pro Image 模型（图生图）
- prompt_optimizer: Gemini 2.0 Flash Exp 模型（提示词优化）
- chat: Gemini 2.0 Flash Exp 模型（文本聊天）
"""

from .imagen_4 import generate_with_imagen
from .gemini_3_pro_image import generate_with_gemini_image3
from .imagen_3_capability import generate_with_imagen_3_capability
from .gemini_2_5_flash_image import generate_with_gemini_2_5_flash_image
from .prompt_optimizer import optimize_prompt
from .chat import chat

# 向后兼容：保留旧名称
generate_with_gemini_image = generate_with_gemini_image3

__all__ = [
    'generate_with_imagen',
    'generate_with_gemini_image3',  # 新的函数名（Gemini 3 Pro）
    'generate_with_gemini_image',   # 向后兼容的别名
    'generate_with_imagen_3_capability',
    'generate_with_gemini_2_5_flash_image',
    'optimize_prompt',
    'chat',
]
