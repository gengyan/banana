"""
Gemini 2.5 Flash Image 图片生成器

使用 Gemini 2.5 Flash Image (gemini-2.5-flash-image) 模型进行文生图和图生图
"""
import os
import base64
import logging
import traceback
import io
from pathlib import Path
from typing import Optional, List
from PIL import Image

# ⚠️ 重要：加载环境变量（确保能读取到 .env 文件中的配置）
try:
    from dotenv import load_dotenv, find_dotenv
    
    # 自动查找并加载 .env 文件
    env_file = find_dotenv()
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
        temp_logger = logging.getLogger("果捷后端")
        temp_logger.info(f"✅ [gemini_2_5_flash_image] 已加载环境变量文件: {env_file}")
    else:
        # 手动查找 backend/.env
        current_file = Path(__file__).resolve()
        env_path = current_file.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            temp_logger = logging.getLogger("果捷后端")
            temp_logger.info(f"✅ [gemini_2_5_flash_image] 已加载环境变量文件: {env_path}")
        else:
            load_dotenv(override=False)
            temp_logger = logging.getLogger("果捷后端")
            temp_logger.info("✅ [gemini_2_5_flash_image] 已尝试加载环境变量")
except ImportError:
    temp_logger = logging.getLogger("果捷后端")
    temp_logger.warning("⚠️ [gemini_2_5_flash_image] python-dotenv 未安装，无法自动加载 .env 文件")

logger = logging.getLogger("果捷后端")

# ========== 代理配置 ==========
# ⚠️ 重要：检测运行环境，只在本地开发环境使用代理
# 在 Google Cloud Run 等云端环境中，不需要代理（直接访问 Google 服务）
def _should_use_proxy():
    """判断是否应该使用代理"""
    # 检测是否在 Cloud Run 环境（通过 K_SERVICE 环境变量）
    if os.getenv('K_SERVICE'):
        logger.info("🌐 [gemini_2_5_flash_image] 检测到 Cloud Run 环境，不使用代理")
        return False
    
    # 检测是否在其他云端环境
    if os.getenv('GAE_ENV') or os.getenv('GOOGLE_CLOUD_PROJECT'):
        # 如果明确设置了 DISABLE_PROXY，则不使用代理
        if os.getenv('DISABLE_PROXY', '').lower() == 'true':
            logger.info("🌐 [gemini_2_5_flash_image] 检测到云端环境且 DISABLE_PROXY=true，不使用代理")
            return False
    
    # 本地开发环境：检查代理是否可用
    PROXY_HOST = os.getenv('PROXY_HOST', '127.0.0.1')
    PROXY_PORT = os.getenv('PROXY_PORT', '29290')
    PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"
    
    # 如果环境变量中已经设置了代理，使用环境变量的值
    if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
        proxy_url = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
        logger.info(f"🔗 [gemini_2_5_flash_image] 使用环境变量中的代理: {proxy_url}")
        return True
    
    # 本地开发环境：设置代理
    logger.info(f"🔗 [gemini_2_5_flash_image] 本地开发环境，设置代理: HTTP_PROXY={PROXY_URL}, HTTPS_PROXY={PROXY_URL}")
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
    return True

# 根据环境决定是否使用代理
_should_use_proxy()

# 导入 google.genai（新的统一 SDK）


