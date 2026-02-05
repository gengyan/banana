#!/usr/bin/env python3
"""
应用配置管理模块
处理环境变量和默认配置
"""

import os
from typing import Optional

# ==================== 数据库配置 ====================
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# ==================== 管理员账号配置 ====================
# 从环境变量获取，如果未设置则使用默认值（仅用于开发环境）
MANAGER_ACCOUNT = os.getenv('MANAGER_ACCOUNT', 'manager')
MANAGER_PASSWORD = os.getenv('MANAGER_PASSWORD', None)
MANAGER_NICKNAME = os.getenv('MANAGER_NICKNAME', '管理员')
MANAGER_LEVEL = os.getenv('MANAGER_LEVEL', 'enterprise')

# ==================== API 配置 ====================
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))

# ==================== CORS 配置 ====================
FRONTEND_ORIGINS = os.getenv('FRONTEND_ORIGINS', 'http://localhost:3000').split(',')

# ==================== 日志配置 ====================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ==================== 会话配置 ====================
SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', 24))

# ==================== 配置验证 ====================
def validate_config():
    """
    验证必要配置是否已设置
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    # 检查管理员密码是否已设置
    if not MANAGER_PASSWORD:
        errors.append(
            f"❌ 管理员密码未设置！请设置环境变量 MANAGER_PASSWORD\n"
            f"   使用方式：export MANAGER_PASSWORD='your_secure_password'"
        )
    elif len(MANAGER_PASSWORD) < 6:
        errors.append(
            f"⚠️  管理员密码过短（当前长度: {len(MANAGER_PASSWORD)} 字符）\n"
            f"   建议密码长度至少 8 字符，包含字母、数字和特殊字符"
        )
    
    return len(errors) == 0, errors


def get_config_summary():
    """
    获取配置摘要（用于调试）
    """
    return {
        'manager_account': MANAGER_ACCOUNT,
        'manager_nickname': MANAGER_NICKNAME,
        'manager_level': MANAGER_LEVEL,
        'api_host': API_HOST,
        'api_port': API_PORT,
        'session_timeout_hours': SESSION_TIMEOUT_HOURS,
        'log_level': LOG_LEVEL,
        'manager_password_set': bool(MANAGER_PASSWORD),  # 不显示密码本身
    }
