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
from typing import Optional, List, Union
from datetime import datetime

# 配置日志：使用 log_utils 提供的日志管理
from log_utils import setup_logging_if_needed

setup_logging_if_needed()
logger = logging.getLogger("果捷后端")

# 版本管理
from version import APP_VERSION

logger.info(f"✅ 日志系统初始化完成（版本: {APP_VERSION}）")

# 忽略警告
warnings.filterwarnings('ignore')

# 兼容性修复：为 Python 3.9 提供 importlib.metadata.packages_distributions
# 某些 Google 库在导入时会调用该方法，但标准库在 3.10 之前未提供
try:
    import importlib.metadata as _importlib_metadata
    if not hasattr(_importlib_metadata, "packages_distributions"):
        try:
            import importlib_metadata as _importlib_metadata_backport

            def _packages_distributions():
                return _importlib_metadata_backport.packages_distributions()

            # 动态填充缺失的 API，避免导入时异常
            setattr(_importlib_metadata, "packages_distributions", _packages_distributions)
            print("✅ 已为 importlib.metadata 添加 packages_distributions 兼容实现（使用 backport）")
        except Exception as _e:
            print(f"⚠️ 无法提供 packages_distributions 兼容实现: {_e}")
except Exception as _e:
    print(f"⚠️ importlib.metadata 兼容性检查失败: {_e}")

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

# Google Gemini API (文本生成和多模态理解)
import google.generativeai as genai

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

# 配置 Google API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️  警告: GOOGLE_API_KEY 未设置，请在 .env 文件中配置")
else:
    genai.configure(api_key=api_key)
    
    # 初始化 Google genai 客户端用于 Imagen 4 API
    try:
        genai_client = genai_image.Client(api_key=api_key)
        logger.info("✅ Google genai 客户端初始化成功")
    except Exception as e:
        logger.error(f"❌ Google genai 客户端初始化失败: {e}")
        genai_client = None

# 创建 FastAPI 应用
app = FastAPI(title="果捷后端服务", version=APP_VERSION)

# 在应用启动时执行验证
validate_environment_variables()

# 配置 CORS
# 定义允许的源（参考标准配置方式）
# 默认只包含本地开发环境，生产地址从环境变量读取
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://gj.emaos.top",
    "https://gj.emaos.top",
    "http://gj.emaos.top/",
    "https://gj.emaos.top/",
    "http://47.82.167.164",
    "http://47.82.167.164:80",
    "http://47.82.167.164:3000",
]

# 从环境变量读取生产环境的前端地址（多个地址用逗号分隔）
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
if frontend_origins_env:
    env_origins = [origin.strip() for origin in frontend_origins_env.split(",") if origin.strip()]
    for origin in env_origins:
        normalized = origin.rstrip("/")
        if normalized and normalized not in origins:
            origins.append(normalized)
        if origin.endswith("/") and origin not in origins:
            origins.append(origin)

