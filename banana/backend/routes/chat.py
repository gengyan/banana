#!/usr/bin/env python3
"""
聊天 API 路由
"""

import logging
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from generators import chat

logger = logging.getLogger("聊天API")

router = APIRouter(prefix="/api", tags=["聊天"])


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"
    history: list = []


# ==================== API 端点 ====================

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    聊天接口
    
    参数:
    - message: 用户消息内容
    - mode: 聊天模式（默认: "chat"）
    - history: 历史对话记录（可选）
    """
    try:
        message = request.message
        mode = request.mode
        history = request.history or []
        
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 调用生成器模块的聊天函数
        response_text = chat(message, history)
        
        logger.info(f"✅ 聊天请求处理成功: {message[:50]}...")
        
        return {
            "response": response_text,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"聊天接口错误: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "CHAT_ERROR",
            "error_detail": traceback.format_exc()
        }
