"""
Imagen 3.0 Capability 图片生成器

使用 Imagen 3.0 Capability (imagen-3.0-capability-001) 模型进行文生图和图生图
支持参考图片（reference images）
"""
import os
import base64
import logging
import traceback
import io
from typing import Optional, List
from PIL import Image

logger = logging.getLogger("果捷后端")

# 导入 google.genai（新的统一 SDK）
try:
    from google import genai as genai_new
    from google.genai import types
    GEMINI_NEW_AVAILABLE = True
except ImportError:
    GEMINI_NEW_AVAILABLE = False
    logger.warning("⚠️ google.genai 模块不可用")


def _get_genai_client():
    """获取或创建 google.genai Client 实例（用于 Imagen 3.0 Capability）"""
    if not GEMINI_NEW_AVAILABLE:
        return None
    
    # 检查 Vertex AI 环境变量和服务账户凭据
    vertex_ai_project = os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    vertex_ai_location = os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    google_app_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # 强制使用 Vertex AI 模式
    if not vertex_ai_project:
        logger.error("❌ VERTEX_AI_PROJECT 未设置，无法使用 Vertex AI 模式")
        return None
    
    if not google_app_credentials:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS 未设置，无法使用 Vertex AI 模式")
        return None
    
    # 确保 GOOGLE_APPLICATION_CREDENTIALS 环境变量已设置
    if not os.path.exists(google_app_credentials):
        logger.error(f"❌ 服务账户凭据文件不存在: {google_app_credentials}")
        return None
    
    logger.info(f"🔧 使用 Vertex AI 模式（服务账户凭据）: project={vertex_ai_project}, location={vertex_ai_location}")
    
    try:
        # 强制设置环境变量（确保 SDK 能读取到）
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials
        
        # 客户端会自动从 GOOGLE_APPLICATION_CREDENTIALS 环境变量读取凭据
        client = genai_new.Client(
            vertexai=True,
            project=vertex_ai_project,
            location=vertex_ai_location
        )
        logger.info("✅ Vertex AI Client 创建成功（使用服务账户凭据）")
        return client
    except Exception as e:
        logger.error(f"❌ 创建 Vertex AI Client 失败: {e}")
        logger.error("⚠️ 请确认服务账户是否有 Vertex AI User 权限")
        return None


