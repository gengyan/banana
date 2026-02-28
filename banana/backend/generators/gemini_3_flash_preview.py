"""
聊天功能模块 - Gemini 3 Flash Preview

使用 Gemini 3 Flash Preview (gemini-3-flash-preview) 模型进行文本聊天
支持多模态输入：文本 + 可选参考图片
"""
import time
import logging
import traceback
import base64
import io
import os
import re
from typing import List, Optional, Union
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    GEMINI_NEW_AVAILABLE = True
except ImportError:
    GEMINI_NEW_AVAILABLE = False
    genai = None
    types = None

import google.api_core.exceptions as gexceptions

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


def _prepare_image_part(image_data: Union[bytes, str, Path]) -> types.Part:
    """
    将各种格式的图片转换为 types.Part 对象
    
    Args:
        image_data: 图片数据（字节、base64字符串、或文件路径）
    
    Returns:
        types.Part 对象
    """
    try:
        # 如果是文件路径
        if isinstance(image_data, (str, Path)):
            path = Path(image_data)
            if path.exists():
                with open(path, 'rb') as f:
                    image_bytes = f.read()
                mime_type = _get_mime_type(str(path))
                return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        
        # 如果是字节数据
        if isinstance(image_data, bytes):
            mime_type = _detect_mime_type(image_data)
            return types.Part.from_bytes(data=image_data, mime_type=mime_type)
        
        # 如果是 base64 字符串
        if isinstance(image_data, str):
            if image_data.startswith('data:'):
                # Data URL 格式
                header, b64_data = image_data.split(',', 1)
                mime_type = header.split(':')[1].split(';')[0]
                image_bytes = base64.b64decode(b64_data)
            else:
                # 纯 base64
                image_bytes = base64.b64decode(image_data)
                mime_type = "image/jpeg"  # 默认
            return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        
        raise ValueError(f"不支持的图片格式: {type(image_data)}")
    except Exception as e:
        logger.error(f"❌ 准备图片数据失败: {e}")
        raise


