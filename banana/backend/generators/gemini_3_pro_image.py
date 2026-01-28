"""
Gemini 3 Pro Image 图片生成器 (重构版)

使用 Gemini 3 Pro Image (gemini-3-pro-image-preview) 模型进行图片生成
支持：4K 分辨率、最多 14 张参考图、文生图/图生图
"""
import os
import base64
import logging
import traceback
import io
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image

# ==================== 配置模块 ====================
class EnvConfig:
    """环境变量和配置管理（单一职责）"""
    
    @staticmethod
    def load_env():
        """加载环境变量（.env 文件）"""
        try:
            from dotenv import load_dotenv, find_dotenv
            env_file = find_dotenv() or EnvConfig._find_backend_env()
            if env_file:
                load_dotenv(dotenv_path=env_file, override=False)
                return env_file
            load_dotenv(override=False)
        except ImportError:
            pass
        return None
    
    @staticmethod
    def _find_backend_env() -> Optional[Path]:
        """查找 backend/.env 文件"""
        current = Path(__file__).resolve()
        for env_path in [current.parent.parent / '.env', current.parent.parent.parent / '.env']:
            if env_path.exists():
                return env_path
        return None
    
    @staticmethod
    def should_use_proxy() -> bool:
        """判断是否使用代理"""
        # 优先级：DISABLE_PROXY > Cloud环境 > SOCKS5 > HTTP
        if os.getenv('DISABLE_PROXY', '').lower() == 'true':
            ProxyConfig.clear_proxy_env()
            return False
        
        if os.getenv('K_SERVICE') or os.getenv('GAE_ENV'):
            return False
        
        # SOCKS5 优先
        if os.getenv('USE_SOCKS5_PROXY', '').lower() == 'true':
            socks5_proxy = os.getenv('SOCKS5_PROXY', '').strip()
            if socks5_proxy:
                return ProxyConfig.setup_socks5(socks5_proxy)
        
        # HTTP 代理
        return ProxyConfig.setup_http()


class ProxyConfig:
    """代理配置管理（单一职责）"""
    
    @staticmethod
    def clear_proxy_env():
        """清除代理环境变量"""
        keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        for key in keys:
            os.environ.pop(key, None)
    
    @staticmethod
    def setup_socks5(proxy_url: str) -> bool:
        """配置 SOCKS5 代理"""
        os.environ['ALL_PROXY'] = proxy_url
        os.environ['all_proxy'] = proxy_url
        try:
            import socks
            return True
        except ImportError:
            logging.getLogger("果捷后端").warning("⚠️ pysocks 未安装，SOCKS5 可能不工作")
            return False
    
    @staticmethod
    def setup_http() -> bool:
        """配置 HTTP 代理"""
        proxy_url = (os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY') or 
                     f"http://{os.getenv('PROXY_HOST', '127.0.0.1')}:{os.getenv('PROXY_PORT', '29290')}")
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ[key] = proxy_url
        return True


# ==================== 初始化 ====================
logger = logging.getLogger("果捷后端")
env_file = EnvConfig.load_env()
if env_file:
    logger.info(f"✅ [gemini_3_pro_image] 已加载环境: {env_file}")
EnvConfig.should_use_proxy()

# 导入 google.genai
try:
    from google import genai as genai_new
    from google.genai import types
    from google.genai.types import Modality, FinishReason
    GEMINI_NEW_AVAILABLE = True
except ImportError:
    GEMINI_NEW_AVAILABLE = False
    logger.warning("⚠️ google.genai 模块不可用")


