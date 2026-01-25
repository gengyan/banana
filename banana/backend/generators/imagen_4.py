"""
Imagen 4.0 图片生成器

使用 Imagen 4.0 Ultra (imagen-4.0-ultra-generate-001) 模型进行文生图
"""
import base64
import logging
import traceback
from typing import Optional
from google.genai import types

logger = logging.getLogger("果捷后端")


def generate_with_imagen(client, prompt: str, aspect_ratio: Optional[str] = None, image_size: Optional[str] = None) -> Optional[str]:
    """
    使用 Imagen 4.0 API 生成图片（纯图片生成模型）
    
    ⚠️ 重要：这是唯一的图片生成函数，不再混用文本生成模型
    
    实现细节：
    - 模型: imagen-4.0-ultra-generate-001（Imagen 4.0 Ultra 专门的图片生成模型）
    - API: client.models.generate_images（图片生成专用 API）
    - 配置: types.GenerateImagesConfig（图片生成专用配置）
    - 响应: response.generated_images[0].image.image_bytes（图片生成专用响应格式）
    
    参考文档：https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images
    
    注意：不使用 generate_content API，不使用 Gemini 模型
    
    Args:
        client: google.genai.Client 实例
        prompt: 图片生成提示词
        aspect_ratio: 长宽比，可选值: "1:1", "4:3", "3:4", "16:9", "9:16"
        image_size: 图片尺寸，可选值: "1K", "2K"（仅 Imagen 4.0 支持，Imagen 3 不支持）
    
    Returns:
        生成的图片 base64 data URL，失败返回 None
    """
    # 1. 使用 Imagen 4.0 Ultra 模型（支持提示增强等新特性）
    model_id = 'imagen-4.0-ultra-generate-001'
    logger.info(f"🖼️ 使用 Imagen 4.0 Ultra 生成图片, 模型: {model_id}")
    logger.info(f"📝 提示词: {prompt[:150]}...")
    
    # 2. 验证并规范化 aspect_ratio（必须指定有效值，不能为 None）
    # ⚠️ 重要：Google API 要求 aspect_ratio 必须明确传递，不能为 None
    valid_aspect_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
    if not aspect_ratio or aspect_ratio not in valid_aspect_ratios:
        logger.warning(f"⚠️ 无效的 aspect_ratio: {aspect_ratio}，将使用默认值 1:1")
        logger.info(f"💡 支持的 aspect_ratio 值: {valid_aspect_ratios}")
        aspect_ratio = "1:1"  # 确保始终有有效值
    
    # 3. 验证并规范化 image_size（必须明确传递，不能为 None）
    # ⚠️ 重要：Google API 要求 image_size 必须明确传递，不能为 None
    # 如果为 None，API 可能会忽略该参数，导致使用默认配置（1K）
    valid_image_sizes = ["1K", "2K"]
    if not image_size or image_size.upper() not in valid_image_sizes:
        if image_size:
            logger.warning(f"⚠️ 无效的 image_size: {image_size}，只支持 1K 和 2K，将使用默认值 2K")
        else:
            logger.info(f"ℹ️ image_size 未指定，将使用默认值 2K")
        logger.info(f"💡 支持的 image_size 值: {valid_image_sizes}")
        image_size = "2K"  # 默认使用 2K，确保明确传递
    
    # 规范化 image_size（确保是大写）
    image_size = image_size.upper()
    
    # 4. 正确的配置对象 (google-genai SDK 使用 GenerateImagesConfig)
    # Imagen 4.0 Ultra 支持的标准参数：
    # - aspect_ratio: 支持的值为 "1:1", "4:3", "3:4", "16:9", "9:16"（必须指定）
    # - image_size: 支持的值为 "1K", "2K"（必须明确传递，不能为 None）
    # - number_of_images: 生成图片数量
    # - output_mime_type: 输出格式，支持 "image/jpeg", "image/png"
    config_params = {
        "aspect_ratio": aspect_ratio,  # 已经确保不为 None
        "image_size": image_size,  # 已经确保不为 None
        "number_of_images": 1,
        "output_mime_type": "image/jpeg"
    }
    
    config = types.GenerateImagesConfig(**config_params)
    logger.info(f"📐 配置: aspect_ratio={aspect_ratio}, image_size={image_size}, number_of_images=1, output_mime_type=image/jpeg")
    
    try:
        # 3. 关键：使用 generate_images (google-genai SDK 使用复数形式)
        # Imagen 4.0 支持提示增强，响应中可能包含增强后的提示词
        logger.info(f"🚀 调用 Imagen API: model={model_id}")
        response = client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=config
        )
        
        # 4. 正确提取图片数据和元信息
        if response.generated_images and len(response.generated_images) > 0:
            generated_image = response.generated_images[0]
            
            # 4.1 检查图片数据
            if not hasattr(generated_image, 'image') or not generated_image.image:
                # 检查是否被安全过滤
                if hasattr(generated_image, 'rai_filtered_reason') and generated_image.rai_filtered_reason:
                    logger.warning(f"⚠️ 图片被安全过滤: {generated_image.rai_filtered_reason}")
                    raise Exception(f"图片被安全过滤: {generated_image.rai_filtered_reason}")
                raise Exception("图片数据为空")
            
            # 4.2 提取图片字节
            if not hasattr(generated_image.image, 'image_bytes'):
                raise Exception("响应中缺少 image_bytes 字段")
            
            image_bytes = generated_image.image.image_bytes
            if not image_bytes:
                raise Exception("image_bytes 为空")
            
            # 🔍 关键调试：打印原始 image_bytes 的前50个字节（用于对比）
            # 如果是 JPEG 图片，前几个字节应该是: b'\xff\xd8\xff\xe0' (JPEG 文件头)
            # Base64 编码后应该是: /9j/4AAQ... (Lzlq 是错误的)
            logger.info(f"🔍 [调试] 原始 image_bytes 类型: {type(image_bytes)}")
            logger.info(f"🔍 [调试] 原始 image_bytes 长度: {len(image_bytes)} bytes")
            if isinstance(image_bytes, bytes):
                # 打印原始字节的前50个（十六进制）
                hex_preview = image_bytes[:50].hex()
                logger.info(f"🔍 [调试] 原始 image_bytes 前50字节(hex): {hex_preview}")
                # 打印原始字节的前50个（如果可打印）
                try:
                    ascii_preview = image_bytes[:50].decode('latin-1', errors='replace')
                    logger.info(f"🔍 [调试] 原始 image_bytes 前50字节(ascii): {repr(ascii_preview)}")
                except:
                    pass
                # 直接对原始字节进行 base64 编码，查看前50个字符
                raw_b64_preview = base64.b64encode(image_bytes[:50]).decode('utf-8')
                logger.info(f"🔍 [调试] 原始 image_bytes 前50字节的 base64: {raw_b64_preview}")
            
            # 4.3 提取增强后的提示词（如果模型支持提示增强）
            enhanced_prompt = None
            if hasattr(generated_image, 'prompt') and generated_image.prompt:
                enhanced_prompt = generated_image.prompt
                logger.info(f"✨ Imagen 4.0 提示增强功能: 已检测到增强后的提示词")
                logger.info(f"   原始提示词: {prompt[:100]}...")
                logger.info(f"   增强提示词: {enhanced_prompt[:100]}...")
            
            # 4.4 获取 MIME 类型
            mime_type = "image/jpeg"
            if hasattr(generated_image, 'mime_type') and generated_image.mime_type:
                mime_type = generated_image.mime_type
            
            # 4.5 编码处理
            # 检查 image_bytes 到底是 bytes 还是 str
            if isinstance(image_bytes, str):
                logger.warning("⚠️ 检测到 image_bytes 已经是字符串格式，跳过 base64 编码")
                image_b64 = image_bytes
            else:
                # 只有是 bytes 类型时才编码
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 🔍 关键调试：此时 image_b64 应该是正常的 /9j/ 开头
            logger.info(f"🔍 [调试] 最终 base64 字符串前50字符: {image_b64[:50]}")
            logger.info(f"🔍 [调试] 编码后的 base64 字符串是否以 /9j/ 开头: {image_b64.startswith('/9j/')}")
            logger.info(f"🔍 [调试] 编码后的 base64 字符串是否以 Lzlq 开头: {image_b64.startswith('Lzlq')}")
            
            # 如果此时还是 Lzlq 开头，说明原始数据本身就有问题，需要对其进行一次解码
            if image_b64.startswith('Lzlq'):
                logger.error("❌ 检测到二次编码数据，尝试自动修复...")
                # 将 Lzlq... 解码回 /9j/...（解码一次即可，因为 Lzlq 是 /9j/ 的二次编码）
                try:
                    # 第一次解码：Lzlq... -> /9j/... (base64 字符串)
                    decoded_str = base64.b64decode(image_b64).decode('utf-8')
                    # 直接使用解码后的字符串（已经是正确的 base64 格式）
                    image_b64 = decoded_str
                    logger.info(f"✅ 自动修复完成，修复后的 base64 前50字符: {image_b64[:50]}")
                    logger.info(f"✅ 修复后是否以 /9j/ 开头: {image_b64.startswith('/9j/')}")
                except Exception as decode_error:
                    logger.error(f"❌ 自动修复失败: {decode_error}")
                    raise Exception(f"检测到二次编码但无法修复: {decode_error}")
            
            logger.info(f"✅ Imagen 4.0 生图成功")
            logger.info(f"   图片大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
            logger.info(f"   MIME 类型: {mime_type}")
            
            # 根据实际的 MIME 类型返回正确的 data URL
            data_url_prefix = f"data:{mime_type};base64,"
            final_data_url = f"{data_url_prefix}{image_b64}"
            
            # 🔍 关键调试：打印最终的 data URL 前50个字符
            logger.info(f"🔍 [调试] 最终 data URL 前50字符: {final_data_url[:50]}")
            
            return final_data_url
        else:
            raise Exception("响应中未生成任何图片")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Imagen 4.0 生图失败: {error_msg}")
        logger.error(f"📋 错误类型: {type(e).__name__}")
        
        # 检查常见错误类型
        error_lower = error_msg.lower()
        if any(kw in error_lower for kw in ['location', 'region', 'not supported', 'precondition']):
            logger.error("💡 提示：Imagen 模型在某些地区不可用，请检查 API 访问权限")
        elif 'invalid' in error_lower and 'argument' in error_lower:
            logger.error("💡 提示：请求参数无效，请检查配置参数是否符合要求")
        elif 'quota' in error_lower or 'limit' in error_lower:
            logger.error("💡 提示：API 配额或限制已达到上限")
        elif 'authentication' in error_lower or 'unauthorized' in error_lower:
            logger.error("💡 提示：API 密钥无效或认证失败")
        
        logger.error(f"📋 完整错误堆栈:\n{traceback.format_exc()}")
        return None
