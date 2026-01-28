#!/usr/bin/env python3
"""
用户认证 API 路由
"""

import logging
import traceback
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import (
    create_user, verify_user_login, get_user_by_id,
    create_session, delete_session, verify_password
)
from config import MANAGER_ACCOUNT, MANAGER_PASSWORD
from log_utils import LogContext, log_info, log_warning, log_error, log_success, log_api

logger = logging.getLogger("认证API")

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ==================== Session 管理 ====================
# 注意：主要的会话存储现在在数据库中（database.py）
# 这个字典用于内存缓存和向后兼容，但数据会同时保存到数据库
user_sessions = {}

def generate_session_token() -> str:
    """生成会话令牌"""
    import secrets
    return secrets.token_urlsafe(32)

def get_user_from_session(session_token: Optional[str]) -> Optional[dict]:
    """
    从 session token 获取用户信息（先从数据库查询，然后检查内存缓存）
    
    Args:
        session_token: 会话令牌
        
    Returns:
        用户信息字典，如果无效返回 None
    """
    if not session_token:
        log_warning("会话", "session_token 为空")
        return None
    
    # 首先从数据库查询（这是主要来源）
    try:
        from database import get_user_from_session as db_get_user_from_session
        user = db_get_user_from_session(session_token)
        if user:
            return user
    except Exception as e:
        log_warning("会话", "从数据库查询会话失败", {"错误": str(e)})
    
    # 备用：检查内存中的会话（向后兼容旧的内存会话）
    if session_token not in user_sessions:
        log_warning("会话", "token不在session中", {
            "token": session_token[:20] if session_token else "None",
            "活跃session数": len(user_sessions)
        })
        return None
    
    user_id = user_sessions.get(session_token)
    if not user_id:
        log_warning("会话", "user_id为空")
        return None
    
    # manager 账号特殊处理（不需要从数据库查询）
    if user_id == 'manager_user':
        log_info("会话", "检测到管理员账号")
        manager_user = {
            'id': 'manager_user',
            'account': 'manager',
            'nickname': '管理员',
            'avatar': None,
            'level': 'enterprise',
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }
        return manager_user
    
    try:
        user = get_user_by_id(user_id)
        if user:
            log_info("会话", "成功获取用户", {"账号": user.get('account')})
        else:
            log_warning("会话", f"用户{user_id}不存在")
        return user
    except Exception as e:
        log_error("会话", "获取用户信息失败", {"错误": str(e)})
        return None



# ==================== 请求模型 ====================

class RegisterRequest(BaseModel):
    account: str
    password: str
    nickname: Optional[str] = None

class LoginRequest(BaseModel):
    account: str
    password: str

class SessionRequest(BaseModel):
    session_token: Optional[str] = None


# ==================== API 端点 ====================

