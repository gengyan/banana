"""
API 路由模块
"""

from .auth import router as auth_router
from .admin import router as admin_router
from .chat import router as chat_router
from .payment import router as payment_router
from .feedback import router as feedback_router

__all__ = ['auth_router', 'admin_router', 'chat_router', 'payment_router', 'feedback_router']