def _get_mime_type(filepath: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    ext = Path(filepath).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')


def _detect_mime_type(image_bytes: bytes) -> str:
    """根据文件头识别图片 MIME 类型"""
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    elif image_bytes.startswith(b'\x89PNG'):
        return 'image/png'
    elif image_bytes.startswith(b'GIF8'):
        return 'image/gif'
    elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
        return 'image/webp'
    else:
        return 'image/jpeg'  # 默认


def chat(
    message: str,
    history: Optional[List] = None,
    image_data: Optional[Union[bytes, str, List]] = None,
    temperature: Optional[float] = None
) -> str:
    """
    使用 Gemini 3 Flash Preview 模型进行文本聊天（支持图片）
    
    ⚠️ 重要：这是文本生成函数，只返回文本，不生成图片
    - 模型: gemini-3-flash-preview（多模态文本生成模型）
    - API: client.models.generate_content()（生成内容 API）
    - 响应: response.text（文本响应）
    - 支持: 文本 + 可选参考图片
    
    功能：与用户进行文本对话（支持多模态输入）
    
    Args:
        message: 用户消息
        history: 聊天历史记录（可选）
        image_data: 参考图片数据（可选，支持字节、base64、文件路径或列表）
        temperature: 温度参数（0-2，默认 1.0）
    
    Returns:
        模型的文本回复，失败时返回友好的错误消息
    """
    try:
        # 初始化客户端（Vertex AI）
        if not GEMINI_NEW_AVAILABLE:
            logger.error("❌ google.genai 模块不可用，无法使用 Vertex AI")
            return "抱歉，AI 服务暂时不可用，请稍后重试。"

        project_id = (os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
        location = (os.getenv("VERTEX_AI_LOCATION", "global") or "").strip()
        credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not project_id:
            logger.error("❌ VERTEX_AI_PROJECT 未设置")
            return "抱歉，AI 服务暂时不可用，请稍后重试。"

        if not credentials:
            logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS 未设置")
            return "抱歉，AI 服务暂时不可用，请稍后重试。"

        # 处理相对路径的凭据
        if credentials and not os.path.isabs(credentials):
            backend_root = Path(__file__).parent.parent
            candidate = (backend_root / credentials).resolve()
            if candidate.exists():
                credentials = str(candidate)

        # 设置凭据环境变量
        if credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials

        try:
            http_options = types.HttpOptions(timeout=int(os.getenv('HTTP_TIMEOUT', '1200000')))
            client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                http_options=http_options
            )
            model_name = 'gemini-3-flash-preview'
        except Exception as e:
            logger.error(f"❌ 初始化 Vertex AI 客户端失败: {e}")
            return "抱歉，AI 服务暂时不可用，请稍后重试。"
        
        # 构建内容列表
        parts = []
        
        # 添加参考图片（如果有）
        if image_data:
            try:
                images = [image_data] if not isinstance(image_data, list) else image_data
                for img in images:
                    if img:
                        part = _prepare_image_part(img)
                        parts.append(part)
                        logger.info(f"✅ 已添加参考图片 ({len(parts)} 张)")
            except Exception as e:
                logger.warning(f"⚠️ 添加参考图片失败，继续使用纯文本: {e}")
        
        # 添加文本消息
        parts.append(types.Part.from_text(text=message))
        
        # 构建内容对象
        contents = [types.Content(role="user", parts=parts)]
        
        # 如果有历史记录，添加到前面
        if history and isinstance(history, list):
            history_contents = []
            for item in history:
                if isinstance(item, dict):
                    role = item.get('role', 'user')
                    text = item.get('content', '')
                    if text:
                        history_contents.append(
                            types.Content(role=role, parts=[types.Part.from_text(text=text)])
                        )
            if history_contents:
                contents = history_contents + contents
        
        # 配置生成参数
        config_kwargs = {
            "temperature": temperature or 1.0,
            "top_p": 0.95,
            "max_output_tokens": 8192,
        }
        
        # 添加安全设置（关闭所有过滤）
        config_kwargs["safety_settings"] = [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(**config_kwargs)
        
        # 生成回复（带重试机制）
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Gemini 3 Flash Preview 发送请求 (尝试 {attempt + 1}/{max_retries})")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=generate_content_config
                )
                
                result_text = response.text if response and hasattr(response, 'text') else ""
                if not result_text:
                    return "抱歉，AI 返回了空响应，请重试。"
                
                logger.info(f"✅ Gemini 3 Flash Preview 响应成功，长度: {len(result_text)}")
                return result_text
                
            except gexceptions.ServiceUnavailable as e:
                error_msg = str(e)
                core_error = _extract_core_error_message(error_msg)
                if core_error:
                    logger.warning(f"⚠️ Gemini 3 错误: {core_error}")
                    return core_error
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 请求失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {error_msg[:100]}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    if "Timeout" in error_msg or "failed to connect" in error_msg:
                        return "抱歉，网络连接超时，可能是网络问题或服务暂时不可用。请检查网络连接后重试。"
                    else:
                        return "抱歉，AI 服务暂时不可用，请稍后重试。"
                        
            except gexceptions.RetryError as e:
                error_msg = str(e)
                core_error = _extract_core_error_message(error_msg)
                if core_error:
                    logger.warning(f"⚠️ Gemini 3 错误: {core_error}")
                    return core_error
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 请求失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {error_msg[:100]}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    if "Timeout" in error_msg:
                        return "抱歉，请求超时，可能是网络问题。请检查网络连接后重试。"
                    else:
                        return "抱歉，AI 服务暂时不可用，请稍后重试。"
        
        return "抱歉，AI 服务暂时不可用，请稍后重试。"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 聊天失败: {e}")
        logger.error(traceback.format_exc())
        
        core_error = _extract_core_error_message(error_msg)
        if core_error:
            return core_error
        if "Timeout" in error_msg or "timeout" in error_msg.lower():
            return "抱歉，请求超时，可能是网络问题。请检查网络连接后重试。"
        elif "503" in error_msg or "ServiceUnavailable" in error_msg:
            return "抱歉，AI 服务暂时不可用，请稍后重试。"
        elif "failed to connect" in error_msg.lower():
            return "抱歉，无法连接到 AI 服务，请检查网络连接。"
        else:
            return "抱歉，处理请求时出错。如果问题持续，请联系技术支持。"
