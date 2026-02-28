#!/usr/bin/env python3
"""
果捷后端服务 - FastAPI 主应用
"""
import os
import sys
import warnings
import base64
import io
import time
import requests
import logging
import traceback
import re
import asyncio
from typing import Optional, List, Union
from datetime import datetime

# 版本管理
from version import APP_VERSION

# 配置日志：使用 log_utils 提供的日志管理
from log_utils import setup_logging_if_needed

setup_logging_if_needed()
logger = logging.getLogger("果捷后端")
logger.info(f"✅ 日志系统初始化完成（版本: {APP_VERSION}）")

# 忽略警告
warnings.filterwarnings('ignore')

# 兼容性修复：为 Python 3.9 提供 importlib.metadata.packages_distributions
# 某些 Google 库在导入时会调用该方法，但标准库在 3.10 之前未提供
def _setup_importlib_compatibility():
    """设置importlib兼容性（安全地处理可选依赖）"""
    try:
        import importlib.metadata as _importlib_metadata
        if not hasattr(_importlib_metadata, "packages_distributions"):
            try:
                # 尝试从backport包导入（可选）
                try:
                    # 动态导入，避免静态分析检查
                    import sys
                    _backport = __import__('importlib_metadata', globals(), locals(), [], 0)
                    def _packages_distributions():
                        return _backport.packages_distributions()
                    setattr(_importlib_metadata, "packages_distributions", _packages_distributions)
                    print("✅ 已为 importlib.metadata 添加 packages_distributions 兼容实现（使用 backport）")
                except (ImportError, AttributeError):
                    # 如果 backport 不可用或不完整，提供默认实现
                    def _packages_distributions():
                        return {}
                    setattr(_importlib_metadata, "packages_distributions", _packages_distributions)
                    print("⚠️ importlib_metadata backport 未安装或不完整，使用默认实现")
            except Exception as _e:
                print(f"⚠️ 无法提供 packages_distributions 兼容实现: {_e}")
    except Exception as _e:
        print(f"⚠️ importlib.metadata 兼容性检查失败: {_e}")

_setup_importlib_compatibility()

# FastAPI 相关
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse, FileResponse
from pydantic import BaseModel

# 环境变量
from dotenv import load_dotenv
import pathlib

# ⚠️ 重要：显式加载路径，确保在容器根目录加载 .env 文件
# 参考 Google 建议：使用 os.path.join(os.getcwd(), '.env') 确保在容器根目录加载
env_paths = [
    os.path.join(os.getcwd(), '.env'),  # 容器根目录
    os.path.join(os.path.dirname(__file__), '.env'),  # backend/.env
    os.path.join(os.path.dirname(__file__), '..', '.env'),  # 项目根目录
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=False)
        print(f"✅ [main.py] 已加载环境变量文件: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    # 如果都找不到，尝试默认的 load_dotenv()（可能环境变量已通过其他方式设置）
    load_dotenv(override=False)
    print("⚠️ [main.py] 未找到 .env 文件，将使用系统环境变量或 Cloud Run 注入的环境变量")

# 配置代理和环境变量验证（使用包导入避免与 config.py 冲突）
from config.proxy_config import setup_proxy
from config.environment import validate_environment_variables

setup_proxy()

# Google Gemini API (图片生成 - 新的客户端)
# 正确的导入方式 (针对 google-genai 库)
try:
    from google import genai as genai_image
    from google.genai import types
    GEMINI_IMAGE_AVAILABLE = True
    logger.info("✅ google.genai 模块加载成功")
except ImportError as e:
    GEMINI_IMAGE_AVAILABLE = False
    logger.error(f"❌ google.genai 模块不可用，图片生成功能将不可用。错误: {e}")
    logger.error("💡 请安装: pip install google-genai")

# 图片处理
from PIL import Image

# 生成器模块
from generators import generate_with_gemini_image3, generate_with_gemini_2_5_flash_image, optimize_prompt
from generators.gemini_3_flash_preview import chat
from generators.imagen_4 import generate_with_imagen
# ========== 其他模型已屏蔽（统一使用 gemini-3-pro-image-preview）==========
# from generators import generate_with_imagen_3_capability


def _extract_session_token(req: Request) -> Optional[str]:
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "", 1).strip()

    session_token = req.query_params.get("session_token")
    if session_token:
        return session_token

    return req.cookies.get("session_token")