print(f"🌐 CORS 允许的源: {origins}")

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # 允许跨域的域名列表
    allow_credentials=True,
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
        # 确保 manager 账号存在
        try:
            create_manager_account()
        except Exception as e:
            # 如果已存在，忽略错误
            if "已被注册" not in str(e):
                logger.warning(f"创建 manager 账号时出现错误: {e}")
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
            return JSONResponse({
                "success": False,
                "error_code": "HANDLER_ERROR",
                "error_message": f"请求处理器错误: {str(handler_error)}",
                "request_id": request_id
            }, status_code=500)
        
        # 构建响应
        if response_data.get("success"):
            image_bytes = response_data.get("image_bytes")
            mime_type = response_data.get("mime_type", "image/jpeg")
            image_format = response_data.get("format", "jpeg")
            width = response_data.get("width", 0)
            height = response_data.get("height", 0)
            
            return Response(
                content=image_bytes,
                media_type=mime_type,
                headers={
                    "X-Image-Format": image_format,
                    "X-Image-Width": str(width) if width else "",
                    "X-Image-Height": str(height) if height else "",
                    "X-Model-Version": "gemini_image",
                    "X-Success": "true",
                    "X-Request-ID": request_id,
                    "Cache-Control": "no-cache",
                    "Access-Control-Expose-Headers": "X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
                }
            )
        else:
            return JSONResponse({
                **response_data,
                "request_id": request_id
            }, status_code=status_code)
    
    except Exception as e:
        from log_utils import log_error
        log_error("banana-img异常", str(e))
        logger.error(traceback.format_exc())
        return JSONResponse({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": str(e),
            "request_id": request_id
        }, status_code=500)


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

        # 详细记录请求信息
        content_type = request.headers.get("content-type", "未指定")
        content_length = request.headers.get("content-length", "未指定")
        logger.debug(f"[{request_id}] 请求信息: content-type={content_type}, content-length={content_length}")

        # 导入处理器
        from handlers.banana_img_handler import handle_banana_img_request

        logger.info(f"[{request_id}] 🔄 开始解析请求数据...")

        # 强制使用 banana_pro 模式（Gemini 3 Pro）
        try:
            logger.info("开始调用模型")
            response_data, status_code = await handle_banana_img_request(
                request,
                generate_with_gemini_2_5_flash_image,
                generate_with_gemini_image3,
                force_mode="banana_pro"
            )
            logger.info("模型调用完成")
            logger.info(f"[{request_id}] ✅ 请求处理完成, status={status_code}")
        except Exception as handler_error:
            logger.error(f"发生崩溃: {str(handler_error)}", exc_info=True)
            return JSONResponse({
                "success": False,
                "error_code": "HANDLER_ERROR",
                "error_message": f"请求处理器错误: {str(handler_error)}",
                "request_id": request_id
            }, status_code=500)

        # 构建响应
        if response_data.get("success"):
            logger.info(f"[{request_id}] 🖼️  图片生成成功，准备返回...")
            image_bytes = response_data.get("image_bytes")
            mime_type = response_data.get("mime_type", "image/jpeg")
            image_format = response_data.get("format", "jpeg")
            width = response_data.get("width", 0)
            height = response_data.get("height", 0)

            logger.debug(f"[{request_id}] 返回图片: format={image_format}, size={width}x{height}, mime={mime_type}, bytes={len(image_bytes) if image_bytes else 0}")

            return Response(
                content=image_bytes,
                media_type=mime_type,
                headers={
                    "X-Image-Format": image_format,
                    "X-Image-Width": str(width) if width else "",
                    "X-Image-Height": str(height) if height else "",
                    "X-Model-Version": "gemini_3_pro",
                    "X-Success": "true",
                    "X-Request-ID": request_id,
                    "Cache-Control": "no-cache",
                    "Access-Control-Expose-Headers": "X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
                }
            )
        else:
            logger.warning(f"[{request_id}] ⚠️  生成失败: {response_data.get('error_message', '未知错误')}")
            return JSONResponse(
                {
                    **response_data,
                    "request_id": request_id
                },
                status_code=status_code
            )
    
    except ValueError as val_error:
        logger.exception(f"[{request_id}] 发生严重错误：参数验证失败")
        logger.error(f"[{request_id}] ValueError 详情: {val_error}")
        return JSONResponse({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "error_message": f"参数验证失败: {str(val_error)}",
            "request_id": request_id
        }, status_code=400)
    
    except asyncio.TimeoutError as timeout_error:
        logger.exception(f"[{request_id}] 发生严重错误：请求超时")
        logger.error(f"[{request_id}] TimeoutError 详情: {timeout_error}")
        return JSONResponse({
            "success": False,
            "error_code": "TIMEOUT_ERROR",
            "error_message": f"请求处理超时（超过10分钟）",
            "request_id": request_id
        }, status_code=504)
    
    except MemoryError as mem_error:
        logger.exception(f"[{request_id}] 发生严重错误：内存不足")
        logger.error(f"[{request_id}] MemoryError 详情: {mem_error}")
        return JSONResponse({
            "success": False,
            "error_code": "MEMORY_ERROR",
            "error_message": "服务器内存不足，请稍后重试",
            "request_id": request_id
        }, status_code=503)
    
    except Exception as e:
        logger.exception(f"[{request_id}] 发生严重错误")
        logger.error(f"[{request_id}] 异常类型: {type(e).__name__}")
        logger.error(f"[{request_id}] 异常信息: {str(e)}")
        logger.error(f"[{request_id}] 完整堆栈:\n{traceback.format_exc()}")
        
        return JSONResponse({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": f"内部服务器错误: {str(e)}",
            "error_type": type(e).__name__,
            "request_id": request_id
        }, status_code=500)


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
        if not genai_client:
            logger.error(f"[{request_id}] ❌ Google genai 客户端未初始化")
            return JSONResponse({
                "success": False,
                "error_code": "GENAI_CLIENT_INIT_FAILED",
                "message": "Google genai 客户端未初始化"
            }, status_code=500)
        
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
            }, status_code=400)
        
        # 调用 Imagen 4 生成图片
        logger.info("开始调用模型")
        try:
            logger.info(f"[{request_id}] 🚀 调用 Imagen 4 API")
            data_url = generate_with_imagen(
                genai_client,
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
                        "X-Image-Format": mime_type.split('/')[-1],
                        "X-Image-Width": "",
                        "X-Image-Height": "",
                        "X-Model-Version": "imagen_4",
                        "X-Success": "true",
                        "X-Request-ID": request_id,
                        "Cache-Control": "no-cache",
                        "Access-Control-Expose-Headers": "X-Image-Format, X-Image-Width, X-Image-Height, X-Model-Version, X-Success, X-Request-ID"
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
    
    # Cloud Run 要求监听环境变量 PORT；本地默认 8000
    port = int(os.environ.get("PORT", 8000))
    
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