# ==================== 客户端管理 ====================
class GeminiClient:
    """Gemini Client 管理（单一职责）"""
    
    @staticmethod
    def create():
        """创建 Gemini Client"""
        if not GEMINI_NEW_AVAILABLE:
            return None
        
        project_id = os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("VERTEX_AI_LOCATION", "global")
        credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
        
        if not project_id:
            logger.error("❌ VERTEX_AI_PROJECT 未设置")
            return None
        
        if not (api_key or credentials):
            logger.error("❌ 未设置认证方式")
            return None
        
        try:
            # 配置 httpx 客户端
            http_client = GeminiClient._create_http_client()
            http_options = types.HttpOptions(
                timeout=int(os.getenv('HTTP_TIMEOUT', '1200000')),
                httpx_client=http_client
            )
            
            client = genai_new.Client(
                vertexai=True,
                project=project_id,
                location=location,
                http_options=http_options
            )
            logger.info("✅ Vertex AI Client 创建成功")
            return client
        except Exception as e:
            logger.error(f"❌ 创建 Client 失败: {e}")
            return None
    
    @staticmethod
    def _create_http_client():
        """创建自定义 httpx 客户端"""
        import httpx
        from httpx import Limits
        
        socket_timeout = int(os.getenv('SOCKET_TIMEOUT', '1200'))
        proxy_url = os.getenv('ALL_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        
        limits = Limits(
            max_connections=100,
            max_keepalive_connections=50,
            keepalive_expiry=3600.0
        )
        
        timeout = httpx.Timeout(
            timeout=socket_timeout,
            read=socket_timeout,
            write=socket_timeout,
            connect=120,
            pool=None
        )
        
        if proxy_url:
            if proxy_url.startswith('socks'):
                try:
                    return httpx.Client(limits=limits, timeout=timeout, proxy=proxy_url)
                except:
                    return httpx.Client(limits=limits, timeout=timeout)
            return httpx.Client(limits=limits, timeout=timeout, proxy=proxy_url)
        
        return httpx.Client(limits=limits, timeout=timeout)


# ==================== 图片处理工具 ====================
class ImageProcessor:
    """图片处理工具（单一职责）"""
    
    @staticmethod
    def extract_from_response(response, function_name: str = "生图") -> Optional[Tuple[bytes, str]]:
        """从响应中提取图片数据"""
        try:
            if not hasattr(response, 'candidates') or not response.candidates:
                return None
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
                return None
            
            # 查找图片 part
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    mime_type = part.inline_data.mime_type
                    data = part.inline_data.data
                    
                    if isinstance(data, bytes):
                        return data, mime_type
                    elif isinstance(data, str):
                        # Base64 解码
                        try:
                            return base64.b64decode(data), mime_type
                        except:
                            pass
            
            return None
        except Exception as e:
            logger.error(f"❌ [{function_name}] 提取图片失败: {e}")
            return None
    
    @staticmethod
    def encode_pil_to_bytes(image: Image.Image, format: str = 'JPEG', quality: int = 85) -> bytes:
        """将 PIL Image 编码为 bytes"""
        buffer = io.BytesIO()
        if image.mode != 'RGB' and format.upper() == 'JPEG':
            image = image.convert('RGB')
        image.save(buffer, format=format, quality=quality)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def validate_and_encode(image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """验证图片并返回格式"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True, img.format.lower() if img.format else 'png'
        except:
            return False, None


# ==================== 提示词优化 ====================
class PromptOptimizer:
    """提示词优化工具（单一职责）"""
    
    @staticmethod
    def optimize_for_image(prompt: str, num_reference_images: int = 0, aspect_ratio: str = None) -> str:
        """优化图片生成提示词"""
        parts = []
        
        # 添加参考图说明
        if num_reference_images > 0:
            parts.append(
                f"I have provided {num_reference_images} reference image{'s' if num_reference_images > 1 else ''}. "
                f"Please carefully consider and combine elements from ALL {num_reference_images} images equally "
                "when generating the new image."
            )
        
        # 添加原始提示词
        parts.append(f"Generate an image that {prompt}")
        
        # 添加质量要求
        parts.extend([
            "Please keep the aspect ratio consistent with the reference images if provided.",
            "Ensure high quality, detailed, and visually appealing output.",
            "Focus on accuracy and coherence in the generated image."
        ])
        
        return " ".join(parts)


# ==================== 主要生成函数 ====================
def generate_with_gemini_image3(
    prompt: str,
    reference_images: Optional[List[Image.Image]] = None,
    aspect_ratio: Optional[str] = None,
    image_size: str = "1K"
) -> Optional[dict]:
    """
    使用 Gemini 3 Pro Image 生成图片
    
    Args:
        prompt: 提示词
        reference_images: 参考图片列表（最多 14 张）
        aspect_ratio: 长宽比（如 "3:2", "16:9"）
        image_size: 分辨率（"1K" 或 "4K"）
    
    Returns:
        {"image_data": "base64_string", "image_format": "png/jpeg"} 或错误字典
    """
    if not GEMINI_NEW_AVAILABLE:
        return {"error": True, "error_type": "ModuleNotAvailable", 
                "error_message": "google.genai 模块不可用"}
    
    client = GeminiClient.create()
    if not client:
        return {"error": True, "error_type": "ClientCreationFailed",
                "error_message": "无法创建 Client"}
    
    try:
        # 构建内容
        has_reference = reference_images and len(reference_images) > 0
        mode_str = "图生图" if has_reference else "文生图"
        
        logger.info(f"🖼️ [Gemini 3 Pro {mode_str}] 开始生成")
        logger.info(f"   提示词: {prompt[:50]}...")
        logger.info(f"   参考图: {len(reference_images) if has_reference else 0} 张")
        logger.info(f"   分辨率: {image_size}, 长宽比: {aspect_ratio or '默认'}")
        
        # 优化提示词
        optimized_prompt = PromptOptimizer.optimize_for_image(
            prompt,
            num_reference_images=len(reference_images) if has_reference else 0,
            aspect_ratio=aspect_ratio
        )
        
        # 构建 parts
        parts = [types.Part.from_text(text=optimized_prompt)]
        
        # 添加参考图
        if has_reference:
            for idx, ref_img in enumerate(reference_images[:14]):
                img_bytes = ImageProcessor.encode_pil_to_bytes(ref_img)
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
                parts.append(types.Part.from_text(text=f"[Reference Image {idx+1} of {len(reference_images)}]"))
        
        # 配置
        config_params = {
            "response_modalities": [Modality.TEXT, Modality.IMAGE],
            "temperature": 0.4,
            "top_p": 0.95,
            "max_output_tokens": 32768
        }
        
        if aspect_ratio:
            config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)
        
        # 注意：Gemini 3 Pro 的分辨率由模型自动决定，不能通过API指定
        # image_size 参数仅用于日志记录，不传递给API
        
        config = types.GenerateContentConfig(**config_params)
        
        # 调用 API
        logger.info(f"📤 发送请求到 Google API...")
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=[types.Content(parts=parts, role='user')],
            config=config
        )
        
        # 提取图片
        result = ImageProcessor.extract_from_response(response, mode_str)
        if not result:
            return {"error": True, "error_type": "NoImageInResponse",
                    "error_message": "响应中没有图片数据"}
        
        image_bytes, mime_type = result
        
        # 验证并编码
        is_valid, format_name = ImageProcessor.validate_and_encode(image_bytes)
        if not is_valid:
            return {"error": True, "error_type": "InvalidImage",
                    "error_message": "生成的图片数据无效"}
        
        logger.info(f"✅ [Gemini 3 Pro {mode_str}] 生成成功")
        logger.info(f"   大小: {len(image_bytes)} bytes ({len(image_bytes)/1024:.1f} KB)")
        logger.info(f"   格式: {format_name}")
        
        # 获取图片尺寸
        try:
            from PIL import Image as PILImage
            import io
            img = PILImage.open(io.BytesIO(image_bytes))
            width, height = img.size
        except:
            width, height = 0, 0
        
        # 返回统一格式（与 handler 期望一致）
        return {
            "image_bytes": image_bytes,
            "mime_type": f"image/{format_name}",
            "format": format_name or 'png',
            "width": width,
            "height": height
        }
        
    except Exception as e:
        logger.error(f"❌ [Gemini 3 Pro] 生成失败: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": True,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_detail": traceback.format_exc()
        }


# 兼容旧接口
def generate_image(prompt: str, reference_images: Optional[List[Image.Image]] = None,
                  aspect_ratio: Optional[str] = None, image_size: str = "1K") -> Optional[dict]:
    """兼容旧函数名"""
    return generate_with_gemini_image3(prompt, reference_images, aspect_ratio, image_size)
