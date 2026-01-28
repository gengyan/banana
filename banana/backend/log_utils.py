"""
日志管理工具 - 简化和统一日志输出，支持结构化日志和用户上下文
"""
import logging
import os
import sys
import traceback
from typing import Optional, Dict, Any
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("果捷后端")


def setup_logging_if_needed():
    """
    设置日志系统（如果还没设置的话）
    同时输出到终端和文件
    """
    root_logger = logging.getLogger()
    
    # 如果已经有处理器，说明日志已初始化
    if root_logger.handlers:
        return
    
    root_logger.setLevel(logging.INFO)
    
    # 日志格式
    log_format = logging.Formatter(
        '[后端] %(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 终端输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 2. 文件输出（RotatingFileHandler）
    log_file = os.path.join(os.path.dirname(__file__), 'backend.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)


# 日志级别配置（保留原有的 basicConfig 以兼容性考虑）
logging.basicConfig(
    level=logging.INFO,
    format='[后端] %(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class LogContext:
    """日志上下文管理 - 在日志中添加用户信息等"""
    _context: Dict[str, Any] = {}
    
    @classmethod
    def set_user(cls, account: str, user_id: Optional[str] = None):
        """设置当前用户信息"""
        cls._context['user_account'] = account
        cls._context['user_id'] = user_id
    
    @classmethod
    def clear_user(cls):
        """清除用户信息"""
        cls._context.pop('user_account', None)
        cls._context.pop('user_id', None)
    
    @classmethod
    def get_user_prefix(cls) -> str:
        """获取用户前缀（用于日志）"""
        if 'user_account' in cls._context:
            return f"[{cls._context['user_account']}]"
        return ""
    
    @classmethod
    @contextmanager
    def user_session(cls, account: str, user_id: Optional[str] = None):
        """上下文管理器 - 自动管理用户信息"""
        cls.set_user(account, user_id)
        try:
            yield
        finally:
            cls.clear_user()


def log_info(title: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None, 
             emoji: str = "ℹ️", is_separator: bool = False):
    """
    简化日志输出 - 替代多行 logger.info 调用
    
    Args:
        title: 日志标题
        message: 日志消息（可选）
        details: 详细信息字典（可选）
        emoji: 表情符号前缀（默认: ℹ️）
        is_separator: 是否显示分隔线
    
    Examples:
        log_info("开始处理图片", emoji="🖼️")
        log_info("图片信息", details={"大小": "1.5MB", "格式": "PNG"})
        log_info("处理完成", "生成了3张图片", emoji="✅")
        log_info("关键操作", is_separator=True)
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    if is_separator:
        logger.info("=" * 80)
    
    if message:
        # 标题 + 消息格式
        if details:
            details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
            logger.info(f"{prefix} {message} - {details_str}")
        else:
            logger.info(f"{prefix} {message}")
    else:
        # 仅标题，或标题 + 详情
        if details:
            details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
            logger.info(f"{prefix} {details_str}")
        else:
            logger.info(prefix)
    
    if is_separator:
        logger.info("=" * 80)


def log_debug(title: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None, 
              emoji: str = "🔧"):
    """
    调试日志 - 用于详细的技术信息
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    if message:
        if details:
            details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
            logger.debug(f"{prefix} {message} - {details_str}")
        else:
            logger.debug(f"{prefix} {message}")
    else:
        if details:
            details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
            logger.debug(f"{prefix} {details_str}")
        else:
            logger.debug(prefix)


def log_warning(title: str, message: str, details: Optional[Dict[str, Any]] = None, 
                emoji: str = "⚠️"):
    """
    警告日志
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    if details:
        details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        logger.warning(f"{prefix} {message} - {details_str}")
    else:
        logger.warning(f"{prefix} {message}")


def log_error(title: str, message: str, details: Optional[Dict[str, Any]] = None, 
              emoji: str = "❌"):
    """
    错误日志
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    if details:
        details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        logger.error(f"{prefix} {message} - {details_str}")
    else:
        logger.error(f"{prefix} {message}")


def log_success(title: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """
    成功日志
    """
    log_info(title, message, details, emoji="✅")


def log_step(step_num: int, title: str, status: str = "进行中", emoji: str = "📍"):
    """
    步骤日志 - 用于多步骤流程
    
    Examples:
        log_step(1, "初始化", "完成")
        log_step(2, "处理数据")
        log_step(3, "上传结果", "失败")
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [步骤{step_num}]" if user_prefix else f"{emoji} [步骤{step_num}]"
    logger.info(f"{prefix} {title} ({status})")


def log_exception(title: str, message: str, exception: Optional[Exception] = None, 
                  emoji: str = "❌", include_traceback: bool = False):
    """
    异常日志 - 记录异常信息，可选包含堆栈跟踪
    
    Args:
        title: 日志标题
        message: 错误信息
        exception: 异常对象
        emoji: 表情符号前缀
        include_traceback: 是否包含详细堆栈跟踪
    
    Examples:
        try:
            do_something()
        except Exception as e:
            log_exception("处理失败", "无法处理数据", e, include_traceback=True)
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    error_msg = message
    if exception:
        error_msg = f"{message}: {str(exception)}"
    
    logger.error(f"{prefix} {error_msg}")
    
    if include_traceback and exception:
        logger.error(traceback.format_exc())


def log_multiline(title: str, message: str, lines: list, emoji: str = "📋"):
    """
    多行日志 - 用于输出列表/多行数据
    
    Args:
        title: 日志标题
        message: 说明信息
        lines: 要输出的行列表
        emoji: 表情符号前缀
    
    Examples:
        log_multiline("查询结果", "找到3条用户信息", [
            "- 用户1: user1@example.com",
            "- 用户2: user2@example.com",
            "- 用户3: user3@example.com"
        ])
    """
    user_prefix = LogContext.get_user_prefix()
    prefix = f"{emoji} {user_prefix} [{title}]" if user_prefix else f"{emoji} [{title}]"
    
    logger.info(f"{prefix} {message} ({len(lines)}项)")
    for line in lines[:10]:  # 最多输出10行，防止日志过多
        logger.info(f"  {line}")
    if len(lines) > 10:
        logger.info(f"  ... 还有 {len(lines) - 10} 项")


def log_transaction(title: str, operation: str, success: bool = True, 
                    details: Optional[Dict[str, Any]] = None):
    """
    事务日志 - 用于数据库操作、支付等事务性操作
    
    Args:
        title: 事务标题
        operation: 操作类型 (INSERT, UPDATE, DELETE, SELECT等)
        success: 是否成功
        details: 操作详情
    
    Examples:
        log_transaction("用户管理", "INSERT", True, {"user_id": "123", "account": "user@example.com"})
        log_transaction("支付订单", "UPDATE", False, {"error": "支付失败", "order_id": "ORD123"})
    """
    emoji = "✅" if success else "❌"
    status = "成功" if success else "失败"
    log_func = log_success if success else log_error
    
    message = f"{operation} {status}"
    log_func(title, message, details, emoji)


def log_api(method: str, endpoint: str, status_code: int = 200, 
            details: Optional[Dict[str, Any]] = None):
    """
    API日志 - 用于API请求/响应
    
    Args:
        method: HTTP方法 (GET, POST, PUT, DELETE等)
        endpoint: API端点
        status_code: 响应状态码
        details: 请求/响应详情
    
    Examples:
        log_api("POST", "/api/auth/login", 200, {"account": "user@example.com", "time": "0.5s"})
        log_api("POST", "/api/auth/login", 401, {"error": "password incorrect"})
    """
    emoji = "✅" if status_code < 400 else ("⚠️" if status_code < 500 else "❌")
    message = f"{method} {endpoint}"
    
    details_with_code = {"状态码": status_code}
    if details:
        details_with_code.update(details)
    
    log_func = log_success if status_code < 300 else log_warning if status_code < 400 else log_error
    log_func("API", message, details_with_code, emoji)
