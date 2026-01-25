"""
聊天功能模块

使用 Gemini 2.0 Flash Exp (gemini-2.0-flash-exp) 模型进行文本聊天
"""
import time
import logging
import traceback
from typing import List, Optional
import google.generativeai as genai
import google.api_core.exceptions as gexceptions

logger = logging.getLogger("果捷后端")


def chat(message: str, history: Optional[List] = None) -> str:
    """
    使用 Gemini 2.0 Flash Exp 模型进行文本聊天
    
    ⚠️ 重要：这是文本生成函数，只返回文本，不生成图片
    - 模型: gemini-2.0-flash-exp（文本生成模型）
    - API: model.start_chat().send_message()（文本聊天 API）
    - 响应: response.text（文本响应）
    
    功能：与用户进行文本对话（纯文本处理）
    
    Args:
        message: 用户消息
        history: 聊天历史记录（可选）
    
    Returns:
        模型的文本回复，失败时返回友好的错误消息
    """
    try:
        # 使用 gemini-2.0-flash-exp 模型
        model_name = 'gemini-2.0-flash-exp'
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"❌ 模型 {model_name} 不可用: {e}")
            return "抱歉，AI 服务暂时不可用，请稍后重试。"
        
        # 构建聊天历史
        chat_session = model.start_chat(history=[])
        if history:
            for item in history:
                if isinstance(item, dict) and 'role' in item and 'content' in item:
                    # 这里可以根据实际历史格式调整
                    pass
        
        # 生成回复（带重试机制）
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = chat_session.send_message(message)
                return response.text
            except gexceptions.ServiceUnavailable as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️  请求失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {error_msg[:100]}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                else:
                    if "Timeout" in error_msg or "failed to connect" in error_msg:
                        return "抱歉，网络连接超时，可能是网络问题或服务暂时不可用。请检查网络连接后重试。"
                    else:
                        return "抱歉，AI 服务暂时不可用，请稍后重试。"
            except gexceptions.RetryError as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️  请求失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {error_msg[:100]}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
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
        
        # 提供更友好的错误消息
        if "Timeout" in error_msg or "timeout" in error_msg.lower():
            return "抱歉，请求超时，可能是网络问题。请检查网络连接后重试。"
        elif "503" in error_msg or "ServiceUnavailable" in error_msg:
            return "抱歉，AI 服务暂时不可用，请稍后重试。"
        elif "failed to connect" in error_msg.lower():
            return "抱歉，无法连接到 AI 服务，请检查网络连接。"
        else:
            return f"抱歉，处理请求时出错。如果问题持续，请联系技术支持。"
