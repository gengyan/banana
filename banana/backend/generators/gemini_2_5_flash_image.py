"""
Gemini 2.5 Flash Image 图片生成器 (重构版)

使用 Gemini 2.5 Flash Image (gemini-2.5-flash-image) 模型进行图片生成
支持：1K 分辨率、最多 3 张参考图、文生图/图生图
"""
import os
import base64
import logging
import traceback
import io
import re
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image

# 结构化日志工具
import sys
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
from log_utils import log_info, log_debug, log_warning, log_error, log_success

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
        # 优先级：DISABLE_PROXY > Cloud环境 > HTTP
        if os.getenv('DISABLE_PROXY', '').lower() == 'true':
            ProxyConfig.clear_proxy_env()
            return False
        
        if os.getenv('K_SERVICE') or os.getenv('GAE_ENV'):
            return False
        
        # HTTP 代理
        return ProxyConfig.setup_http()


class ProxyConfig:
    """代理配置管理（单一职责）"""
    
    @staticmethod
    def clear_proxy_env():
        """清除代理环境变量"""
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(key, None)
    
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


def _extract_core_error_message(error_msg: str) -> Optional[str]:
    if not error_msg:
        return None

    match = re.search(r"\b(\d{3})\s+([A-Z_]+)\b", error_msg)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    code_match = re.search(r"['\"]code['\"]\s*:\s*(\d{3})", error_msg)
    status_match = re.search(r"['\"]status['\"]\s*:\s*['\"]([A-Z_]+)['\"]", error_msg)
    if code_match and status_match:
        return f"{code_match.group(1)} {status_match.group(1)}"

    if "RESOURCE_EXHAUSTED" in error_msg:
        return "RESOURCE_EXHAUSTED"

    return None
env_file = EnvConfig.load_env()
if env_file:
    logger.info(f"✅ [gemini_2_5_flash_image] 已加载环境: {env_file}")
EnvConfig.should_use_proxy()