def _record_quantity_stat(req: Request, request_type: str) -> None:
    try:
        session_token = _extract_session_token(req)
        if not session_token:
            return

        from routes.auth import get_user_from_session
        user = get_user_from_session(session_token)
        account = user.get("account") if user else None
        if not account:
            return

        from database import increment_quantity_statistics
        increment_quantity_statistics(account=account, request_type=request_type)
    except Exception as e:
        logger.warning(f"⚠️ 数量统计记录失败: {e}")


def _sanitize_header_value(value: str, max_length: int = 200) -> str:
    """
    清理 HTTP header 值，移除非法字符
    
    Args:
        value: 原始值
        max_length: 最大长度
        
    Returns:
        清理后的安全字符串
    """
    if not value:
        return ""
    
    # 移除换行符和回车符
    sanitized = value.replace('\n', ' ').replace('\r', ' ')
    
    # 移除其他控制字符
    sanitized = ''.join(char if ord(char) >= 32 or char == '\t' else ' ' for char in sanitized)
    
    # 限制长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."
    
    # 压缩多个空格为一个
    sanitized = ' '.join(sanitized.split())
    
    return sanitized


# 配置 Vertex AI 客户端（用于 Imagen 4 API）
# ⚠️ 重点：延迟初始化，不在导入时阻塞
genai_client = None

def _init_genai_client():
    """延迟初始化 Vertex AI 客户端，避免阻塞应用启动"""
    global genai_client
    if genai_client is not None:
        return genai_client
    
    project_id = (os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    location = (os.getenv("VERTEX_AI_LOCATION") or "global").strip()
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    logger.info(f"🔧 Vertex AI 配置: project={project_id}, location={location}, credentials={'设置' if credentials else '未设置'}")

    if not project_id:
        logger.warning("⚠️ VERTEX_AI_PROJECT 未设置，Vertex AI 客户端不可用")
        return None
    elif not credentials:
        logger.warning("⚠️ GOOGLE_APPLICATION_CREDENTIALS 未设置，Vertex AI 客户端不可用")
        return None
    
    try:
        # 处理相对路径的凭据
        if credentials and not os.path.isabs(credentials):
            backend_root = pathlib.Path(__file__).parent
            candidate = (backend_root / credentials).resolve()
            if candidate.exists():
                credentials = str(candidate)
        if credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials
        
        from google.genai import types
        http_options = types.HttpOptions(timeout=int(os.getenv('HTTP_TIMEOUT', '1200000')))
        genai_client = genai_image.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=http_options
        )
        logger.info("✅ Vertex AI 客户端初始化成功")
        return genai_client
    except Exception as e:
        logger.error(f"⚠️ Vertex AI 客户端初始化失败: {e}")
        return None

# 创建 FastAPI 应用
app = FastAPI(title="果捷后端服务", version=APP_VERSION)

# ⚠️ 重点：在应用启动之前添加一个健康检查端点
# 这确保Cloud Run的健康检查能够立即获得200响应
# 而不是等待长时间的环境验证
@app.get("/health")
@app.get("/healthz")
async def health_check():
    """健康检查端点 - Cloud Run 健康检查用"""
    return {"status": "ok", "service": "果捷后端"}

# ⚠️ 关键修改：延迟环境验证，不在应用启动时阻塞
# 使用 FastAPI 的 lifespan 事件处理器
import asyncio

