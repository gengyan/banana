#!/usr/bin/env python3
"""
反馈 API 路由
"""

import logging
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from log_utils import log_info, log_error, log_success, log_warning

from database import (
    create_feedback,
    get_feedbacks_by_user_id,
    get_all_feedbacks,
    get_feedback_by_id,
    update_feedback_reply,
    get_user_feedback_count
)
from routes.auth import get_user_from_session

logger = logging.getLogger("反馈API")

router = APIRouter(prefix="/api/feedback", tags=["反馈"])


# ==================== 请求模型 ====================

class SubmitFeedbackRequest(BaseModel):
    feedback: str
    contact: str


class ReplyFeedbackRequest(BaseModel):
    reply: str


# ==================== API 端点 ====================

@router.post("/submit")
async def submit_feedback(request: SubmitFeedbackRequest, req: Request):
    """提交反馈意见"""
    try:
        # 获取会话令牌
        auth_header = req.headers.get("Authorization", "")
        session_token = auth_header.replace("Bearer ", "") if auth_header else None
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        # 添加调试日志
        log_info("反馈", "提交反馈请求", {
            "token": session_token[:20] if session_token else "None",
            "auth_header": auth_header[:50] if auth_header else "None"
        })
        
        if not session_token:
            log_warning("反馈", "未提供会话令牌")
            raise HTTPException(status_code=401, detail="未提供会话令牌")
        
        # 获取用户信息
        from routes.auth import user_sessions
        log_info("反馈", "会话信息", {
            "活跃session数": len(user_sessions),
            "token在session中": session_token in user_sessions
        })
        
        user = get_user_from_session(session_token)
        if not user:
            log_error("反馈", "会话无效或已过期", {
                "token": session_token[:20],
                "活跃sessions": str(list(user_sessions.keys())[:3])
            })
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        log_success("反馈", "成功获取用户信息", {"账号": user.get('account')})
        
        # 验证输入
        if not request.feedback or not request.feedback.strip():
            raise HTTPException(status_code=400, detail="反馈内容不能为空")
        
        if not request.contact or not request.contact.strip():
            raise HTTPException(status_code=400, detail="联系方式不能为空")
        
        # 创建反馈
        feedback = create_feedback(
            user_id=user['id'],
            account=user['account'],
            feedback=request.feedback.strip(),
            contact=request.contact.strip()
        )
        
        log_success("反馈", "用户提交反馈成功", {
            "用户": user['account'],
            "反馈ID": feedback['id']
        })
        
        return {
            "success": True,
            "feedback": feedback,
            "message": "反馈提交成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("反馈", "提交反馈失败", {"错误": str(e)})
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


@router.get("/my")
async def get_my_feedbacks(req: Request):
    """获取当前用户的反馈列表"""
    try:
        # 获取会话令牌
        session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="未提供会话令牌")
        
        # 获取用户信息
        user = get_user_from_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        # 获取反馈列表
        feedbacks = get_feedbacks_by_user_id(user['id'])
        
        log_success("反馈", "获取反馈列表成功", {
            "用户": user['account'],
            "反馈数": len(feedbacks)
        })
        
        return {
            "success": True,
            "feedbacks": feedbacks,
            "count": len(feedbacks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("反馈", "获取反馈列表失败", {"错误": str(e)})
        raise HTTPException(status_code=500, detail=f"获取反馈列表失败: {str(e)}")


@router.get("/admin/all")
async def get_all_feedbacks_admin(req: Request):
    """获取所有反馈列表（管理员功能）"""
    try:
        # 获取会话令牌
        session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="未提供会话令牌")
        
        # 获取用户信息
        user = get_user_from_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        # 检查是否是管理员
        if user.get('account') != 'manager':
            raise HTTPException(status_code=403, detail="无权限访问，仅管理员可操作")
        
        # 获取所有反馈
        feedbacks = get_all_feedbacks()
        
        log_success("反馈", "管理员获取反馈列表成功", {"反馈数": len(feedbacks)})
        
        return {
            "success": True,
            "feedbacks": feedbacks,
            "count": len(feedbacks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("反馈", "获取反馈列表失败", {"错误": str(e)})
        raise HTTPException(status_code=500, detail=f"获取反馈列表失败: {str(e)}")


@router.post("/admin/{feedback_id}/reply")
async def reply_feedback(feedback_id: str, request: ReplyFeedbackRequest, req: Request):
    """管理员回复反馈"""
    try:
        # 获取会话令牌
        session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="未提供会话令牌")
        
        # 获取用户信息
        user = get_user_from_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        # 检查是否是管理员
        if user.get('account') != 'manager':
            raise HTTPException(status_code=403, detail="无权限访问，仅管理员可操作")
        
        # 验证输入
        if not request.reply or not request.reply.strip():
            raise HTTPException(status_code=400, detail="回复内容不能为空")
        
        # 检查反馈是否存在
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="反馈不存在")
        
        # 更新回复
        updated_feedback = update_feedback_reply(feedback_id, request.reply.strip())
        
        if not updated_feedback:
            raise HTTPException(status_code=500, detail="回复失败")
        
        logger.info(f"✅ 管理员回复反馈成功: {feedback_id}")
        
        return {
            "success": True,
            "feedback": updated_feedback,
            "message": "回复成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回复反馈失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"回复反馈失败: {str(e)}")
