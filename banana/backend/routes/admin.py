#!/usr/bin/env python3
"""
管理员 API 路由
"""

import logging
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException, Request as Request
from pydantic import BaseModel

from database import get_all_users, update_user, get_user_feedback_count, hash_password, get_user_by_id
from routes.auth import get_user_from_session, get_user_sessions

logger = logging.getLogger("管理员API")

router = APIRouter(prefix="/api/admin", tags=["管理员"])


# ==================== 请求模型 ====================

class UpdateUserRequest(BaseModel):
    session_token: Optional[str] = None
    level: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None


def check_manager_permission(session_token: Optional[str], request: Request) -> dict:
    """
    检查是否是管理员权限
    
    Returns:
        用户信息字典
        
    Raises:
        HTTPException: 如果不是管理员
    """
    if not session_token:
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not session_token:
        session_token = request.query_params.get("session_token")
    
    if not session_token:
        raise HTTPException(status_code=401, detail="未提供会话令牌")
    
    # 检查是否是 manager
    if session_token == "manager_user" or (session_token in get_user_sessions() and get_user_sessions()[session_token] == "manager_user"):
        return {
            'id': 'manager_user',
            'account': 'manager'
        }
    
    user = get_user_from_session(session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="会话无效或已过期")
    
    if user.get('account') != 'manager':
        raise HTTPException(status_code=403, detail="无权限访问，仅管理员可操作")
    
    return user


# ==================== API 端点 ====================

@router.get("/users")
async def get_all_users_api(request: Request):
    """获取所有用户列表（管理员功能）"""
    try:
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = request.query_params.get("session_token")
        
        # 验证是否为管理员
        check_manager_permission(session_token, request)
        
        # 获取所有用户
        users = get_all_users()
        
        # 为每个用户添加反馈数量
        for user in users:
            # 特殊处理 manager 账号：如果账号是 manager，使用 'manager_user' 作为 user_id 查询反馈
            if user.get('account') == 'manager':
                user['feedbackCount'] = get_user_feedback_count('manager_user')
            else:
                user['feedbackCount'] = get_user_feedback_count(user['id'])
        
        logger.info(f"✅ 管理员获取用户列表成功，共 {len(users)} 个用户")
        
        return {
            "success": True,
            "users": users,
            "count": len(users)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.put("/users/{user_id}")
async def update_user_api(user_id: str, request: UpdateUserRequest, req: Request):
    """更新用户信息（管理员功能）"""
    try:
        session_token = request.session_token
        if not session_token:
            session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        # 验证是否为管理员
        check_manager_permission(session_token, req)
        
        # manager 账号不允许通过 API 更新
        if user_id == "manager_user":
            raise HTTPException(status_code=400, detail="无法更新 manager 账号信息")
        
        # 获取更新数据
        updates = {}
        if request.level is not None:
            updates["level"] = request.level
        if request.nickname is not None:
            updates["nickname"] = request.nickname
        if request.avatar is not None:
            updates["avatar"] = request.avatar
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有要更新的字段")
        
        # 更新用户
        updated_user = update_user(user_id, updates)
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        logger.info(f"✅ 管理员更新用户成功: {user_id}")
        
        return {
            "success": True,
            "user": updated_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"更新用户失败: {str(e)}")


@router.post("/users/{user_id}/reset-password")
async def reset_user_password_api(user_id: str, req: Request):
    """重置用户密码为 123456（管理员功能）"""
    try:
        session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            session_token = req.query_params.get("session_token")
        
        # 验证是否为管理员
        check_manager_permission(session_token, req)
        
        # manager 账号不允许重置密码
        if user_id == "manager_user":
            raise HTTPException(status_code=400, detail="无法重置 manager 账号密码")
        
        # 检查用户是否存在
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 生成新密码哈希（固定密码：123456）
        new_password = "123456"
        new_password_hash = hash_password(new_password)
        
        # 更新密码（直接更新 password_hash 字段）
        updated_user = update_user(user_id, {"password_hash": new_password_hash})
        
        if not updated_user:
            raise HTTPException(status_code=500, detail="密码重置失败")
        
        logger.info(f"✅ 管理员重置用户密码成功: {user_id} (账号: {user.get('account')})")
        
        return {
            "success": True,
            "message": "密码已重置为 123456",
            "user": updated_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置用户密码失败: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"重置用户密码失败: {str(e)}")