@app.on_event("startup")
async def startup_event():
    """应用启动事件 - 异步执行环境验证，不阻塞启动"""
    # 在后台任务中运行验证，不阻塞应用启动
    asyncio.create_task(_run_validation_async())

async def _run_validation_async():
    """异步运行环境验证"""
    await asyncio.sleep(0.1)  # 给应用足够的时间启动
    try:
        validate_environment_variables()
        logger.info("✅ 环境验证完成")
    except Exception as e:
        logger.error(f"❌ 环境验证失败: {e}")


# 配置 CORS - 使用白名单模式，只允许指定的源
# 生产环境和本地开发环境的完整URL列表
CORS_ORIGINS = [
    # 生产环境
    "https://hello-1045502692494.asia-southeast1.run.app",
    "http://gj.emaos.top",
    "http://gj.emaos.top/",
    
    # 本地开发环境
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

print(f"🌐 CORS 配置: 白名单模式，允许的源: {CORS_ORIGINS}")

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,      # 使用白名单，只允许指定的源
    allow_credentials=True,          # 允许凭证/Cookie
    allow_methods=["*"],             # 允许所有 HTTP 方法 (GET, POST 等)
    allow_headers=["*"],             # 允许所有 Header
)

# 代理健康检查端点（便于快速确认代理连通性）
@app.get("/proxy-health")
async def proxy_health():
    from config.proxy_config import check_proxy_connectivity
    import time as _time
    import json as _json
    
    status = {
        "timestamp": _time.time(),
        "proxy": check_proxy_connectivity()
    }
    return JSONResponse(content=status)

# ==================== 数据库初始化 ====================
# 导入数据库模块
try:
    from database import init_database, create_manager_account
    # 初始化数据库（启动时自动创建表和 manager 账号）
    try:
        init_database()
        # 尝试创建 manager 账号（如果密码未设置会跳过）
        try:
            result = create_manager_account()
            if result:
                logger.info(f"✅ 管理员账号已就绪: {result.get('account')}")
            else:
                logger.info("ℹ️  未创建管理员账号（密码未配置）")
        except Exception as e:
            # 捕获所有错误，不影响应用启动
            logger.warning(f"⚠️  管理员账号处理出现问题: {e}")
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.warning("⚠️  用户认证功能可能不可用")
except ImportError as e:
    logger.error(f"❌ 无法导入数据库模块: {e}")
    logger.warning("⚠️  用户认证功能不可用")

# ==================== 注册 API 路由 ====================
# 导入路由模块
try:
    from routes import auth_router, admin_router, chat_router, payment_router, feedback_router
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(chat_router)
    app.include_router(payment_router)
    app.include_router(feedback_router)
    logger.info("✅ 用户认证、管理员、聊天、支付和反馈路由已注册")
except ImportError as e:
    logger.error(f"❌ 无法导入路由模块: {e}")
    logger.warning("⚠️  部分 API 可能不可用")

# ==================== API 端点 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "果捷后端服务",
        "status": "running",
        "version": APP_VERSION
    }

# ==================== 统一的 Banana Image 接口 ====================