def _detect_image_format(image_bytes: bytes) -> str:
    """
    检测图片的实际格式（优先使用 PIL，回退到 magic bytes）
    
    ⚠️ 重要：Gemini 系列更倾向于输出 PNG 格式，因此默认回退到 PNG
    
    Args:
        image_bytes: 图片的二进制数据
    
    Returns:
        MIME 类型字符串，例如 'image/png' 或 'image/jpeg'
    """
    if not image_bytes:
        logger.warning("⚠️ _detect_image_format: image_bytes 为空，返回默认 PNG")
        return 'image/png'
    
    if len(image_bytes) < 4:
        logger.warning(f"⚠️ _detect_image_format: 数据长度不足 ({len(image_bytes)} bytes < 4)，返回默认 PNG")
        return 'image/png'
    
    # ⚠️ 优先使用 PIL 检测（最可靠的方法）
    logger.info("=" * 80)
    logger.info("🔧 [解析代码] 开始使用 PIL 检测图片格式")
    logger.info(f"   数据大小: {len(image_bytes)} bytes")
    logger.info(f"   前100字节（十六进制）: {bytes(image_bytes[:100]).hex()}")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()  # 强制加载图片数据，确保格式检测准确
        img_format = img.format
        
        logger.info(f"   PIL.Image.open() 调用成功")
        logger.info(f"   img.format: {img_format}")
        logger.info(f"   图片尺寸: {img.size[0]}x{img.size[1]} pixels")
        
        if img_format:
            format_lower = img_format.lower()
            logger.info(f"✅ _detect_image_format: PIL 检测到格式: {format_lower} (图片尺寸: {img.size[0]}x{img.size[1]})")
            
            if format_lower == 'png':
                logger.info("   返回结果: image/png")
                return 'image/png'
            elif format_lower in ['jpeg', 'jpg']:
                logger.info("   返回结果: image/jpeg")
                return 'image/jpeg'
            else:
                logger.warning(f"⚠️ _detect_image_format: PIL 检测到未知格式: {format_lower}，返回默认 PNG")
                return 'image/png'
        else:
            logger.warning("⚠️ _detect_image_format: PIL 无法识别格式，尝试使用 magic bytes 检测")
    except Exception as e:
        logger.warning(f"⚠️ PIL 检测图片格式失败: {str(e)}，尝试使用 magic bytes 检测")
        logger.warning(f"   错误类型: {type(e).__name__}")
        logger.warning(f"   错误详情: {traceback.format_exc()}")
    
    # 回退到 magic bytes 检测（如果 PIL 失败）
    logger.info("🔧 [解析代码] PIL 检测失败，回退到 magic bytes 检测")
    logger.info(f"   前4字节（十六进制）: {bytes(image_bytes[:4]).hex()}")
    logger.info(f"   前4字节（十进制）: {list(image_bytes[:4])}")
    
    # 检测 PNG: 89 50 4E 47 (PNG 文件头)
    if image_bytes[0] == 0x89 and image_bytes[1] == 0x50 and image_bytes[2] == 0x4E and image_bytes[3] == 0x47:
        logger.info("✅ _detect_image_format: 通过 magic bytes 检测到 PNG 格式 (89 50 4E 47)")
        logger.info("   匹配规则: image_bytes[0] == 0x89 && image_bytes[1] == 0x50 && image_bytes[2] == 0x4E && image_bytes[3] == 0x47")
        logger.info("   返回结果: image/png")
        return 'image/png'
    
    # 检测 JPEG: FF D8 FF (JPEG 文件头)
    if len(image_bytes) >= 3 and image_bytes[0] == 0xFF and image_bytes[1] == 0xD8 and image_bytes[2] == 0xFF:
        logger.info("✅ _detect_image_format: 通过 magic bytes 检测到 JPEG 格式 (FF D8 FF)")
        logger.info("   匹配规则: image_bytes[0] == 0xFF && image_bytes[1] == 0xD8 && image_bytes[2] == 0xFF")
        logger.info("   返回结果: image/jpeg")
        return 'image/jpeg'
    
    # 默认返回 PNG（因为 Gemini 系列更倾向于输出 PNG）
    logger.warning(f"⚠️ _detect_image_format: 无法识别格式，返回默认 PNG (前4字节: {bytes(image_bytes[:4]).hex()})")
    logger.info("=" * 80)
    return 'image/png'
try:
    from google import genai as genai_new
    from google.genai import types
    GEMINI_NEW_AVAILABLE = True
except ImportError:
    GEMINI_NEW_AVAILABLE = False
    logger.warning("⚠️ google.genai 模块不可用")