@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册接口"""
    try:
        account = request.account.strip()
        LogContext.set_user(account)  # 设置用户上下文，所有后续日志都会包含账号信息
        password = request.password
        
        if not account:
            raise HTTPException(status_code=400, detail="账号不能为空")
        
        if not password:
            raise HTTPException(status_code=400, detail="密码不能为空")
        
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        # 验证账号格式（邮箱或手机号），manager 账号特殊处理
        if account != "manager":
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            phone_regex = r'^1[3-9]\d{8,9}$'  # 允许10-11位手机号：1 + [3-9] + 8-9位数字
            import re
            if not (re.match(email_regex, account) or re.match(phone_regex, account)):
                raise HTTPException(status_code=400, detail="账号格式不正确，请输入邮箱或手机号")
        
        # 创建用户
        user = create_user(
            account=account,
            password=password,
            nickname=request.nickname if request.nickname else None
        )
        
        # 生成 session token
        session_token = generate_session_token()
        
        # 保存到数据库（24小时过期）
        expires_at = (datetime.now() + timedelta(days=1)).isoformat()
        create_session(session_token, user['id'], expires_at)
        
        # 同时保存到内存（向后兼容）
        user_sessions[session_token] = user['id']
        
        log_success("注册", "用户注册成功", {"账号": account})
        
        return {
            "success": True,
            "user": user,
            "session_token": session_token
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # 直接抛出 HTTPException，不要捕获它
    except Exception as e:
        log_error("注册", "用户注册失败", {"错误": str(e), "类型": type(e).__name__, "traceback": traceback.format_exc()})
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")
    finally:
        LogContext.clear_user()  # 清除用户上下文


@router.post("/login")
async def login(request: LoginRequest):
    """用户登录接口"""
    try:
        account = request.account.strip()
        LogContext.set_user(account)  # 设置用户上下文，所有后续日志都会包含账号信息
        password = request.password
        
        if not account:
            raise HTTPException(status_code=400, detail="账号不能为空")
        
        if not password:
            raise HTTPException(status_code=400, detail="密码不能为空")
        
        # 管理员账号特殊处理
        # 如果是配置的管理员账号，则进行密码验证
        if account == MANAGER_ACCOUNT and MANAGER_PASSWORD:
            if password == MANAGER_PASSWORD:
                manager_user = {
                    'id': 'manager_user',
                    'account': MANAGER_ACCOUNT,
                    'nickname': '管理员',
                    'avatar': None,
                    'level': 'enterprise',
                    'createdAt': datetime.now().isoformat(),
                    'updatedAt': datetime.now().isoformat()
                }
                # 生成 session token
                session_token = generate_session_token()
                
                # 保存到数据库（24小时过期）
                expires_at = (datetime.now() + timedelta(days=1)).isoformat()
                create_session(session_token, manager_user['id'], expires_at)
                
                # 同时保存到内存（向后兼容）
                user_sessions[session_token] = manager_user['id']
                
                log_success("登录", "管理员登录成功", {"账号": account})
                return {
                    "success": True,
                    "user": manager_user,
                    "session_token": session_token
                }
            else:
                log_warning("登录", "管理员密码错误", {"账号": account})
                raise HTTPException(status_code=401, detail="密码错误")
        
        # 验证用户登录
        log_info("登录", "验证用户登录", {"账号": account, "密码长度": len(password)})
        
        user = verify_user_login(account, password)
        
        if not user:
            log_warning("登录", "验证失败", {"账号": account, "原因": "账号或密码错误"})
            raise HTTPException(status_code=401, detail="账号或密码错误")
        
        # 生成 session token
        session_token = generate_session_token()
        
        # 保存到数据库（24小时过期）
        expires_at = (datetime.now() + timedelta(days=1)).isoformat()
        create_session(session_token, user['id'], expires_at)
        
        # 同时保存到内存（向后兼容）
        user_sessions[session_token] = user['id']
        
        log_success("登录", "用户登录成功", {"账号": account})
        
        return {
            "success": True,
            "user": user,
            "session_token": session_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("登录", "用户登录失败", {"错误": str(e)})
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")
    finally:
        LogContext.clear_user()  # 清除用户上下文


@router.post("/me")
async def get_current_user(request: SessionRequest, req: Request):
    """获取当前登录用户信息"""
    try:
        # 从多个来源获取 session_token
        session_token = request.session_token
        if not session_token:
            session_token = req.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_token:
            # 从查询参数获取
            session_token = req.query_params.get("session_token")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="未提供会话令牌")
        
        # manager 账号特殊处理
        if session_token == "manager_user" or (session_token in user_sessions and user_sessions[session_token] == "manager_user"):
            manager_user = {
                'id': 'manager_user',
                'account': 'manager',
                'nickname': '管理员',
                'avatar': None,
                'level': 'enterprise',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            }
            return {
                "success": True,
                "user": manager_user
            }
        
        user = get_user_from_session(session_token)
        
        if not user:
            raise HTTPException(status_code=401, detail="会话无效或已过期")
        
        return {
            "success": True,
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("用户", "获取用户信息失败", {"错误": str(e)})
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.post("/logout")
async def logout(request: SessionRequest):
    """用户登出接口"""
    try:
        session_token = request.session_token
        
        if session_token:
            # 从数据库删除会话
            delete_session(session_token)
            
            # 同时从内存删除（向后兼容）
            if session_token in user_sessions:
                del user_sessions[session_token]
            
            log_success("登出", "用户登出成功")
        
        return {
            "success": True,
            "message": "登出成功"
        }
        
    except Exception as e:
        log_error("登出", "用户登出失败", {"错误": str(e)})
        return {
            "success": False,
            "message": f"登出失败: {str(e)}"
        }


# 导出 session 管理函数供其他模块使用
def get_user_sessions():
    """获取 session 存储（供其他模块使用）"""
    return user_sessions