@app.post("/api/banana-img")
async def banana_img(request: Request):
    """
    Gemini 2.5 Flash Image 接口 (1K)
    
    - 自动使用 banana 模式（Gemini 2.5 Flash Image）
    - 支持最多3张参考图
    - FormData: 支持参考图片上传（图生图）
    - JSON: 仅支持文生图
    """
    request_id = f"{int(time.time()*1000)}"

    try:
        logger.info(f"[{request_id}] 📨 收到 banana-img 请求")
        _record_quantity_stat(request, "banana_img")

        # 导入处理器
        from handlers.banana_img_handler import handle_banana_img_request

        logger.info(f"[{request_id}] 🔄 开始解析请求数据...")

        # 强制使用 banana 模式（Gemini 2.5）
        try:
            logger.info("开始调用模型")
            response_data, status_code = await handle_banana_img_request(
                request,
                generate_with_gemini_2_5_flash_image,
                generate_with_gemini_image3,
                force_mode="banana"
            )
            logger.info("模型调用完成")
            logger.info(f"[{request_id}] ✅ 请求处理完成, status={status_code}")
        except Exception as handler_error:
            logger.error(f"发生崩溃: {str(handler_error)}", exc_info=True)
            error_msg = f"请求处理器错误: {str(handler_error)}"
            return JSONResponse({
                "success": False,
                "error_code": "HANDLER_ERROR",
                "error_message": error_msg,
                "request_id": request_id
            }, status_code=500, headers={
                "X-Error-Code": "HANDLER_ERROR",
                "X-Error-Message": _sanitize_header_value(error_msg),
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
        
        # 构建响应
        if response_data.get("success"):
            image_bytes = response_data.get("image_bytes")
            mime_type = response_data.get("mime_type", "image/jpeg")
            image_format = response_data.get("format", "jpeg")
            width = response_data.get("width", 0)
            height = response_data.get("height", 0)
            
            # ⚠️ 关键验证：确保 image_bytes 是 bytes 类型
            if not isinstance(image_bytes, bytes):
                logger.error(f"[{request_id}] ❌ 致命错误：image_bytes 类型错误: {type(image_bytes)}")
                error_msg = f"内部错误：图片数据类型不正确（{type(image_bytes).__name__}）"
                return JSONResponse({
                    "success": False,
                    "error_code": "INTERNAL_ERROR",
                    "error_message": error_msg,
                    "request_id": request_id
                }, status_code=500, headers={
                    "X-Error-Code": "INTERNAL_ERROR",
                    "X-Error-Message": _sanitize_header_value(error_msg),
                    "X-Request-ID": request_id,
                    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
                })
            
            # 构建安全的响应头（避免空字符串和非法字符）
            response_headers = {
                "Content-Length": str(len(image_bytes)),  # 显式设置，确保浏览器知道完整大小
                "X-Image-Format": str(image_format) if image_format else "unknown",
                "X-Image-Width": str(width) if width > 0 else "0",
                "X-Image-Height": str(height) if height > 0 else "0",
                "X-Model-Version": "gemini_image",
                "X-Success": "true",
                "X-Request-ID": str(request_id),
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Length, X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
            }
            
            logger.info(f"[{request_id}] ✅ 返回二进制图片数据: {len(image_bytes)} bytes ({len(image_bytes)/1024/1024:.2f}MB)")
            
            try:
                return Response(
                    content=image_bytes,
                    media_type=mime_type,
                    headers=response_headers
                )
            except Exception as response_error:
                logger.error(f"[{request_id}] ❌ 构建响应失败: {str(response_error)}", exc_info=True)
                error_msg = f"响应失败: {str(response_error)}"
                return JSONResponse({
                    "success": False,
                    "error_code": "RESPONSE_ERROR",
                    "error_message": error_msg,
                    "request_id": request_id
                }, status_code=500, headers={
                    "X-Error-Code": "RESPONSE_ERROR",
                    "X-Error-Message": _sanitize_header_value(error_msg),
                    "X-Request-ID": request_id,
                    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
                })
        else:
            error_code = response_data.get("error_code", "UNKNOWN_ERROR")
            error_message = response_data.get("error_message", "未知错误")
            return JSONResponse({
                **response_data,
                "request_id": request_id
            }, status_code=status_code, headers={
                "X-Error-Code": error_code,
                "X-Error-Message": _sanitize_header_value(error_message),
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
    
    except Exception as e:
        from log_utils import log_error
        log_error("banana-img异常", str(e))
        logger.error(traceback.format_exc())
        error_msg = str(e)
        return JSONResponse({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": error_msg,
            "request_id": request_id
        }, status_code=500, headers={
            "X-Error-Code": "INTERNAL_ERROR",
            "X-Error-Message": _sanitize_header_value(error_msg),
            "X-Request-ID": request_id,
            "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
        })


@app.post("/api/banana-img-pro")
async def banana_img_pro(request: Request):
    """
    Gemini 3 Pro Image 接口 (4K)
    
    - 自动使用 banana_pro 模式（Gemini 3 Pro Image）
    - 支持最多14张参考图
    - FormData: 支持参考图片上传（图生图）
    - JSON: 仅支持文生图
    """
    request_id = f"{int(time.time()*1000)}"
    
    try:
        logger.info(f"[{request_id}] 📨 收到 banana-img-pro 请求")
        _record_quantity_stat(request, "banana_img_pro")

        # 详细记录请求信息
        content_type = request.headers.get("content-type", "未指定")
        content_length = request.headers.get("content-length", "未指定")
        logger.debug(f"[{request_id}] 请求信息: content-type={content_type}, content-length={content_length}")

        # 导入处理器
        from handlers.banana_img_handler import handle_banana_img_request

        logger.info(f"[{request_id}] 🔄 开始解析请求数据...")

        # 强制使用 banana_pro 模式（Gemini 3 Pro）
        try:
            logger.info(f"[{request_id}] 🚀 开始调用 Gemini 3 Pro 模型")
            response_data, status_code = await handle_banana_img_request(
                request,
                generate_with_gemini_2_5_flash_image,
                generate_with_gemini_image3,
                force_mode="banana_pro"
            )
            logger.info(f"[{request_id}] ✅ 模型调用完成, status={status_code}")
        except ValueError as val_error:
            logger.error(f"[{request_id}] ❌ 参数验证错误: {str(val_error)}", exc_info=True)
            error_msg = f"参数验证失败: {str(val_error)}"
            return JSONResponse({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "error_message": error_msg,
                "request_id": request_id,
                "error_detail": str(val_error)
            }, status_code=400, headers={
                "X-Error-Code": "VALIDATION_ERROR",
                "X-Error-Message": _sanitize_header_value(error_msg),
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
        except asyncio.TimeoutError as timeout_error:
            logger.error(f"[{request_id}] ❌ 请求超时: {str(timeout_error)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error_code": "TIMEOUT_ERROR",
                "error_message": "请求处理超时（超过10分钟）",
                "request_id": request_id
            }, status_code=504, headers={
                "X-Error-Code": "TIMEOUT_ERROR",
                "X-Error-Message": "请求处理超时",
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
        except Exception as handler_error:
            logger.error(f"[{request_id}] ❌ 处理器崩溃: {str(handler_error)}", exc_info=True)
            logger.error(f"[{request_id}] 错误类型: {type(handler_error).__name__}")
            logger.error(f"[{request_id}] 完整堆栈:\n{traceback.format_exc()}")
            error_msg = f"请求处理器错误: {str(handler_error)}"
            return JSONResponse({
                "success": False,
                "error_code": "HANDLER_ERROR",
                "error_message": error_msg,
                "error_type": type(handler_error).__name__,
                "request_id": request_id
            }, status_code=500, headers={
                "X-Error-Code": "HANDLER_ERROR",
                "X-Error-Message": _sanitize_header_value(error_msg),
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })

        # 构建响应
        if response_data.get("success"):
            logger.info(f"[{request_id}] 🖼️  图片生成成功，准备返回...")
            image_bytes = response_data.get("image_bytes")
            mime_type = response_data.get("mime_type", "image/jpeg")
            image_format = response_data.get("format", "jpeg")
            width = response_data.get("width", 0)
            height = response_data.get("height", 0)

            # ⚠️ 关键验证：确保 image_bytes 是 bytes 类型
            if not isinstance(image_bytes, bytes):
                logger.error(f"[{request_id}] ❌ 致命错误：image_bytes 类型错误: {type(image_bytes)}")
                error_msg = f"内部错误：图片数据类型不正确（{type(image_bytes).__name__}）"
                return JSONResponse({
                    "success": False,
                    "error_code": "INTERNAL_ERROR",
                    "error_message": error_msg,
                    "request_id": request_id
                }, status_code=500, headers={
                    "X-Error-Code": "INTERNAL_ERROR",
                    "X-Error-Message": _sanitize_header_value(error_msg),
                    "X-Request-ID": request_id,
                    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
                })

            logger.debug(f"[{request_id}] 返回图片: format={image_format}, size={width}x{height}, mime={mime_type}, bytes={len(image_bytes)}")

            # 构建安全的响应头（只包含简单的 ASCII 值，避免协议错误）
            response_headers = {
                "Content-Length": str(len(image_bytes)),  # 显式设置，确保浏览器知道完整大小
                "X-Image-Format": str(image_format) if image_format else "unknown",
                "X-Image-Width": str(width) if width > 0 else "0",
                "X-Image-Height": str(height) if height > 0 else "0",
                "X-Model-Version": "gemini_3_pro",
                "X-Success": "true",
                "X-Request-ID": str(request_id),
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Length, X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
            }
            
            logger.info(f"[{request_id}] ✅ 返回二进制图片数据: {len(image_bytes)} bytes ({len(image_bytes)/1024/1024:.2f}MB), mime_type={mime_type}")

            try:
                return Response(
                    content=image_bytes,
                    media_type=mime_type,
                    headers=response_headers
                )
            except Exception as response_error:
                logger.error(f"[{request_id}] ❌ 构建响应失败: {str(response_error)}", exc_info=True)
                error_msg = f"响应失败: {str(response_error)}"
                return JSONResponse({
                    "success": False,
                    "error_code": "RESPONSE_ERROR",
                    "error_message": error_msg,
                    "request_id": request_id
                }, status_code=500, headers={
                    "X-Error-Code": "RESPONSE_ERROR",
                    "X-Error-Message": _sanitize_header_value(error_msg),
                    "X-Request-ID": request_id,
                    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
                })
        else:
            logger.warning(f"[{request_id}] ⚠️  生成失败: {response_data.get('error_message', '未知错误')}")
            error_code = response_data.get("error_code", "UNKNOWN_ERROR")
            error_message = response_data.get("error_message", "未知错误")
            return JSONResponse(
                {
                    **response_data,
                    "request_id": request_id
                },
                status_code=status_code,
                headers={
                    "X-Error-Code": error_code,
                    "X-Error-Message": _sanitize_header_value(error_message),
                    "X-Request-ID": request_id,
                    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
                }
            )
    
    except Exception as e:
        logger.error(f"[{request_id}] ❌ \u672a\u9884\u671f\u7684\u5916\u5c42\u5f02\u5e38: {str(e)}")
        logger.error(f"[{request_id}] \u5f02\u5e38\u7c7b\u578b: {type(e).__name__}")
        logger.error(f"[{request_id}] \u5b8c\u6574\u5806\u6808:\n{traceback.format_exc()}")
        
        return JSONResponse({
            "success": False,
            "error_code": "UNEXPECTED_ERROR",
            "error_message": f"\u672a\u9884\u671f\u9519\u8bef: {str(e)}",
            "error_type": type(e).__name__,
            "request_id": request_id
        }, status_code=500, headers={
            "X-Error-Code": "UNEXPECTED_ERROR",
            "X-Error-Message": _sanitize_header_value(f"\u672a\u9884\u671f\u9519\u8bef: {str(e)}"),
            "X-Request-ID": request_id,
            "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
        })


# ==================== Imagen 4 路由 ====================

@app.post("/api/imagen")
async def imagen(request: Request):
    """
    Imagen 4.0 图片生成接口
    
    - 支持文生图和图生图
    - 返回二进制图片数据 (blob)
    - FormData 参数: message, mode, aspect_ratio, image_size, reference_images (可选)
    """
    request_id = f"{int(time.time()*1000)}"
    logger.info(f"[{request_id}] 📨 收到 Imagen 4 请求")
    
    try:
        # ⚠️ 延迟初始化 Vertex AI 客户端
        client = _init_genai_client()
        if not client:
            logger.error(f"[{request_id}] ❌ Vertex AI 客户端初始化失败，请检查环境变量配置")
            return JSONResponse({
                "success": False,
                "error_code": "GENAI_CLIENT_INIT_FAILED",
                "message": "Vertex AI 客户端初始化失败"
            }, status_code=500, headers={
                "X-Error-Code": "GENAI_CLIENT_INIT_FAILED",
                "X-Error-Message": "Vertex AI 客户端初始化失败",
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
        
        # 解析 FormData
        form_data = await request.form()
        message = form_data.get("message", "")
        prompt = form_data.get("prompt", message)  # 兼容 prompt 和 message
        aspect_ratio = form_data.get("aspect_ratio", "1:1")
        image_size = form_data.get("image_size", "2K")
        reference_images = form_data.getlist("reference_images")
        
        logger.info(f"[{request_id}] 📝 提示词: {prompt[:100]}...")
        logger.info(f"[{request_id}] 📐 参数: aspect_ratio={aspect_ratio}, image_size={image_size}")
        logger.info(f"[{request_id}] 📸 参考图片数: {len(reference_images)}")
        
        if not prompt:
            logger.error(f"[{request_id}] ❌ 提示词不能为空")
            return JSONResponse({
                "success": False,
                "error_code": "EMPTY_PROMPT",
                "message": "提示词不能为空"
            }, status_code=400, headers={
                "X-Error-Code": "EMPTY_PROMPT",
                "X-Error-Message": "提示词不能为空",
                "X-Request-ID": request_id,
                "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
            })
        
        # 调用 Imagen 4 生成图片
        logger.info("开始调用模型")
        try:
            logger.info(f"[{request_id}] 🚀 调用 Imagen 4 API")
            data_url = generate_with_imagen(
                client,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size
            )
            logger.info("模型调用完成")
        except Exception as e:
            logger.error(f"发生崩溃: {str(e)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error_code": "MODEL_CALL_FAILED",
                "message": str(e),
                "request_id": request_id
            }, status_code=500)
        
        if data_url:
            # 从 data URL 中提取二进制数据
            if data_url.startswith('data:'):
                # 格式: data:image/jpeg;base64,/9j/4AAQ...
                header, encoded = data_url.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                image_bytes = base64.b64decode(encoded)
                
                logger.info(f"[{request_id}] ✅ Imagen 4 生图成功")
                logger.info(f"[{request_id}] 📦 图片大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
                
                # 返回二进制图片数据（与 banana-img 一致）
                return Response(
                    content=image_bytes,
                    media_type=mime_type,
                    headers={
                        "Content-Length": str(len(image_bytes)),  # 显式设置，确保浏览器知道完整大小
                        "X-Image-Format": mime_type.split('/')[-1],
                        "X-Image-Width": "",
                        "X-Image-Height": "",
                        "X-Model-Version": "imagen_4",
                        "X-Success": "true",
                        "X-Request-ID": request_id,
                        "Cache-Control": "no-cache",
                        "Access-Control-Expose-Headers": "Content-Length, X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
                    }
                )
            else:
                logger.error(f"[{request_id}] ❌ 返回的不是 data URL 格式")
                return JSONResponse({
                    "success": False,
                    "error_code": "INVALID_DATA_URL",
                    "message": "图片生成返回格式错误"
                }, status_code=500)
        else:
            logger.error(f"[{request_id}] ❌ Imagen 4 生图返回 None")
            return JSONResponse({
                "success": False,
                "error_code": "IMAGE_GENERATION_FAILED",
                "message": "图片生成失败，请查看服务器日志",
                "request_id": request_id
            }, status_code=500)
    
    except Exception as e:
        logger.error(f"[{request_id}] ❌ 异常: {str(e)}")
        logger.error(f"[{request_id}] 📋 错误堆栈:\n{traceback.format_exc()}")
        return JSONResponse({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_detail": str(e),
            "request_id": request_id
        }, status_code=500)

@app.post("/api/optimize-prompt")
async def optimize_prompt_endpoint(request: dict):
    """
    提示词优化/翻译接口
    
    ⚠️ 重要：此接口用于 banana 模式的提示词优化和 SD3.5 模式的提示词翻译
    - 如果请求中包含翻译指令（如"请将以下中文...翻译成英文"），执行翻译功能
    - 否则，执行提示词优化功能（banana 模式使用）
    """
    request_id = f"OPT-{int(time.time() * 1000)}"
    try:
        prompt = request.get("prompt", "")
        if not prompt:
            logger.warning(f"[{request_id}] ❌ 提示词为空")
            raise HTTPException(status_code=400, detail="提示词不能为空")
        
        logger.info(f"[{request_id}] 📝 收到提示词处理请求: {prompt[:100]}...")
        
        # ⚠️ 检测是否为翻译请求（SD3.5 模式使用）
        # 如果提示词包含翻译指令，执行翻译功能；否则执行优化功能
        is_translation_request = (
            "请将以下中文" in prompt or 
            "翻译成英文" in prompt or 
            "translate" in prompt.lower() or
            "translation" in prompt.lower()
        )
        
        if is_translation_request:
            logger.info(f"[{request_id}] 🌐 检测到翻译请求（SD3.5 模式），执行翻译功能")
        else:
            logger.info(f"[{request_id}] 📝 检测到优化请求（banana 模式），执行优化功能")
        
        # 使用 Gemini 文本模型处理提示词（优化或翻译）
        # ⚠️ 注意：optimize_prompt 函数会根据 prompt 的内容执行相应操作
        # 如果 prompt 是翻译指令，Gemini 会执行翻译；如果是普通提示词，会执行优化
        processed_prompt = optimize_prompt(prompt)
        
        if processed_prompt and processed_prompt.strip():
            logger.info(f"[{request_id}] ✅ 提示词处理完成: {processed_prompt[:100]}...")
            logger.info(f"[{request_id}] 📊 处理结果: 原始长度={len(prompt)}, 处理后长度={len(processed_prompt)}")
            
            result = {
                "success": True,
                "original_prompt": prompt,
                "optimized_prompt": processed_prompt,
                "prompt_length": len(processed_prompt),
                "is_translation": is_translation_request  # 标记是否为翻译结果
            }
            logger.info(f"[{request_id}] ✅ 准备返回结果: success=True, processed_prompt长度={len(processed_prompt)}")
            return result
        else:
            logger.warning(f"[{request_id}] ⚠️ 处理返回空值，返回原始提示词")
            result = {
                "success": False,
                "original_prompt": prompt,
                "optimized_prompt": prompt,
                "message": "提示词处理失败，返回原始提示词"
            }
            logger.info(f"[{request_id}] 📤 返回结果: success=False")
            return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"提示词优化接口错误: {str(e)}"
        logger.error(f"[{request_id}] ❌ {error_msg}")
        logger.error(f"[{request_id}] 📋 完整错误堆栈:\n{traceback.format_exc()}")
        result = {
            "success": False,
            "original_prompt": request.get("prompt", ""),
            "optimized_prompt": request.get("prompt", ""),
            "error_code": "OPTIMIZE_PROMPT_ERROR",
            "error_detail": str(e)
        }
        logger.error(f"[{request_id}] 📤 返回错误结果")
        return result

# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    import traceback
    
    # Cloud Run 要求监听环境变量 PORT；本地默认 8080 以对齐容器
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"🚀 启动果捷后端服务 - 地址: http://0.0.0.0:{port} | API 文档: http://0.0.0.0:{port}/docs")
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error("❌ 应用启动失败: %s", e)
        logger.error(traceback.format_exc())
        raise