def generate_with_imagen_3_capability(prompt: str, reference_images: Optional[List[Image.Image]] = None,
                                      aspect_ratio: Optional[str] = None, resolution: Optional[str] = None,
                                      temperature: Optional[float] = None) -> Optional[str]:
    """
    使用 Imagen 3.0 模型进行图片生成（支持文生图和图生图）
    
    实现细节（根据参考代码）：
    - 文生图：使用 imagen-3.0-generate-001 + generate_images API
    - 图生图：使用 imagen-3.0-capability-001 + edit_image API
    - 支持参考图片（reference images）
    
    ⚠️ 重要：在所有 prompt 尾部硬编码拼接英文指令：
    ", professional typography, clean design, high resolution"
    
    Args:
        prompt: 图片生成提示词
        reference_images: 参考图片列表（PIL Image 对象），可选。如果为 None 或空列表，则为文生图模式
        aspect_ratio: 长宽比（可选）
        resolution: 图片分辨率（可选）
        temperature: 温度参数（可选，可能不被支持）
    
    Returns:
        生成的图片 base64 data URL，失败返回 None
    """
    has_reference_images = reference_images and len(reference_images) > 0
    mode_text = "图生图" if has_reference_images else "文生图"
    
    logger.info(f"🖼️ 使用 Imagen 3.0 Capability 进行{mode_text}")
    logger.info(f"📝 原始提示词: {prompt[:150]}...")
    logger.info(f"📸 参考图片数量: {len(reference_images) if reference_images else 0}")
    
    # 在 prompt 尾部硬编码拼接英文指令（根据参考代码，当前已禁用）
    ENHANCEMENT_SUFFIX = ", professional typography, clean design, high resolution"
    enhanced_prompt = prompt  # 增强词已禁用（用户要求）
    logger.info(f"📝 提示词: {enhanced_prompt[:200]}...")
    
    if not GEMINI_NEW_AVAILABLE:
        logger.error("❌ google.genai 模块不可用，无法使用 Imagen 3.0 Capability")
        return None
    
    client = _get_genai_client()
    if not client:
        logger.error("❌ 无法创建 genai Client")
        return None
    
    try:
        # 根据参考代码：
        # - 文生图：使用 imagen-3.0-generate-001 + generate_images API
        # - 图生图：使用 imagen-3.0-capability-001 + edit_image API
        
        # 验证并规范化 aspect_ratio
        valid_aspect_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
        if not aspect_ratio or aspect_ratio not in valid_aspect_ratios:
            logger.warning(f"⚠️ 无效的 aspect_ratio: {aspect_ratio}，将使用默认值 1:1")
            aspect_ratio = "1:1"
        
        # 验证并规范化 resolution（转换为 sample_image_size）
        # 根据参考代码，使用 sample_image_size="2K"（3.0 系列 2K 最稳）
        sample_image_size = "2K"  # 默认使用 2K（参考代码推荐）
        
        if resolution:
            resolution_upper = resolution.upper()
            if resolution_upper == "2K":
                sample_image_size = "2K"
            elif resolution_upper == "1K":
                sample_image_size = "1K"
            elif resolution_upper == "4K":
                logger.warning("⚠️ Imagen 3.0 不支持 4K，将使用 2K")
                sample_image_size = "2K"
            else:
                logger.warning(f"⚠️ 不支持的分辨率: {resolution_upper}，将使用默认值 2K")
                sample_image_size = "2K"
        else:
            sample_image_size = "2K"  # 默认使用 2K（参考代码推荐）
        
        logger.info(f"📐 sample_image_size: {sample_image_size}")
        
        if has_reference_images:
            # ========== 图生图模式：使用 imagen-3.0-capability-001 + edit_image API ==========
            logger.info(f"📸 图生图模式：使用 {len(reference_images)} 张参考图片")
            model_id = 'imagen-3.0-capability-001'  # 图生图使用 capability 模型
            logger.info(f"🎯 使用模型: {model_id} (图生图模式)")
            
            # 处理参考图片（edit_image 通常只需要一张参考图片）
            if len(reference_images) > 1:
                logger.warning(f"⚠️ edit_image API 通常只支持一张参考图片，将使用第一张")
            
            base_image = reference_images[0]
            try:
                # 转换为 RGB 模式
                if base_image.mode != 'RGB':
                    base_image = base_image.convert('RGB')
                
                # 限制图片大小（避免过大）
                max_size = 2048
                if base_image.width > max_size or base_image.height > max_size:
                    base_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                logger.info(f"   参考图片处理完成，尺寸: {base_image.size}, 模式: {base_image.mode}")
            except Exception as e:
                logger.error(f"❌ 处理参考图片失败: {e}")
                return None
            
            # 使用 edit_image API（根据参考代码）
            # edit_image API 需要 reference_images 列表，可以直接传递 PIL Image 对象
            logger.info("📤 调用 edit_image API...")
            logger.info(f"   模型: {model_id}")
            logger.info(f"   端点: Vertex AI")
            logger.info(f"   项目: {os.getenv('VERTEX_AI_PROJECT', 'N/A')}")
            logger.info(f"   位置: {os.getenv('VERTEX_AI_LOCATION', 'N/A')}")
            logger.info(f"   提示词: {enhanced_prompt[:200]}...")
            logger.info(f"   参考图片: 1 张（edit_image 通常只支持一张）")
            
            # 使用 edit_image API（直接传递 PIL Image 对象列表）
            # 根据 SDK 文档，reference_images 可以是 PIL Image 对象列表
            response = client.models.edit_image(
                model=model_id,
                prompt=enhanced_prompt,
                reference_images=[base_image],  # 直接传递 PIL Image 对象列表
                # config 参数可选，如果需要可以添加 EditImageConfig
            )
            logger.info("✅ 使用 edit_image API 成功（图生图）")
        else:
            # ========== 文生图模式：使用 imagen-3.0-generate-001 + generate_images API ==========
            logger.info("📝 文生图模式")
            model_id = 'imagen-3.0-generate-001'  # 文生图使用 generate 模型
            logger.info(f"🎯 使用模型: {model_id} (文生图模式)")
            
            # 根据参考代码，使用 imageSize="2K"（3.0 系列 2K 最稳）
            # 注意：SDK 不支持 sample_image_size，需要使用 imageSize
            config = types.GenerateImagesConfig(
                imageSize=sample_image_size,  # 使用 "2K" 格式（SDK 使用 imageSize 参数）
                aspectRatio=aspect_ratio
            )
            
            logger.info(f"📤 发送请求到 Google API (Vertex AI)")
            logger.info(f"   模型: {model_id}")
            logger.info(f"   端点: Vertex AI")
            logger.info(f"   项目: {os.getenv('VERTEX_AI_PROJECT', 'N/A')}")
            logger.info(f"   位置: {os.getenv('VERTEX_AI_LOCATION', 'N/A')}")
            logger.info(f"   提示词: {enhanced_prompt[:200]}...")
            logger.info(f"   配置: imageSize={sample_image_size}, aspect_ratio={aspect_ratio}")
            
            response = client.models.generate_images(
                model=model_id,
                prompt=enhanced_prompt,
                config=config
            )
        
        # 提取生成的图片
        # 注意：edit_image 和 generate_images 的响应格式可能不同
        image_bytes = None
        mime_type = 'image/jpeg'
        
        if has_reference_images:
            # 图生图模式：edit_image API 的响应格式
            # 根据 SDK 文档示例，edit_image 返回 response.generated_images[0].image
            if hasattr(response, 'generated_images') and response.generated_images:
                generated_image = response.generated_images[0]
                if hasattr(generated_image, 'image') and generated_image.image:
                    if hasattr(generated_image.image, 'image_bytes'):
                        image_bytes = generated_image.image.image_bytes
                        mime_type = getattr(generated_image.image, 'mime_type', 'image/jpeg')
                    else:
                        logger.error("❌ generated_image.image 缺少 image_bytes 字段")
                        return None
                else:
                    logger.error("❌ generated_image 缺少 image 字段")
                    return None
            elif hasattr(response, 'edited_image') and response.edited_image:
                # 如果 edit_image 返回 edited_image 格式
                if hasattr(response.edited_image, 'image_bytes'):
                    image_bytes = response.edited_image.image_bytes
                    mime_type = getattr(response.edited_image, 'mime_type', 'image/jpeg')
                elif hasattr(response.edited_image, 'image') and response.edited_image.image:
                    if hasattr(response.edited_image.image, 'image_bytes'):
                        image_bytes = response.edited_image.image.image_bytes
                        mime_type = getattr(response.edited_image.image, 'mime_type', 'image/jpeg')
            else:
                logger.error("❌ edit_image 响应中没有找到图片数据")
                logger.error(f"   响应对象类型: {type(response)}")
                logger.error(f"   响应对象属性: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                return None
        else:
            # 文生图模式：generate_images API 的响应格式
            if hasattr(response, 'generated_images') and response.generated_images:
                generated_image = response.generated_images[0]
                if hasattr(generated_image, 'image') and generated_image.image:
                    if hasattr(generated_image.image, 'image_bytes'):
                        image_bytes = generated_image.image.image_bytes
                        mime_type = getattr(generated_image.image, 'mime_type', 'image/jpeg')
            else:
                logger.error("❌ generate_images 响应中没有找到图片数据")
                logger.error(f"   响应对象类型: {type(response)}")
                logger.error(f"   响应对象属性: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                return None
        
        if not image_bytes:
            logger.error("❌ 无法提取图片数据")
            return None
        
        logger.info(f"✅ Imagen 3.0 {mode_text}成功")
        logger.info(f"   图片大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        
        # 转换为 base64 data URL
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        data_url_prefix = f"data:{mime_type};base64,"
        return f"{data_url_prefix}{image_b64}"
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Imagen 3.0 Capability {mode_text}失败: {error_msg}")
        logger.error(f"📋 错误类型: {type(e).__name__}")
        
        # 检查是否是模型端点无效的错误
        if 'invalid endpoint' in error_msg.lower() or 'invalid_argument' in error_msg.lower():
            logger.error("⚠️ 模型端点无效，可能的原因：")
            logger.error("   1. imagen-3.0-capability-001 可能不支持 generate_images API（主要用于图片编辑）")
            logger.error("   2. 模型在该区域不可用")
            logger.error("   3. 账户没有访问权限")
            logger.error("💡 建议：如果文生图失败，可能需要使用 imagen-3.0-generate-001 或其他支持文生图的模型")
        
        logger.error(f"📋 完整错误堆栈:\n{traceback.format_exc()}")
        return None