# 导入 google.genai
try:
    from google import genai as genai_new
    from google.genai import types
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
        
        # 获取配置
        project_id = (os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
        location = (os.getenv("VERTEX_AI_LOCATION", "global") or "").strip()
        credentials = GeminiClient._resolve_credentials()
        
        if not project_id:
            log_error("配置检查", "VERTEX_AI_PROJECT未设置")
            return None
        
        if not credentials:
            log_error("配置检查", "GOOGLE_APPLICATION_CREDENTIALS未设置")
            return None
        
        # 设置环境变量
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials
        
        try:
            # 设置超时（10分钟）
            http_options = types.HttpOptions(timeout=600_000)
            
            client = genai_new.Client(
                vertexai=True,
                project=project_id,
                location=location,
                http_options=http_options
            )
            log_success("Client创建", f"Vertex AI Client初始化成功", {"项目": project_id})
            return client
        except Exception as e:
            log_error("Client创建", f"创建失败: {e}")
            return None
    
    @staticmethod
    def _resolve_credentials() -> Optional[str]:
        """解析凭据路径（支持相对路径和自动查找）"""
        credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # 如果是相对路径，转为绝对路径
        if credentials and not os.path.isabs(credentials):
            backend_root = Path(__file__).parent.parent
            candidate = (backend_root / credentials).resolve()
            if candidate.exists():
                return str(candidate)
        
        # 如果已设置且存在，直接返回
        if credentials and Path(credentials).exists():
            return credentials
        
        # 自动查找 google-key.json
        current = Path(__file__).resolve()
        for key_path in [
            current.parent.parent / 'google-key.json',  # backend/
            current.parent.parent.parent / 'google-key.json',  # 项目根
            Path(os.getcwd()) / 'google-key.json'  # 容器根
        ]:
            if key_path.exists():
                log_info("凭证查找", f"找到 google-key.json: {key_path}")
                return str(key_path.resolve())
        
        log_warning("凭证查找", "未找到 google-key.json")
        return None


# ==================== 图片处理工具 ====================
class ImageProcessor:
    """图片处理工具（单一职责）"""
    
    @staticmethod
    def detect_format(image_bytes: bytes) -> str:
        """检测图片格式（返回 MIME 类型）"""
        if not image_bytes or len(image_bytes) < 4:
            return 'image/png'
        
        # 优先使用 PIL
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
            if img.format:
                fmt = img.format.lower()
                log_info("格式检测", f"PIL识别: {fmt} ({img.size[0]}x{img.size[1]})", emoji="✅")
                return 'image/jpeg' if fmt in ['jpeg', 'jpg'] else 'image/png'
        except Exception as e:
            log_warning("格式检测", f"PIL失败: {e}")
        
        # 回退到 magic bytes
        if image_bytes[:4] == b'\x89PNG':
            return 'image/png'
        if image_bytes[:3] == b'\xFF\xD8\xFF':
            return 'image/jpeg'
        
        return 'image/png'
    
    @staticmethod
    def extract_from_response(response) -> Optional[Tuple[bytes, str]]:
        """从响应中提取图片数据"""
        try:
            if not hasattr(response, 'candidates') or not response.candidates:
                log_warning("图片提取", "response.candidates 为空，可能被安全过滤")
                return None
            
            candidate = response.candidates[0]

            # 兼容不同 SDK 结构，获取 parts
            parts = None
            if hasattr(candidate, 'content') and candidate.content is not None:
                if hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                elif isinstance(candidate.content, dict):
                    parts = candidate.content.get('parts')
                elif isinstance(candidate.content, list):
                    parts = candidate.content

            if not parts:
                try:
                    finish_reason = getattr(candidate, "finish_reason", None)
                    safety_ratings = getattr(candidate, "safety_ratings", None)
                    prompt_feedback = getattr(response, "prompt_feedback", None)
                    candidate_type = str(type(candidate))
                    log_warning("图片提取", "candidate.content.parts 为空，无法提取图片", {
                        "finish_reason": str(finish_reason),
                        "safety_ratings": str(safety_ratings),
                        "prompt_feedback": str(prompt_feedback),
                        "candidate_type": candidate_type
                    })
                except Exception:
                    log_warning("图片提取", "candidate.content.parts 为空，无法提取图片")
                return None
            
            for part in parts:
                try:
                    part_type = getattr(part, "type", None)
                    data_preview = None
                    if hasattr(part, 'inline_data') and part.inline_data:
                        data = part.inline_data.data
                        data_preview = f"inline_data={type(data)}"
                    else:
                        data_preview = f"part={type(part)}"
                    log_debug("图片提取", "遍历响应 part", {"part_type": part_type, "data": data_preview})
                except Exception:
                    pass

                if hasattr(part, 'inline_data') and part.inline_data:
                    data = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    
                    # 规范化为 bytes
                    if isinstance(data, memoryview):
                        data = data.tobytes()
                    if isinstance(data, bytearray):
                        data = bytes(data)

                    # str -> base64 解码
                    if isinstance(data, str):
                        try:
                            decoded = base64.b64decode(data)
                            if ImageProcessor.validate(decoded):
                                return decoded, mime_type
                        except Exception:
                            continue
                    
                    if isinstance(data, bytes):
                        # 先尝试直接验证
                        if ImageProcessor.validate(data):
                            return data, mime_type
                        else:
                            try:
                                hex_preview = data[:32].hex()
                                log_warning("图片提取", "图片校验失败，头部预览", {"len": len(data), "hex": hex_preview})
                            except Exception:
                                pass

                        # 如果 bytes 实际是 base64(bytes)，尝试解码
                        decoded = None
                        try:
                            decoded = base64.b64decode(data, validate=True)
                        except Exception:
                            try:
                                decoded = base64.b64decode(data)
                            except Exception:
                                decoded = None

                        if decoded and ImageProcessor.validate(decoded):
                            log_warning("图片提取", "检测到 base64(bytes)，已解码为原始图片 bytes")
                            return decoded, mime_type
            
            return None
        except Exception as e:
            log_error("图片提取", f"提取失败: {e}")
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
    def validate(image_bytes: bytes) -> bool:
        """验证图片数据是否有效"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True
        except:
            return False


# ==================== 提示词优化 ====================
class PromptOptimizer:
    """提示词优化工具（单一职责）"""
    
    @staticmethod
    def optimize_for_image(prompt: str, num_reference_images: int = 0) -> str:
        """优化图片生成提示词"""
        parts = []
        
        # 添加参考图说明
        if num_reference_images > 0:
            parts.append(
                f"Based on the {num_reference_images} reference image{'s' if num_reference_images > 1 else ''} provided, "
                "please generate a new image that incorporates elements from these references."
            )
        
        # 添加原始提示词
        parts.append(f"Generate: {prompt}")
        
        # 添加质量要求
        parts.extend([
            "Requirements:",
            "- High quality and detailed output",
            "- Maintain aspect ratio consistent with references if provided",
            "- Ensure visual coherence and accuracy"
        ])
        
        return " ".join(parts)


# ==================== 主要生成函数 ====================
def generate_with_gemini_2_5_flash_image(
    prompt: str,
    reference_images: Optional[List[Image.Image]] = None,
    aspect_ratio: Optional[str] = None
) -> Optional[dict]:
    """
    使用 Gemini 2.5 Flash Image 生成图片
    
    Args:
        prompt: 提示词
        reference_images: 参考图片列表（最多 3 张）
        aspect_ratio: 长宽比（如 "3:2", "16:9"）
    
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
        
        log_info("Gemini 2.5", f"开始 {mode_str} 生成", emoji="🖼️")
        log_debug("请求参数", f"提示词: {prompt[:50]}...", {
            "参考图": len(reference_images) if has_reference else 0,
            "长宽比": aspect_ratio or "默认"
        })
        
        # 优化提示词
        optimized_prompt = PromptOptimizer.optimize_for_image(
            prompt,
            num_reference_images=len(reference_images) if has_reference else 0
        )
        
        # 构建 parts
        parts = [types.Part.from_text(text=optimized_prompt)]
        
        # 添加参考图（最多 3 张）
        if has_reference:
            for idx, ref_img in enumerate(reference_images[:3]):
                img_bytes = ImageProcessor.encode_pil_to_bytes(ref_img)
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
                log_debug("参考图", f"添加第 {idx+1} 张参考图", {"大小": f"{len(img_bytes)} bytes"})
        
        # 配置
        config_params = {
            "response_modalities": [types.Modality.IMAGE],
            "temperature": 0.4,
            "max_output_tokens": 8192,
            "safety_settings": [
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ]
        }
        
        if aspect_ratio:
            config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)
        
        config = types.GenerateContentConfig(**config_params)
        
        # 调用 API
        log_info("API调用", "发送请求到 Google...", emoji="📤")
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=[types.Content(parts=parts, role='user')],
            config=config
        )
        log_info("API调用", "模型调用完成", emoji="✅")
        
        # 提取图片
        result = ImageProcessor.extract_from_response(response)
        if not result:
            return {"error": True, "error_type": "NoImageInResponse",
                    "error_message": "响应中没有图片数据"}
        
        image_bytes, mime_type = result
        
        # 验证图片
        if not ImageProcessor.validate(image_bytes):
            return {"error": True, "error_type": "InvalidImage",
                    "error_message": "生成的图片数据无效"}
        
        # 检测格式
        detected_format = ImageProcessor.detect_format(image_bytes)
        format_name = 'jpeg' if 'jpeg' in detected_format else 'png'
        
        # 获取图片尺寸
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
        except:
            width, height = 0, 0
        
        log_success("生成完成", f"Gemini 2.5 {mode_str} 成功", {
            "大小": f"{len(image_bytes)} bytes ({len(image_bytes)/1024:.1f} KB)",
            "格式": format_name
        })
        
        # 验证 image_bytes 类型
        if not isinstance(image_bytes, bytes):
            log_error("验证失败", f"image_bytes 类型错误: {type(image_bytes)}")
            return {"error": True, "error_type": "InvalidImageType",
                    "error_message": f"image_bytes 必须是 bytes，实际为 {type(image_bytes)}"}
        
        log_info("序列化检查", "返回数据已验证为可序列化", emoji="✅")
        
        # 返回新架构格式：image_bytes + 元数据（所有字段都是可序列化的）
        return {
            "image_bytes": image_bytes,  # bytes
            "mime_type": mime_type or f"image/{format_name}",  # str
            "format": format_name,  # str
            "width": width,  # int
            "height": height  # int
        }
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        core_error = _extract_core_error_message(error_message)
        if core_error:
            error_message = core_error
        log_error("生成失败", f"Gemini 2.5 错误: {error_message}")
        logger.error(f"异常类型: {error_type}")
        logger.error(f"完整堆栈:\n{traceback.format_exc()}")
        
        # ⚠️ 重要：不要在返回的字典中包含 traceback，因为它可能包含对象引用导致序列化失败
        return {
            "error": True,
            "error_type": error_type,  # str
            "error_message": error_message  # str
        }


# 兼容旧接口
def generate_image(prompt: str, reference_images: Optional[List[Image.Image]] = None,
                  aspect_ratio: Optional[str] = None) -> Optional[dict]:
    """兼容旧函数名"""
    return generate_with_gemini_2_5_flash_image(prompt, reference_images, aspect_ratio)
