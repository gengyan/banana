"""
配置模块 - 提取代理、环境验证等配置逻辑
"""

from .proxy_config import setup_proxy
from .environment import validate_environment_variables

# 直接读取并定义配置常量（避免循环导入）
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")
MANAGER_ACCOUNT = os.getenv('MANAGER_ACCOUNT', 'manager')
MANAGER_PASSWORD = os.getenv('MANAGER_PASSWORD', None)
MANAGER_NICKNAME = os.getenv('MANAGER_NICKNAME', '管理员')
MANAGER_LEVEL = os.getenv('MANAGER_LEVEL', 'enterprise')
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))
FRONTEND_ORIGINS = os.getenv('FRONTEND_ORIGINS', 'http://localhost:3000').split(',')

__all__ = [
    'setup_proxy', 
    'validate_environment_variables',
    'DB_PATH',
    'MANAGER_ACCOUNT',
    'MANAGER_PASSWORD', 
    'MANAGER_NICKNAME',
    'MANAGER_LEVEL',
    'API_HOST',
    'API_PORT',
    'FRONTEND_ORIGINS'
]
