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
import time
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image
from pydantic import ValidationError

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
        
        api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY") or "").strip()
        
        if not api_key:
            logger.error("❌ GOOGLE_API_KEY 未设置")
            return None
        
        try:
            # 配置 httpx 客户端
            http_client = GeminiClient._create_http_client()
            http_options = types.HttpOptions(
                timeout=int(os.getenv('HTTP_TIMEOUT', '1200000')),
                httpx_client=http_client
            )
            
            client = genai_new.Client(
                api_key=api_key,
                http_options=http_options
            )
            
            # 输出 google-genai 版本信息（用于诊断兼容性问题）
            genai_version = getattr(genai_new, '__version__', 'unknown')
            logger.info("✅ AI Studio Client 创建成功")
            logger.info(f"📦 google-genai 版本: {genai_version}")
            
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
                logger.warning(f"⚠️ [{function_name}] response.candidates 为空，可能被安全过滤")
                return None
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
                logger.warning(f"⚠️ [{function_name}] candidate.content.parts 为空，无法提取图片")
                return None
            
            def _looks_like_base64_text(text: str) -> bool:
                if not text or len(text) % 4 != 0:
                    return False
                base64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
                return all(ch in base64_chars for ch in text)

            def _decode_base64_to_bytes(text: str) -> Optional[bytes]:
                try:
                    decoded = base64.b64decode(text, validate=True)
                    return decoded
                except Exception:
                    try:
                        return base64.b64decode(text)
                    except Exception:
                        return None

            def _is_image_magic(raw: bytes) -> bool:
                return (
                    raw.startswith(b"\xFF\xD8\xFF") or
                    raw.startswith(b"\x89PNG") or
                    raw.startswith(b"GIF87a") or
                    raw.startswith(b"GIF89a") or
                    raw.startswith(b"RIFF")  # WebP
                )

            # 查找图片 part
            found_parts = []
            for idx, part in enumerate(candidate.content.parts):
                part_type = "unknown"
                if hasattr(part, 'inline_data'):
                    part_type = "inline_data"
                elif hasattr(part, 'text'):
                    part_type = "text"
                found_parts.append(f"part[{idx}]={part_type}")

                if hasattr(part, 'inline_data') and part.inline_data:
                    mime_type = part.inline_data.mime_type
                    data = part.inline_data.data

                    if isinstance(data, bytes):
                        # 可能是 base64 文本 bytes
                        try:
                            text = data.decode('ascii')
                            if _looks_like_base64_text(text):
                                decoded = _decode_base64_to_bytes(text)
                                if decoded and _is_image_magic(decoded):
                                    logger.warning(f"⚠️ [{function_name}] inline_data 为 base64(bytes)，已解码为原始图片 bytes")
                                    return decoded, mime_type
                        except Exception:
                            pass

                        logger.info(f"✅ [{function_name}] inline_data bytes: {len(data)} bytes, mime={mime_type}")
                        return data, mime_type

                    elif isinstance(data, str):
                        # 允许 base64 字符串，解码为原始 bytes 再返回
                        if _looks_like_base64_text(data):
                            decoded = _decode_base64_to_bytes(data)
                            if decoded and _is_image_magic(decoded):
                                logger.warning(f"⚠️ [{function_name}] inline_data 为 base64(str)，已解码为原始图片 bytes")
                                return decoded, mime_type
                        logger.warning(f"⚠️ [{function_name}] inline_data 为字符串但无法解码，长度={len(data)}")
                        return None

            logger.warning(f"⚠️ [{function_name}] 未找到 inline_data 图片，parts={', '.join(found_parts)}")
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
        # 先检查数据长度
        if len(image_bytes) < 100:
            logger.error(f"❌ 图片数据太短: {len(image_bytes)} bytes")
            return False, None

        # 兜底：如果数据是 base64 文本 bytes（如 iVBOR.../9j/），先解码为原始 bytes
        try:
            if image_bytes[:4] in (b'iVBO', b'/9j/'):
                logger.warning("⚠️ 检测到 base64 文本 bytes，尝试解码为原始图片")
                decoded = base64.b64decode(image_bytes)
                if decoded:
                    image_bytes = decoded
        except Exception as e:
            logger.warning(f"base64 解码失败: {e}")
        
        # 先根据 magic bytes 快速判断格式（避免 PIL 误判）
        preview_hex = image_bytes[:16].hex()
        logger.info(f"🔍 图片数据前缀(hex): {preview_hex}, 长度: {len(image_bytes)} bytes")
        
        if image_bytes[:3] == b'\xFF\xD8\xFF':
            logger.info("✅ Magic bytes 检测: JPEG")
            # 但仍需验证完整性
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.load()
                logger.info("✅ JPEG 完整性验证通过")
                return True, 'jpeg'
            except Exception as e:
                logger.warning(f"JPEG 数据损坏: {e}")
                return False, None
                
        if image_bytes[:4] == b'\x89PNG':
            logger.info("✅ Magic bytes 检测: PNG")
            # 但仍需验证完整性
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.load()
                logger.info("✅ PNG 完整性验证通过")
                return True, 'png'
            except Exception as e:
                logger.warning(f"PNG 数据损坏: {e}")
                return False, None

        def _try_validate(raw_bytes: bytes) -> Tuple[bool, Optional[str]]:
            try:
                img = Image.open(io.BytesIO(raw_bytes))
                img.load()
                return True, img.format.lower() if img.format else 'png'
            except Exception as e:
                logger.warning(f"PIL 验证失败: {e}")
                return False, None

        is_valid, fmt = _try_validate(image_bytes)
        if is_valid:
            logger.info(f"✅ PIL 通用验证通过: {fmt}")
            return True, fmt

        # 记录调试信息（避免打印太长）
        logger.warning(f"所有验证方式均失败，size={len(image_bytes)} bytes, head(hex)={preview_hex}")
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
        
        # 创建 ImageConfig - 防御性编程：自动适配 SDK 版本
        def _create_image_config_safely(aspect_ratio_val, image_size_val):
            """
            防御性创建 ImageConfig
            - 如果 SDK 支持所有参数，就全部传递（获得最佳效果）
            - 如果 SDK 不支持某些参数，自动移除不支持的参数（保证不崩溃）
            - 优先级：全参数 > 无 output_mime_type > 无 image_size > 仅 aspect_ratio > 无配置
            """
            # 尝试顺序：从最完整到最基础
            param_sets = [
                # 1. 完整参数（最理想）- 使用 JPEG 格式减小文件大小（2K 约 800KB vs PNG 6MB）
                {"aspect_ratio": aspect_ratio_val, "image_size": image_size_val, "output_mime_type": "image/jpeg"},
                # 2. 无 output_mime_type（常见情况）
                {"aspect_ratio": aspect_ratio_val, "image_size": image_size_val},
                # 3. 仅 aspect_ratio（保底方案）
                {"aspect_ratio": aspect_ratio_val},
                # 4. 空配置（最后选择）
                {}
            ]
            
            for idx, params in enumerate(param_sets):
                # 过滤掉 None 值
                params = {k: v for k, v in params.items() if v is not None}
                if not params:  # 如果过滤后为空，跳到下一组
                    continue
                    
                try:
                    cfg = types.ImageConfig(**params)
                    logger.info(f"✅ ImageConfig 创建成功 (方案{idx+1}): {list(params.keys())}")
                    return cfg
                except (ValidationError, TypeError) as e:
                    logger.debug(f"🔄 方案{idx+1}失败: {list(params.keys())} - {str(e)[:100]}")
                    continue
            
            # 所有方案都失败，返回 None（使用模型默认配置）
            logger.warning(f"⚠️  无法创建 ImageConfig，将使用模型默认配置")
            return None
        
        # 调用防御性函数
        image_config = _create_image_config_safely(aspect_ratio, image_size)
        if image_config:
            config_params["image_config"] = image_config
        
        config = types.GenerateContentConfig(**config_params)
        
        # 调用 API
        logger.info("开始调用模型")
        logger.info(f"📤 发送请求到 Google API...")
        
        def _is_rate_limited(err: Exception) -> bool:
            message = str(err)
            return "429" in message or "RESOURCE_EXHAUSTED" in message or "too many" in message.lower()
        
        def _is_validation_error(err: Exception) -> bool:
            """检查是否是参数验证错误（通常与参数不兼容有关）"""
            error_type = type(err).__name__
            message = str(err)
            return (
                error_type in {"ValidationError", "ValueError"}
                or "Extra inputs are not permitted" in message
                or "parameter is not supported" in message
            )
        
        # 添加重试逻辑处理 429 限流和参数验证错误
        max_retries = 3
        retry_delay = 2  # 秒
        
        response = None
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-3-pro-image-preview',
                    contents=[types.Content(parts=parts, role='user')],
                    config=config
                )
                logger.info("模型调用完成")
                break  # 成功则退出重试循环
            except Exception as api_error:
                # 处理参数验证错误（如 image_size 不被支持）
                if _is_validation_error(api_error) and attempt == 1:
                    logger.warning(f"⚠️  检测到参数验证错误: {str(api_error)[:200]}")
                    if "output_mime_type" in str(api_error):
                        logger.info("🔄 尝试移除 output_mime_type 参数并重试...")
                        # 重建配置，不包含 output_mime_type
                        image_config_params_fallback = {}
                        if aspect_ratio:
                            image_config_params_fallback["aspect_ratio"] = aspect_ratio
                        if image_size:
                            image_config_params_fallback["image_size"] = image_size

                        try:
                            config_params["image_config"] = types.ImageConfig(**image_config_params_fallback)
                            config = types.GenerateContentConfig(**config_params)
                            logger.info("✅ 已重建配置（无 output_mime_type）")
                            continue  # 重试 API 调用
                        except Exception as fallback_error:
                            logger.error(f"❌ 重建配置失败: {fallback_error}")
                            raise api_error

                    if "image_size" in str(api_error):
                        logger.info("🔄 尝试移除 image_size 参数并重试...")
                        # 重建配置，不包含 image_size
                        image_config_params_fallback = {}
                        if aspect_ratio:
                            image_config_params_fallback["aspect_ratio"] = aspect_ratio
                        image_config_params_fallback["output_mime_type"] = "image/jpeg"

                        try:
                            config_params["image_config"] = types.ImageConfig(**image_config_params_fallback)
                            config = types.GenerateContentConfig(**config_params)
                            logger.info("✅ 已重建配置（无 image_size）")
                            continue  # 重试 API 调用
                        except Exception as fallback_error:
                            logger.error(f"❌ 重建配置失败: {fallback_error}")
                            raise api_error
                
                # 处理限流错误
                if _is_rate_limited(api_error) and attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # 指数退避
                    logger.warning(f"⚠️ 检测到限流，{wait_time}秒后重试 ({attempt}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ API 调用失败 (第 {attempt} 次): {api_error}")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise
        
        # 提取图片
        logger.info("🔍 开始提取图片数据...")
        result = ImageProcessor.extract_from_response(response, mode_str)
        if not result:
            logger.error(f"❌ 响应中没有图片数据")
            return {"error": True, "error_type": "NoImageInResponse",
                    "error_message": "响应中没有图片数据"}
        
        image_bytes, mime_type = result
        logger.info(f"✅ 图片数据提取成功: {len(image_bytes)} bytes, mime={mime_type}")
        
        # 验证并编码
        logger.info("🔍 开始验证图片数据...")
        is_valid, format_name = ImageProcessor.validate_and_encode(image_bytes)
        if not is_valid:
            logger.error(f"❌ 图片数据验证失败")
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
        
        # 验证 image_bytes 类型
        if not isinstance(image_bytes, bytes):
            logger.error(f"❌ image_bytes 类型错误: {type(image_bytes)}")
            return {"error": True, "error_type": "InvalidImageType",
                    "error_message": f"image_bytes 必须是 bytes，实际为 {type(image_bytes)}"}
        
        logger.info(f"✅ 序列化检查通过")
        
        # 返回统一格式（与 handler 期望一致，所有字段都是可序列化的）
        return {
            "image_bytes": image_bytes,  # bytes
            "mime_type": f"image/{format_name}",  # str
            "format": format_name or 'png',  # str
            "width": width,  # int
            "height": height  # int
        }
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        # 检测 429 配额耗尽错误
        is_quota_error = (
            "429" in error_message or 
            "RESOURCE_EXHAUSTED" in error_message or 
            "quota" in error_message.lower() or
            "rate limit" in error_message.lower()
        )
        
        if is_quota_error:
            logger.error(f"❌ [Gemini 3 Pro] API配额已耗尽")
            logger.warning(f"⏳ 建议：等待配额恢复或检查 https://aistudio.google.com/apikey")
            return {
                "error": True,
                "error_type": "QuotaExhausted",
                "error_message": "API 请求配额已耗尽。免费版限制：每分钟15次请求。请稍后重试或升级配额。"
            }
        
        logger.error(f"❌ [Gemini 3 Pro] 生成失败: {error_message}")
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
                  aspect_ratio: Optional[str] = None, image_size: str = "1K") -> Optional[dict]:
    """兼容旧函数名"""
    return generate_with_gemini_image3(prompt, reference_images, aspect_ratio, image_size)