def _get_genai_client():
    """获取或创建 google.genai Client 实例（Vertex AI 模式）
    
    使用 Vertex AI 模式，通过服务账户凭据进行身份验证
    
    环境变量要求：
    - VERTEX_AI_PROJECT 或 GOOGLE_CLOUD_PROJECT: Vertex AI 项目 ID
    - VERTEX_AI_LOCATION 或 GOOGLE_CLOUD_LOCATION: Vertex AI 位置（默认: global）
    - GOOGLE_APPLICATION_CREDENTIALS: 服务账户凭据 JSON 文件路径（或自动查找 google-key.json）
    
    注意：此函数专门用于 gemini-2.5-flash-image 模型
    """
    if not GEMINI_NEW_AVAILABLE:
        return None
    
    # ⚠️ 重要：显式加载 .env 文件（使用容器根目录路径）
    # 参考 Google 建议：使用 os.path.join(os.getcwd(), '.env') 确保在容器根目录加载
    try:
        from dotenv import load_dotenv
        env_paths = [
            os.path.join(os.getcwd(), '.env'),  # 容器根目录
            os.path.join(os.path.dirname(__file__), '..', '.env'),  # backend/.env
            os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # 项目根目录
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, override=False)
                logger.info(f"✅ [_get_genai_client] 已加载环境变量文件: {env_path}")
                env_loaded = True
                break
        
        if not env_loaded:
            load_dotenv(override=False)
            logger.warning("⚠️ [_get_genai_client] 未找到 .env 文件，将使用系统环境变量")
    except ImportError:
        logger.warning("⚠️ python-dotenv 未安装，跳过环境变量加载")
    
    # 检查 Vertex AI 环境变量
    # ⚠️ Fallback 机制：如果 VERTEX_AI_PROJECT 缺失，尝试读取 GOOGLE_CLOUD_PROJECT 作为备份
    vertex_ai_project = os.getenv("VERTEX_AI_PROJECT")
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # Fallback 机制
    if not vertex_ai_project and google_cloud_project:
        logger.info(f"✅ 使用 Fallback 机制: GOOGLE_CLOUD_PROJECT ({google_cloud_project}) -> VERTEX_AI_PROJECT")
        os.environ['VERTEX_AI_PROJECT'] = google_cloud_project
        vertex_ai_project = google_cloud_project
    
    vertex_ai_location = os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    google_app_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # ⚠️ 自动获取 google-key.json 的绝对路径并赋值给 os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    # ⚠️ 绝对路径校验：如果文件丢失，通过日志显示当前容器里的文件列表
    if not google_app_credentials:
        current_file = Path(__file__).resolve()
        # 查找 google-key.json（多个可能位置）
        google_key_paths = [
            current_file.parent.parent / 'google-key.json',  # backend/google-key.json
            current_file.parent.parent.parent / 'google-key.json',  # 项目根目录
            Path(os.getcwd()) / 'google-key.json',  # 容器根目录
        ]
        
        google_key_found = False
        for google_key_path in google_key_paths:
            if google_key_path.exists():
                # 获取绝对路径
                google_app_credentials = str(google_key_path.resolve())
                # 赋值给环境变量
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_app_credentials
                logger.info(f"✅ 自动获取 google-key.json 绝对路径并设置: {google_app_credentials}")
                google_key_found = True
                break
        
        if not google_key_found:
            logger.warning("⚠️ 未找到 google-key.json 文件，将尝试使用 API Key 或其他认证方式")
            # 绝对路径校验：如果文件丢失，通过日志显示当前容器里的文件列表
            logger.warning("📋 当前容器文件列表（用于调试）:")
            try:
                current_dir = os.getcwd()
                files_in_dir = os.listdir(current_dir)
                logger.warning(f"   当前目录 ({current_dir}): {', '.join(files_in_dir[:30])}...")  # 显示前30个文件
            except Exception as e:
                logger.warning(f"   无法列出目录文件: {e}")
    
    # ⚠️ 在初始化前，打印 os.path.exists(credentials_path) 来确认文件是否存在
    if google_app_credentials:
        credentials_path = Path(google_app_credentials).resolve()
        credentials_exists = os.path.exists(credentials_path)
        logger.info(f"🔍 检查凭据文件（在初始化 Client 之前）:")
        logger.info(f"   凭据文件路径: {credentials_path}")
        logger.info(f"   os.path.exists(credentials_path): {credentials_exists}")
        
        if not credentials_exists:
            logger.error(f"❌ 凭据文件不存在: {credentials_path}")
            logger.error("💡 请确保 google-key.json 文件存在于 backend/ 目录下")
            return None
    
    # 调试信息：打印环境变量状态
    logger.info(f"🔍 环境变量检查:")
    logger.info(f"   VERTEX_AI_PROJECT: {os.getenv('VERTEX_AI_PROJECT', '未设置')}")
    logger.info(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', '未设置')}")
    logger.info(f"   VERTEX_AI_LOCATION: {os.getenv('VERTEX_AI_LOCATION', '未设置')}")
    logger.info(f"   GOOGLE_APPLICATION_CREDENTIALS: {google_app_credentials or '未设置'}")
    logger.info(f"📋 检测到的项目 ID: {vertex_ai_project or '未找到'}")
    
    # 必须使用 Vertex AI 模式
    if not vertex_ai_project:
        logger.error("❌ VERTEX_AI_PROJECT 未设置，无法使用 Vertex AI 模式")
        logger.error("💡 请设置 VERTEX_AI_PROJECT 或 GOOGLE_CLOUD_PROJECT 环境变量")
        logger.error("💡 检查 backend/.env 文件是否存在，以及是否包含正确的配置")
        return None
    
    if not google_app_credentials:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS 未设置，无法使用 Vertex AI 模式")
        logger.error("💡 请设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量或确保 google-key.json 存在于 backend/ 目录")
        return None
    
    logger.info(f"🔧 使用 Vertex AI 模式: project={vertex_ai_project}, location={vertex_ai_location}")
    
    try:
        # ⚠️ 设置超时时间：10分钟（600秒 = 600000毫秒），匹配前端和 Cloud Run 的超时设置
        http_options = types.HttpOptions(timeout=600_000)  # 600秒 = 600000毫秒（10分钟），匹配前端和 Cloud Run 的超时设置
        
        # ⚠️ 重要：在 Cloud Run 等云端环境，不需要设置代理
        # 代理配置已在文件开头根据环境自动处理
        
        # 确保 GOOGLE_APPLICATION_CREDENTIALS 已设置（在自动查找 google-key.json 时已设置）
        if google_app_credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials
        
        # 客户端会自动从 GOOGLE_APPLICATION_CREDENTIALS 环境变量读取凭据
        client = genai_new.Client(
            vertexai=True,
            project=vertex_ai_project,
            location=vertex_ai_location,
            http_options=http_options  # 设置超时时间（120秒）
        )
        logger.info("✅ Vertex AI Client 创建成功")
        return client
    except Exception as e:
        logger.error(f"❌ 创建 Vertex AI Client 失败: {e}")
        logger.error(f"📋 错误详情: {traceback.format_exc()}")
        return None


def generate_with_gemini_2_5_flash_image(prompt: str, reference_images: Optional[List[Image.Image]] = None, 
                                        aspect_ratio: Optional[str] = None) -> Optional[dict]:
    """
    使用 Gemini 2.5 Flash Image 模型进行图片生成（支持文生图和图生图）
    
    实现细节（根据 Google 文档）：
    - 模型: gemini-2.5-flash-image
    - API: client.models.generate_content
    - 配置: GenerateContentConfig(response_modalities=["IMAGE"], image_config=ImageConfig(aspect_ratio=...))
    - 响应: 从 response.candidates[0].content.parts 中提取 inline_data
    - 参考图片: 可以通过 contents 参数传递（最多3张）
    
    注意：
    - 该模型只支持 1K 分辨率（固定1024像素），不支持 4K
    - 如需 4K 分辨率，请使用 banana_pro 模式（imagen-3.0-generate-001 或 gemini-3-pro-image-preview）
    
    Args:
        prompt: 图片生成提示词
        reference_images: 参考图片列表（PIL Image 对象），可选。如果为 None 或空列表，则为文生图模式
        aspect_ratio: 长宽比（可选），例如 "16:9", "4:3", "1:1" 等
    
    Returns:
        包含图片数据的字典: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
        失败返回 None
    """
    has_reference = reference_images and len(reference_images) > 0
    mode_str = "图生图" if has_reference else "文生图"
    logger.info("=" * 80)
    logger.info(f"🖼️ [Gemini 2.5 Flash] 开始{mode_str}")
    logger.info(f"📝 提示词: {prompt[:150]}...")
    if has_reference:
        logger.info(f"📸 参考图片数量: {len(reference_images)}（最多3张）")
    if aspect_ratio:
        logger.info(f"📐 长宽比: {aspect_ratio}")
    logger.info(f"📏 分辨率: 1K（固定，不支持 4K）")
    logger.info(f"🔧 生成器: gemini_2_5_flash_image.py")
    logger.info("=" * 80)
    
    if not GEMINI_NEW_AVAILABLE:
        logger.error("❌ google.genai 模块不可用，无法使用新的 API")
        return {
            "error": True,
            "error_type": "ModuleNotAvailable",
            "error_message": "google.genai 模块不可用，无法使用新的 API",
            "error_code": "MODULE_NOT_AVAILABLE",
            "error_detail": "google.genai 模块未安装或导入失败，请检查依赖"
        }
    
    client = _get_genai_client()
    if not client:
        logger.error("❌ 无法创建 genai Client")
        return {
            "error": True,
            "error_type": "ClientCreationFailed",
            "error_message": "无法创建 genai Client",
            "error_code": "CLIENT_CREATION_FAILED",
            "error_detail": "无法创建 Google GenAI Client，请检查环境变量和凭证配置"
        }
    
    try:
        model_id = 'gemini-2.5-flash-image'
        logger.info(f"🎯 使用模型: {model_id}")
        
        # 构建 contents（包含提示词和参考图片）
        contents_parts = []
        
        # 添加参考图片（如果有）
        if has_reference:
            for idx, ref_img in enumerate(reference_images[:3]):  # 最多3张参考图片
                try:
                    # 将 PIL Image 转换为 bytes
                    img_bytes = io.BytesIO()
                    # 确保是 RGB 模式（兼容性最好）
                    if ref_img.mode != 'RGB':
                        ref_img = ref_img.convert('RGB')
                    ref_img.save(img_bytes, format='JPEG', quality=95)
                    img_bytes.seek(0)
                    img_data = img_bytes.getvalue()
                    
                    # 使用 types.Part.from_bytes（更简单的方式）
                    image_part = types.Part.from_bytes(
                        data=img_data,
                        mime_type="image/jpeg"
                    )
                    contents_parts.append(image_part)
                    logger.info(f"📸 添加参考图片 {idx+1}: {ref_img.size[0]}x{ref_img.size[1]} pixels")
                except Exception as e:
                    logger.error(f"❌ 处理参考图片 {idx+1} 失败: {str(e)}")
                    logger.error(f"📋 错误详情: {traceback.format_exc()}")
        
        # 添加文本提示词
        contents_parts.append(prompt)
        
        # 构建 GenerateContentConfig
        # ⚠️ 关键：使用 image_config 参数设置长宽比
        config_dict = {
            'response_modalities': ["IMAGE"],  # 只返回图片
            'candidate_count': 1
        }
        
        # 如果提供了长宽比，添加到 image_config
        if aspect_ratio:
            valid_aspect_ratios = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
            if aspect_ratio in valid_aspect_ratios:
                # 尝试创建 ImageConfig（如果 SDK 支持）
                try:
                    config_dict['image_config'] = types.ImageConfig(aspect_ratio=aspect_ratio)
                    logger.info(f"✅ 成功设置长宽比: {aspect_ratio}")
                except (AttributeError, TypeError) as e:
                    # 如果 SDK 不支持 ImageConfig，尝试直接传递参数
                    logger.warning(f"⚠️ types.ImageConfig 不可用，尝试直接传递参数: {e}")
                    try:
                        # 尝试直接在 config 中传递 image_config
                        config_dict['image_config'] = {'aspect_ratio': aspect_ratio}
                        logger.info(f"✅ 使用字典方式设置长宽比: {aspect_ratio}")
                    except Exception as e2:
                        logger.warning(f"⚠️ 设置长宽比失败，将使用模型默认值: {e2}")
            else:
                logger.warning(f"⚠️ 无效的长宽比: {aspect_ratio}，将使用模型默认值")
        
        # 创建 GenerateContentConfig
        config = types.GenerateContentConfig(**config_dict)
        
        logger.info("📤 发送请求到 Google API (Vertex AI)")
        logger.info(f"   模型: {model_id}")
        logger.info(f"   端点: Vertex AI")
        logger.info(f"   项目: {os.getenv('VERTEX_AI_PROJECT', 'N/A')}")
        logger.info(f"   位置: {os.getenv('VERTEX_AI_LOCATION', 'global')}")
        logger.info(f"   提示词: {prompt[:200]}...")
        logger.info(f"   参考图片数量: {len(contents_parts) - 1 if has_reference else 0}")
        if aspect_ratio:
            logger.info(f"   长宽比: {aspect_ratio}")
        
        # 调用 generate_content API
        response = client.models.generate_content(
            model=model_id,
            contents=contents_parts,
            config=config
        )
        
        # 提取生成的图片（从 candidates[0].content.parts 中提取）
        image_bytes = None
        mime_type_from_response = None
        
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                    for part in candidate.content.parts:
                        # 提取图片数据
                        if hasattr(part, 'inline_data') and part.inline_data:
                            raw_data = part.inline_data.data
                            # 获取响应中的 MIME 类型（可能为 None）
                            mime_type_from_response = getattr(part.inline_data, 'mime_type', None)
                            
                            # ⚠️ 重要：检查数据类型
                            logger.info(f"📋 原始数据类型: {type(raw_data).__name__}")
                            
                            # ⚠️ 关键修复：检测并处理 Base64 编码的字符串
                            # Google API 可能返回 Base64 编码的字符串，需要先解码为真正的二进制数据
                            
                            if isinstance(raw_data, str):
                                # 情况1：raw_data 是字符串（可能是 Base64）
                                logger.info(f"📋 检测到字符串格式，长度: {len(raw_data)}")
                                logger.info(f"📋 字符串前50字符: {raw_data[:50]}...")
                                
                                # 检测是否是 Base64 编码的图片（PNG: iVBO, JPEG: /9j/）
                                is_base64_png = raw_data.startswith('iVBOR') or raw_data.startswith('iVBO')
                                is_base64_jpeg = raw_data.startswith('/9j/')
                                
                                if is_base64_png or is_base64_jpeg:
                                    logger.info(f"📋 检测到 Base64 编码的图片字符串: {'PNG' if is_base64_png else 'JPEG'}")
                                    logger.info(f"📋 Base64 字符串前缀: {raw_data[:20]}")
                                    
                                    # 先解码 Base64 字符串为真正的二进制数据
                                    try:
                                        image_bytes = base64.b64decode(raw_data)
                                        logger.info(f"✅ Base64 解码成功，解码后大小: {len(image_bytes)} bytes")
                                        logger.info(f"   解码后前4字节（十六进制）: {bytes(image_bytes[:4]).hex()}")
                                    except Exception as e:
                                        logger.error(f"❌ Base64 解码失败: {str(e)}")
                                        return {
                                            "error": True,
                                            "error_type": "Base64DecodeFailed",
                                            "error_message": f"Base64 解码失败: {str(e)}",
                                            "error_code": "BASE64_DECODE_FAILED",
                                            "error_detail": f"无法解码 Base64 字符串: {str(e)}"
                                        }
                                else:
                                    # 如果不是 Base64 图片字符串，尝试直接解码（可能是其他 Base64 数据）
                                    logger.warning("⚠️ 字符串不是标准的 Base64 图片格式，尝试解码...")
                                    try:
                                        image_bytes = base64.b64decode(raw_data)
                                        logger.info(f"✅ Base64 解码成功，解码后大小: {len(image_bytes)} bytes")
                                    except Exception as e:
                                        logger.error(f"❌ Base64 解码失败: {str(e)}")
                                        return {
                                            "error": True,
                                            "error_type": "Base64DecodeFailed",
                                            "error_message": f"Base64 解码失败: {str(e)}",
                                            "error_code": "BASE64_DECODE_FAILED",
                                            "error_detail": f"无法解码 Base64 字符串: {str(e)}"
                                        }
                                        
                            elif isinstance(raw_data, bytes):
                                # 情况2：raw_data 是 bytes，但可能是 Base64 编码的字符串（转换为 bytes）
                                logger.info(f"📋 检测到 bytes 格式，大小: {len(raw_data)} bytes")
                                logger.info(f"📋 bytes 前100字节（十六进制）: {bytes(raw_data[:100]).hex()}")
                                
                                # ⚠️ 关键：检查 bytes 数据是否实际上是 Base64 编码的字符串
                                # 方法1：尝试将 bytes 解码为字符串，检查是否是 Base64
                                try:
                                    # 尝试将 bytes 解码为字符串
                                    raw_str = raw_data.decode('utf-8', errors='ignore')
                                    logger.info(f"📋 bytes 解码为字符串成功，前50字符: {raw_str[:50]}")
                                    
                                    # 检查是否是 Base64 编码的图片字符串
                                    # PNG Base64 通常以 iVBOR 或 iVBO 开头
                                    # JPEG Base64 通常以 /9j/ 开头
                                    is_base64_png = raw_str.startswith('iVBOR') or raw_str.startswith('iVBO')
                                    is_base64_jpeg = raw_str.startswith('/9j/')
                                    
                                    if is_base64_png or is_base64_jpeg:
                                        logger.warning("=" * 80)
                                        logger.warning("⚠️ 检测到 bytes 数据实际上是 Base64 编码的字符串！")
                                        logger.warning(f"   Base64 字符串前缀: {raw_str[:20]}")
                                        logger.warning(f"   检测到的格式: {'PNG' if is_base64_png else 'JPEG'}")
                                        logger.warning("   需要先解码 Base64 字符串为真正的二进制数据")
                                        logger.warning("=" * 80)
                                        
                                        # ⚠️ 关键修复：先解码 Base64 字符串为真正的二进制数据
                                        image_bytes = base64.b64decode(raw_str)
                                        logger.info(f"✅ Base64 解码成功，解码后大小: {len(image_bytes)} bytes")
                                        logger.info(f"   解码后前4字节（十六进制）: {bytes(image_bytes[:4]).hex()}")
                                        logger.info(f"   解码后前4字节（十进制）: {list(image_bytes[:4])}")
                                        
                                        # 验证解码后的数据是否是真正的图片文件头
                                        if len(image_bytes) >= 4:
                                            first_4 = bytes(image_bytes[:4])
                                            is_png_header = first_4[0] == 0x89 and first_4[1] == 0x50 and first_4[2] == 0x4E and first_4[3] == 0x47
                                            is_jpeg_header = len(image_bytes) >= 3 and first_4[0] == 0xFF and first_4[1] == 0xD8 and first_4[2] == 0xFF
                                            
                                            if is_png_header:
                                                logger.info("   ✅ 验证通过：解码后是 PNG 文件头 (89 50 4E 47)")
                                            elif is_jpeg_header:
                                                logger.info("   ✅ 验证通过：解码后是 JPEG 文件头 (FF D8 FF)")
                                            else:
                                                logger.warning(f"   ⚠️ 警告：解码后未检测到标准图片文件头，前4字节: {first_4.hex()}")
                                    else:
                                        # 不是 Base64 字符串，检查是否是真正的二进制数据
                                        # 检查前4字节是否是图片文件头
                                        if len(raw_data) >= 4:
                                            first_4 = bytes(raw_data[:4])
                                            is_png_header = first_4[0] == 0x89 and first_4[1] == 0x50 and first_4[2] == 0x4E and first_4[3] == 0x47
                                            is_jpeg_header = len(raw_data) >= 3 and first_4[0] == 0xFF and first_4[1] == 0xD8 and first_4[2] == 0xFF
                                            
                                            if is_png_header or is_jpeg_header:
                                                image_bytes = raw_data
                                                logger.info(f"✅ bytes 数据是真正的二进制数据（{'PNG' if is_png_header else 'JPEG'} 文件头），直接使用")
                                            else:
                                                # 既不是 Base64 字符串，也不是图片文件头，尝试作为 Base64 解码
                                                logger.warning("⚠️ bytes 数据既不是 Base64 字符串，也不是图片文件头，尝试作为 Base64 解码...")
                                                try:
                                                    image_bytes = base64.b64decode(raw_str)
                                                    logger.info(f"✅ Base64 解码成功（备用方案），解码后大小: {len(image_bytes)} bytes")
                                                except:
                                                    # 解码失败，直接使用
                                                    image_bytes = raw_data
                                                    logger.warning("⚠️ Base64 解码失败，直接使用原始 bytes 数据")
                                        else:
                                            image_bytes = raw_data
                                            logger.info("✅ bytes 数据长度不足，直接使用")
                                except Exception as e:
                                    # 解码失败，检查是否是真正的二进制数据
                                    logger.warning(f"⚠️ 无法将 bytes 解码为字符串: {str(e)}")
                                    
                                    # 检查前4字节是否是图片文件头
                                    if len(raw_data) >= 4:
                                        first_4 = bytes(raw_data[:4])
                                        is_png_header = first_4[0] == 0x89 and first_4[1] == 0x50 and first_4[2] == 0x4E and first_4[3] == 0x47
                                        is_jpeg_header = len(raw_data) >= 3 and first_4[0] == 0xFF and first_4[1] == 0xD8 and first_4[2] == 0xFF
                                        
                                        if is_png_header or is_jpeg_header:
                                            image_bytes = raw_data
                                            logger.info(f"✅ bytes 数据是真正的二进制数据（{'PNG' if is_png_header else 'JPEG'} 文件头），直接使用")
                                        else:
                                            image_bytes = raw_data
                                            logger.warning("⚠️ 假设是真正的二进制数据，直接使用")
                                    else:
                                        image_bytes = raw_data
                                        logger.warning("⚠️ bytes 数据长度不足，直接使用")
                            else:
                                logger.error(f"❌ 不支持的数据类型: {type(raw_data)}")
                                return {
                                    "error": True,
                                    "error_type": "UnsupportedDataType",
                                    "error_message": f"不支持的数据类型: {type(raw_data)}",
                                    "error_code": "UNSUPPORTED_DATA_TYPE",
                                    "error_detail": f"响应中的图片数据类型不支持: {type(raw_data).__name__}，期望 str 或 bytes"
                                }
                            
                            logger.info(f"📋 响应中的 MIME 类型: {mime_type_from_response or '未提供'}")
                            break
                        # 如果有文本输出，也记录一下
                        elif hasattr(part, 'text') and part.text:
                            logger.info(f"📝 模型返回文本: {part.text[:100]}...")
        
        if not image_bytes:
            logger.error("❌ 响应中未找到图片数据")
            return {
                "error": True,
                "error_type": "ImageExtractionFailed",
                "error_message": "响应中未找到图片数据",
                "error_code": "IMAGE_EXTRACTION_FAILED",
                "error_detail": "从 API 响应中无法提取图片数据，可能原因：响应格式异常、安全策略拦截或图片生成失败"
            }
        
        # ⚠️ 验证 image_bytes 是真正的二进制数据，不是 Base64 字符串
        if not isinstance(image_bytes, bytes):
            logger.error(f"❌ image_bytes 类型错误: {type(image_bytes)}，期望 bytes")
            return {
                "error": True,
                "error_type": "InvalidImageDataType",
                "error_message": f"image_bytes 类型错误: {type(image_bytes)}，期望 bytes",
                "error_code": "INVALID_IMAGE_DATA_TYPE",
                "error_detail": f"提取的图片数据类型不正确: {type(image_bytes).__name__}，期望 bytes"
            }
        
        # ⚠️ 输出收到图片的前100字节到终端（此时应该是真正的二进制数据）
        logger.info("=" * 80)
        logger.info("📦 [图片数据] 收到图片二进制数据（已确保是真正的二进制，不是 Base64 字符串）")
        logger.info(f"   数据总大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        logger.info(f"   前100字节（十六进制）: {bytes(image_bytes[:100]).hex()}")
        logger.info(f"   前100字节（十进制）: {list(image_bytes[:100])}")
        logger.info(f"   前100字节（ASCII可打印字符）: {''.join([chr(b) if 32 <= b <= 126 else '.' for b in image_bytes[:100]])}")
        
        # ⚠️ 验证前4字节是否是真正的图片文件头（不是 Base64 字符串）
        if len(image_bytes) >= 4:
            first_4_bytes = bytes(image_bytes[:4])
            first_4_hex = first_4_bytes.hex()
            logger.info(f"   前4字节（十六进制）: {first_4_hex}")
            logger.info(f"   前4字节（十进制）: {list(first_4_bytes)}")
            
            # PNG 文件头: 89 50 4E 47
            # JPEG 文件头: FF D8 FF
            is_png_header = first_4_bytes[0] == 0x89 and first_4_bytes[1] == 0x50 and first_4_bytes[2] == 0x4E and first_4_bytes[3] == 0x47
            is_jpeg_header = len(image_bytes) >= 3 and first_4_bytes[0] == 0xFF and first_4_bytes[1] == 0xD8 and first_4_bytes[2] == 0xFF
            
            if is_png_header:
                logger.info("   ✅ 检测到 PNG 文件头 (89 50 4E 47)，确认是真正的二进制数据")
            elif is_jpeg_header:
                logger.info("   ✅ 检测到 JPEG 文件头 (FF D8 FF)，确认是真正的二进制数据")
            else:
                logger.warning(f"   ⚠️ 未检测到标准的图片文件头，前4字节: {first_4_hex}")
        logger.info("=" * 80)
        
        # ⚠️ 关键修复：使用 PIL 自动检测图片格式，不要依赖响应中的 MIME 类型
        # 因为 Gemini API 可能返回错误的 MIME 类型（例如返回 image/jpeg 但实际是 PNG）
        # ⚠️ 注意：此时 image_bytes 应该是真正的二进制数据，不是 Base64 字符串
        logger.info(f"🔍 开始检测图片格式，数据大小: {len(image_bytes)} bytes")
        logger.info(f"🔍 数据前4字节（十六进制）: {bytes(image_bytes[:4]).hex() if len(image_bytes) >= 4 else '不足4字节'}")
        
        # ⚠️ 输出解析图片的代码逻辑
        logger.info("=" * 80)
        logger.info("🔧 [解析代码] 图片格式检测逻辑:")
        logger.info("   1. 优先使用 PIL.Image.open() 检测格式（最可靠）")
        logger.info("   2. 如果 PIL 失败，使用 magic bytes 检测:")
        logger.info("      - PNG: 89 50 4E 47 (0x89 0x50 0x4E 0x47)")
        logger.info("      - JPEG: FF D8 FF (0xFF 0xD8 0xFF)")
        logger.info("   3. 默认回退到 PNG（Gemini 系列更倾向于输出 PNG）")
        logger.info("=" * 80)
        
        # 使用 PIL 检测实际格式（最可靠的方法）
        detected_mime_type = _detect_image_format(image_bytes)
        logger.info(f"🔍 PIL 检测到的格式: {detected_mime_type}")
        
        # ⚠️ 始终使用检测到的格式，忽略响应中的 MIME 类型（如果存在不一致）
        if mime_type_from_response:
            logger.info(f"📋 响应中的 MIME 类型: {mime_type_from_response}")
            if mime_type_from_response != detected_mime_type:
                logger.warning(f"⚠️ MIME 类型冲突: 响应={mime_type_from_response}, PIL检测={detected_mime_type}")
                logger.warning(f"⚠️ 使用 PIL 检测到的格式（更可靠）: {detected_mime_type}")
                mime_type = detected_mime_type
            else:
                logger.info(f"✅ MIME 类型一致: {detected_mime_type}")
                mime_type = detected_mime_type
        else:
            # 响应中没有 MIME 类型，使用检测到的格式
            logger.info(f"📋 响应中未提供 MIME 类型，使用 PIL 检测到的格式: {detected_mime_type}")
            mime_type = detected_mime_type
        
        # 验证 image_bytes 类型
        if not isinstance(image_bytes, bytes):
            logger.error(f"❌ image_bytes 类型错误: {type(image_bytes)}，期望 bytes")
            return {
                "error": True,
                "error_type": "InvalidImageDataType",
                "error_message": f"image_bytes 类型错误: {type(image_bytes)}，期望 bytes",
                "error_code": "INVALID_IMAGE_DATA_TYPE",
                "error_detail": f"提取的图片数据类型不正确: {type(image_bytes).__name__}，期望 bytes"
            }
        
        logger.info(f"✅ Gemini 2.5 Flash Image {mode_str}成功")
        logger.info(f"   图片大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        logger.info(f"   图片格式: {mime_type}")
        logger.info(f"   数据前4字节（十六进制）: {bytes(image_bytes[:4]).hex()}")
        
        # ⚠️ 修改：只返回 Base64 字符串和格式信息，不构建 Data URL
        # 让前端自己根据格式构建 Data URL
        # ⚠️ 重要：此时 image_bytes 应该是真正的二进制数据，不是 Base64 字符串
        try:
            logger.info("=" * 80)
            logger.info("🔧 [解析代码] 开始 Base64 编码（仅编码一次）")
            logger.info(f"   原始二进制数据大小: {len(image_bytes)} bytes")
            logger.info(f"   编码前100字节（十六进制）: {bytes(image_bytes[:100]).hex()}")
            logger.info(f"   编码前4字节（十六进制）: {bytes(image_bytes[:4]).hex()}")
            
            # ⚠️ 验证：确保 image_bytes 是真正的二进制数据，不是 Base64 字符串
            # PNG 文件头应该是 89 50 4E 47，JPEG 文件头应该是 FF D8 FF
            if len(image_bytes) >= 4:
                first_4 = bytes(image_bytes[:4])
                is_png = first_4[0] == 0x89 and first_4[1] == 0x50 and first_4[2] == 0x4E and first_4[3] == 0x47
                is_jpeg = len(image_bytes) >= 3 and first_4[0] == 0xFF and first_4[1] == 0xD8 and first_4[2] == 0xFF
                
                if is_png or is_jpeg:
                    logger.info(f"   ✅ 验证通过：确认是真正的二进制数据（{'PNG' if is_png else 'JPEG'} 文件头）")
                else:
                    logger.warning(f"   ⚠️ 警告：未检测到标准的图片文件头，前4字节: {first_4.hex()}")
            
            # ⚠️ 关键：只进行一次 Base64 编码
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            logger.info(f"✅ Base64 编码成功，编码后长度: {len(image_b64)} 字符")
            logger.info(f"   Base64 前100字符: {image_b64[:100]}")
            logger.info(f"   Base64 编码代码: base64.b64encode(image_bytes).decode('utf-8')")
            logger.info(f"   ⚠️ 重要：这是唯一一次 Base64 编码，确保不会二次编码")
            logger.info("=" * 80)
            
            # 提取格式（从 mime_type 中提取，例如 'image/png' -> 'png'）
            image_format = mime_type.replace('image/', '') if mime_type.startswith('image/') else 'png'
            
            # 返回包含 Base64 字符串和格式的字典
            # 格式：{"image_data": "base64_string", "image_format": "png"}
            logger.info(f"✅ 返回原始图片数据（Base64 + 格式信息），格式: {image_format}")
            logger.info(f"   返回结构: {{'image_data': '...', 'image_format': '{image_format}'}}")
            return {
                "image_data": image_b64,
                "image_format": image_format
            }
        except Exception as e:
            logger.error(f"❌ Base64 编码失败: {str(e)}")
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            return {
                "error": True,
                "error_type": "Base64EncodeFailed",
                "error_message": f"Base64 编码失败: {str(e)}",
                "error_code": "BASE64_ENCODE_FAILED",
                "error_detail": f"无法将图片二进制数据编码为 Base64: {str(e)}"
            }
        
    except Exception as e:
        error_name = type(e).__name__
        error_message = str(e)
        logger.error(f"Gemini 2.5 Flash Image {mode_str}失败: {error_name} - {error_message}")
        
        # 创建详细的错误信息字典
        error_info = {
            "error": True,
            "error_type": error_name,
            "error_message": error_message,
            "error_code": None,
            "error_detail": None
        }
        
        # 识别特定的错误类型并设置错误码
        if "Timeout" in error_name or "timeout" in error_message.lower() or "超时" in error_message:
            error_info["error_code"] = "TIMEOUT_ERROR"
            error_info["error_detail"] = f"Google API 请求超时: {error_message}"
        elif "ProxyError" in error_name or "proxy" in error_message.lower():
            error_info["error_code"] = "PROXY_ERROR"
            error_info["error_detail"] = f"代理连接失败: {error_message}"
        elif "SAFETY" in error_message.upper() or "安全" in error_message:
            error_info["error_code"] = "SAFETY_BLOCKED"
            error_info["error_detail"] = f"安全策略拦截: {error_message}"
        else:
            error_info["error_code"] = "GENERATION_ERROR"
            error_info["error_detail"] = f"图片生成失败: {error_message}"
        
        # 返回错误信息字典而不是 None，让调用方能够获取详细错误信息
        return error_info
