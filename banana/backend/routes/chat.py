#!/usr/bin/env python3
"""
聊天 API 路由 - Gemini 3 Flash Preview
支持多模态输入：文本 + 可选参考图片
"""

import logging
import traceback
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from log_utils import log_info, log_error, log_success

from generators.gemini_3_flash_preview import chat

logger = logging.getLogger("聊天API")

router = APIRouter(prefix="/api", tags=["聊天"])


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"
    history: list = []
    temperature: Optional[float] = None


# ==================== API 端点 ====================

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    聊天接口（纯文本）
    
    参数:
    - message: 用户消息内容
    - mode: 聊天模式（默认: "chat"）
    - history: 历史对话记录（可选）
    - temperature: 温度参数 0-2（可选，默认 1.0）
    """
    try:
        message = request.message
        mode = request.mode
        history = request.history or []
        temperature = request.temperature
        
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 调用生成器模块的聊天函数
        response_text = chat(
            message=message,
            history=history,
            temperature=temperature
        )
        
        log_success("聊天", "处理聊天请求成功", {"消息": message[:50] + "..."})
        
        return {
            "response": response_text,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("聊天", "处理聊天请求失败", {"错误": str(e)})
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "CHAT_ERROR",
            "error_detail": traceback.format_exc()
        }


@router.post("/chat-with-images")
async def chat_with_images_endpoint(request: Request):
    """
    聊天接口（支持参考图片）
    
    使用 FormData 格式：
    - message: 用户消息内容
    - mode: 聊天模式（默认: "chat"）
    - history: 历史对话记录 JSON 字符串（可选）
    - temperature: 温度参数 0-2（可选，默认 1.0）
    - reference_images: 参考图片文件列表（可选，多个）
    """
    try:
        # 解析 FormData
        form_data = await request.form()
        
        message = form_data.get('message')
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        mode = form_data.get('mode', 'chat')
        history_str = form_data.get('history')
        temperature = form_data.get('temperature')
        
        # 解析历史记录
        history_list = []
        if history_str:
            import json
            try:
                history_list = json.loads(history_str)
            except:
                logger.warning(f"⚠️ 历史记录解析失败，使用空列表")
        
        # 解析温度
        if temperature:
            try:
                temperature = float(temperature)
            except:
                temperature = None
        
        # 读取参考图片（可能多个）
        image_data_list = []
        
        # 方式1: 从 form_data 中直接获取（如果前端发送了多个 reference_images）
        reference_images = form_data.getlist('reference_images')
        
        if reference_images:
            for file in reference_images:
                if file and hasattr(file, 'filename') and file.filename:
                    try:
                        image_bytes = await file.read()
                        if image_bytes:
                            image_data_list.append(image_bytes)
                            logger.info(f"✅ 已读取参考图片: {file.filename} ({len(image_bytes)} 字节)")
                    except Exception as e:
                        logger.warning(f"⚠️ 读取参考图片失败: {file.filename}, 错误: {e}")
        
        # 调用生成器模块的聊天函数
        response_text = chat(
            message=message,
            history=history_list,
            image_data=image_data_list if image_data_list else None,
            temperature=temperature
        )
        
        log_success(
            "聊天+图片",
            "处理聊天请求成功",
            {
                "消息": message[:50] + "...",
                "图片数": len(image_data_list)
            }
        )
        
        return {
            "response": response_text,
            "success": True,
            "images_processed": len(image_data_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(
            "聊天+图片",
            "处理聊天请求失败",
            {"错误": str(e)}
        )
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "CHAT_WITH_IMAGES_ERROR",
            "error_detail": traceback.format_exc()
        }
