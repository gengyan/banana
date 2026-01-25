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

# 配置日志：同时输出到终端和文件
import sys
from logging.handlers import RotatingFileHandler

# 创建日志格式（添加 [后端] 前缀以便区分）
log_format = logging.Formatter(
    '[后端] %(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 清除现有的处理器
root_logger.handlers.clear()

# 1. 终端输出（StreamHandler）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)
root_logger.addHandler(console_handler)

# 2. 文件输出（RotatingFileHandler，自动轮转）
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

logger = logging.getLogger("果捷后端")
logger.info("✅ 日志系统初始化完成（同时输出到终端和文件）")

# 忽略警告
warnings.filterwarnings('ignore')

# FastAPI 相关
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
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

# 配置代理（需要在导入 Google API 之前处理）
# ⚠️ 重要：在 Cloud Run 环境中，必须关闭代理，避免干扰
# 检测是否在 Cloud Run 环境（通过 K_SERVICE 环境变量）
is_cloud_run = bool(os.getenv('K_SERVICE'))
disable_proxy = os.getenv("DISABLE_PROXY", "").lower() == "true" or is_cloud_run

if disable_proxy or is_cloud_run:
    print("✅ 代理已禁用（Cloud Run 环境或 DISABLE_PROXY=true），直接连接")
    # 清除所有代理环境变量（包括从 .env 文件加载的）
    proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    for key in proxy_keys:
        if key in os.environ:
            os.environ.pop(key, None)  # 使用 pop 确保完全移除
            print(f"   ✅ 已移除代理环境变量: {key}")
else:
    proxy_url = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("http_proxy") or os.getenv("https_proxy")
    if proxy_url:
        print(f"✅ 使用代理: {proxy_url}")
        # 设置环境变量，让Google API客户端使用代理
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url

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
from generators import generate_with_gemini_image3, generate_with_gemini_2_5_flash_image, optimize_prompt, chat
# ========== 其他模型已屏蔽（统一使用 gemini-3-pro-image-preview）==========
# from generators import generate_with_imagen, generate_with_imagen_3_capability

# 配置 Google API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️  警告: GOOGLE_API_KEY 未设置，请在 .env 文件中配置")
else:
    genai.configure(api_key=api_key)

# 创建 FastAPI 应用
app = FastAPI(title="果捷后端服务", version="1.3.0")

# ⚠️ 重要：启动时验证关键环境变量并输出到日志
def validate_environment_variables():
    """验证关键环境变量是否已加载，输出详细日志"""
    logger.info("=" * 80)
    logger.info("🔍 [启动验证] 检查关键环境变量配置")
    logger.info("=" * 80)
    
    # 检查工作目录和文件列表
    current_dir = os.getcwd()
    logger.info(f"📁 当前工作目录: {current_dir}")
    
    # 列出当前目录的文件（用于调试）
    try:
        files_in_dir = os.listdir(current_dir)
        logger.info(f"📋 当前目录文件列表: {', '.join(files_in_dir[:20])}...")  # 只显示前20个
    except Exception as e:
        logger.warning(f"⚠️ 无法列出目录文件: {e}")
    
    # 检查 .env 文件
    env_file_path = os.path.join(current_dir, '.env')
    if os.path.exists(env_file_path):
        logger.info(f"✅ .env 文件存在: {env_file_path}")
    else:
        logger.warning(f"⚠️ .env 文件不存在: {env_file_path}")
    
    # 检查 google-key.json 文件
    google_key_paths = [
        os.path.join(current_dir, 'google-key.json'),
        os.path.join(os.path.dirname(__file__), 'google-key.json'),
        os.path.join(os.path.dirname(__file__), '..', 'google-key.json'),
    ]
    google_key_found = False
    google_key_path = None
    for key_path in google_key_paths:
        if os.path.exists(key_path):
            logger.info(f"✅ google-key.json 文件存在: {key_path}")
            google_key_found = True
            google_key_path = os.path.abspath(key_path)
            # ⚠️ 重要：如果文件存在但环境变量未设置，自动设置环境变量
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_path
                logger.info(f"✅ 自动设置 GOOGLE_APPLICATION_CREDENTIALS: {google_key_path}")
            break
    
    if not google_key_found:
        logger.warning("⚠️ google-key.json 文件未找到，列出当前目录文件:")
        try:
            current_files = os.listdir(current_dir)
            logger.warning(f"   当前目录文件: {', '.join(current_files)}")
        except Exception as e:
            logger.warning(f"   无法列出文件: {e}")
    
    # 检查关键环境变量（使用 Fallback 机制）
    vertex_ai_project = os.getenv("VERTEX_AI_PROJECT")
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # ⚠️ 重要：在 Cloud Run 环境中，如果环境变量未设置，尝试从元数据服务器获取项目 ID
    if not vertex_ai_project and not google_cloud_project:
        # 检测是否在 Cloud Run 环境
        if os.getenv('K_SERVICE'):
            logger.info("🌐 检测到 Cloud Run 环境，尝试从元数据服务器获取项目 ID...")
            try:
                import requests
                # 从元数据服务器获取项目 ID
                metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
                headers = {"Metadata-Flavor": "Google"}
                response = requests.get(metadata_url, headers=headers, timeout=2)
                if response.status_code == 200:
                    project_id_from_metadata = response.text.strip()
                    logger.info(f"✅ 从元数据服务器获取到项目 ID: {project_id_from_metadata}")
                    os.environ['GOOGLE_CLOUD_PROJECT'] = project_id_from_metadata
                    os.environ['VERTEX_AI_PROJECT'] = project_id_from_metadata
                    google_cloud_project = project_id_from_metadata
                    vertex_ai_project = project_id_from_metadata
                else:
                    logger.warning(f"⚠️ 元数据服务器返回状态码: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ 无法从元数据服务器获取项目 ID: {str(e)}")
                logger.warning("   这可能是正常的（如果不在 Cloud Run 环境中）")
    
    # Fallback 机制：如果 VERTEX_AI_PROJECT 缺失，尝试读取 GOOGLE_CLOUD_PROJECT
    if not vertex_ai_project and google_cloud_project:
        logger.info(f"✅ 使用 Fallback 机制: GOOGLE_CLOUD_PROJECT -> VERTEX_AI_PROJECT")
        os.environ['VERTEX_AI_PROJECT'] = google_cloud_project
        vertex_ai_project = google_cloud_project
    
    # 验证关键环境变量（智能检查，不要求所有变量都设置）
    # ⚠️ 重要：重新获取 GOOGLE_APPLICATION_CREDENTIALS（可能已被自动设置）
    google_app_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if google_key_found and google_key_path and not google_app_credentials:
        google_app_credentials = google_key_path
    
    critical_vars = {
        "VERTEX_AI_PROJECT": vertex_ai_project or os.getenv("GOOGLE_CLOUD_PROJECT"),
        "GOOGLE_CLOUD_PROJECT": google_cloud_project,
        "VERTEX_AI_LOCATION": os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION"),
        "GOOGLE_CLOUD_API_KEY": "已设置" if os.getenv("GOOGLE_CLOUD_API_KEY") else "未设置",
        "GOOGLE_APPLICATION_CREDENTIALS": google_app_credentials or ("已找到文件" if google_key_found else "未设置"),
    }
    
    logger.info("📋 环境变量状态:")
    # ⚠️ 智能验证：不是所有变量都必须设置
    # 1. 项目 ID 必须设置（VERTEX_AI_PROJECT 或 GOOGLE_CLOUD_PROJECT 之一）
    # 2. 认证方式必须设置（GOOGLE_CLOUD_API_KEY 或 GOOGLE_APPLICATION_CREDENTIALS 之一）
    for var_name, var_value in critical_vars.items():
        if var_value and var_value != "未设置":
            logger.info(f"   ✅ {var_name}: {var_value if 'KEY' not in var_name and 'CREDENTIALS' not in var_name else '***已设置***'}")
        else:
            # ⚠️ 智能判断：某些变量未设置可能是正常的
            if var_name == "GOOGLE_CLOUD_PROJECT" and vertex_ai_project:
                # 如果 VERTEX_AI_PROJECT 已设置，GOOGLE_CLOUD_PROJECT 未设置是正常的
                logger.info(f"   ℹ️ {var_name}: 未设置（但 VERTEX_AI_PROJECT 已设置，不影响使用）")
            elif var_name == "GOOGLE_CLOUD_API_KEY" and (google_app_credentials or google_key_found):
                # 如果使用服务账户凭据，API Key 未设置是正常的
                logger.info(f"   ℹ️ {var_name}: 未设置（但已配置服务账户凭据，不影响使用）")
            else:
                logger.warning(f"   ⚠️ {var_name}: 未设置")
    
    # 重新评估 all_ok（更智能的判断）
    all_ok = True
    
    # 检查项目 ID（最关键）
    project_id = vertex_ai_project or google_cloud_project
    if not project_id:
        logger.error("=" * 80)
        logger.error("🚨 [严重警告] VERTEX_AI_PROJECT 和 GOOGLE_CLOUD_PROJECT 均未设置！")
        logger.error("🚨 [严重警告] 这将导致 Gemini 图片生成功能无法使用！")
        logger.error("🚨 [严重警告] 请检查：")
        logger.error("   1. .env 文件是否存在并包含正确的配置")
        logger.error("   2. Cloud Run 环境变量是否通过 --set-env-vars 设置")
        logger.error("   3. 是否在 Cloud Run 环境中（会自动注入 GOOGLE_CLOUD_PROJECT）")
        logger.error("=" * 80)
        all_ok = False
    else:
        logger.info(f"✅ 项目 ID: {project_id}")
    
    # 检查认证方式（重新获取，可能已被自动设置）
    has_api_key = bool(os.getenv("GOOGLE_CLOUD_API_KEY"))
    has_credentials = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) or google_key_found
    
    if not has_api_key and not has_credentials:
        logger.error("=" * 80)
        logger.error("🚨 [严重警告] 未设置任何认证方式！")
        logger.error("🚨 [严重警告] 请设置 GOOGLE_CLOUD_API_KEY 或 GOOGLE_APPLICATION_CREDENTIALS")
        logger.error("🚨 [严重警告] 或者确保 google-key.json 文件存在于容器中")
        logger.error("=" * 80)
        all_ok = False
    else:
        if has_credentials:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or (google_key_path if google_key_found else "未指定")
            logger.info(f"✅ 认证方式: 服务账户凭据 ({creds_path})")
        if has_api_key:
            logger.info(f"✅ 认证方式: API Key")
    
    logger.info("=" * 80)
    if all_ok:
        logger.info("✅ [启动验证] 环境变量配置检查通过")
    else:
        logger.error("❌ [启动验证] 环境变量配置检查失败，请查看上述警告")
    logger.info("=" * 80)
    
    return all_ok

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
]

# 从环境变量读取生产环境的前端地址（多个地址用逗号分隔）
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
if frontend_origins_env:
    env_origins = [origin.strip() for origin in frontend_origins_env.split(",") if origin.strip()]
    for origin in env_origins:
        if origin not in origins:
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

# ==================== 辅助函数 ====================

# ========== 已屏蔽（统一使用 gemini-3-pro-image-preview，不再需要单独的 Imagen Client）==========
# def _get_genai_client_for_imagen():
#     """获取或创建 google.genai Client 实例（用于 Imagen 4.0）"""
#     try:
#         from generators.gemini_3_pro_image import _get_genai_client
#         return _get_genai_client()
#     except ImportError:
#         # 如果无法导入，尝试直接创建
#         try:
#             from google import genai as genai_new
#             import os
#             
#             vertex_ai_project = os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
#             vertex_ai_location = os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "global")
#             google_app_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#             
#             if not vertex_ai_project or not google_app_credentials:
#                 logger.error("❌ VERTEX_AI_PROJECT 或 GOOGLE_APPLICATION_CREDENTIALS 未设置")
#                 return None
#             
#             os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials
#             client = genai_new.Client(
#                 vertexai=True,
#                 project=vertex_ai_project,
#                 location=vertex_ai_location
#             )
#             return client
#         except Exception as e:
#             logger.error(f"❌ 创建 Vertex AI Client 失败: {e}")
#             return None

def generate_image_with_google(prompt: str, reference_images: Optional[List[Image.Image]] = None, 
                               aspect_ratio: Optional[str] = None, resolution: Optional[str] = None,
                               temperature: Optional[float] = None) -> Optional[str]:
    """
    使用 Google Imagen API 生成图片
    
    流程：
    1. 使用文本模型（Gemini）润色用户的 prompt
    2. 使用润色后的 prompt 调用图片生成模型（Imagen）
    
    ⚠️ 重要：图片生成和文本生成逻辑已完全分离
    - 文本润色：使用 Gemini API（optimize_prompt）
    - 图片生成：使用 Imagen API（generate_images）
    
    参考文档: https://ai.google.dev/gemini-api/docs/image-generation
    """
    logger.info(f"🎨 开始生成图片 - 原始提示词: {prompt[:100]}...")
    logger.info(f"📐 参数: aspect_ratio={aspect_ratio}, resolution={resolution}, temperature={temperature}, 参考图数量={len(reference_images) if reference_images else 0}")
    
    if not GEMINI_IMAGE_AVAILABLE:
        logger.error("❌ google.genai 模块不可用，无法生成图片。请确保已安装: pip install google-genai")
        return None
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("❌ GOOGLE_API_KEY 未设置")
            return None
        
        # 验证并规范化 aspect_ratio（Imagen API 只支持特定值）
        # ⚠️ 重要：Google API 要求 aspect_ratio 必须明确传递，不能为 None
        valid_aspect_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
        if not aspect_ratio or aspect_ratio not in valid_aspect_ratios:
            logger.warning(f"⚠️ 无效的 aspect_ratio: {aspect_ratio}，将使用默认值 1:1")
            logger.info(f"💡 支持的 aspect_ratio 值: {valid_aspect_ratios}")
            aspect_ratio = "1:1"  # 确保始终有有效值
        
        # 根据是否有参考图选择不同的生成策略
        # ⚠️ 注意：generate_image_with_google 函数用于通用图片生成，不区分 banana/banana_pro
        # 实际调用时，会根据 mode 参数选择不同的生成器函数
        if reference_images and len(reference_images) > 0:
            # ========== 图生图模式：使用 Gemini 3 Pro Image ==========
            logger.info(f"📸 检测到 {len(reference_images)} 张参考图片，使用图生图模式")
            logger.info(f"🎯 使用模型: gemini-3-pro-image-preview")
            logger.info(f"💡 注意: Gemini 3 Pro 支持最多 14 张参考图")
            
            # 图生图模式：不优化提示词，保持原始提示词简洁
            # 原因：优化后的详细提示词可能会覆盖参考图的视觉信息，
            # 导致模型更关注文本描述而不是参考图的风格和内容
            logger.info("📝 图生图模式：使用原始提示词（不优化）以保持与参考图的关联性")
            original_prompt = prompt
            
            # 步骤1: 使用 Gemini 3 Pro Image 进行图生图
            logger.info("🎨 步骤1: 使用 Gemini 3 Pro Image 进行图生图...")
            logger.info(f"   使用的提示词: {original_prompt[:100]}...")
            logger.info(f"   温度参数: {temperature or '使用默认值'}")
            
            result = generate_with_gemini_image3(original_prompt, reference_images, aspect_ratio, temperature, resolution)
            
            if result:
                logger.info("✅ 图生图成功完成")
            else:
                logger.error("❌ 图生图返回 None")
            
            return result
        else:
            # ========== 文生图模式：使用 Gemini 3 Pro Image ==========
            logger.info("文生图模式: gemini-3-pro-image-preview")
            optimized_prompt = prompt
            result = generate_with_gemini_image3(optimized_prompt, None, aspect_ratio, temperature, resolution)
            
            if not result:
                logger.error("文生图返回 None")
            
            return result
        
    except Exception as e:
        logger.error(f"❌ 图片生成失败: {str(e)}")
        logger.error(f"📋 完整错误堆栈:\n{traceback.format_exc()}")
        return None


# ==================== API 端点 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "果捷后端服务",
        "status": "running",
        "version": "1.1.0"
    }

# 定义请求模型
class ProcessJsonRequest(BaseModel):
    message: str
    mode: str = "chat"
    history: Optional[List[dict]] = []  # 修复：明确指定 List[dict] 类型
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    temperature: Optional[float] = None  # 温度参数（0-1之间）
    optimized_prompt: Optional[str] = None  # 如果前端已经优化过提示词，直接传入
    skip_optimization: bool = False  # 是否跳过优化

@app.post("/api/process-json")
async def process_json(request: ProcessJsonRequest):
    """统一处理接口（JSON 格式）"""
    try:
        message = request.message
        mode = request.mode
        history = request.history or []
        aspect_ratio = request.aspect_ratio
        resolution = request.resolution
        temperature = request.temperature  # 温度参数
        optimized_prompt = request.optimized_prompt  # 如果前端已经优化过提示词，直接传入
        skip_optimization = request.skip_optimization  # 是否跳过优化
        
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 初始化模型版本标识
        model_version = None
        
        if mode == "banana":
            # ========== 使用 Gemini 2.5 Flash Image 模型（Banana 模式）==========
            model_version = "2.5"
            logger.info("=" * 80)
            logger.info("🎯 [Banana 模式] 使用模型: gemini-2.5-flash-image")
            logger.info(f"📝 原始提示词: {message[:100]}...")
            logger.info(f"📐 长宽比: {aspect_ratio or '默认'}")
            logger.info(f"📏 分辨率: 1K（固定，不支持 4K）")
            logger.info(f"🔧 生成器: gemini_2_5_flash_image.py")
            logger.info("=" * 80)
            
            # JSON 接口无参考图，使用文生图模式
            # 注意：gemini-2.5-flash-image 只支持 1K 分辨率，最多 3 张参考图
            image_data = generate_with_gemini_2_5_flash_image(
                prompt=message,
                reference_images=None,  # JSON 接口无参考图
                aspect_ratio=aspect_ratio
            )
            
        elif mode == "banana_pro":
            # ========== 使用 Gemini 3 Pro Image 模型（Banana Pro 模式）==========
            model_version = "3_pro"
            logger.info("=" * 80)
            logger.info("🎯 [Banana Pro 模式] 使用模型: gemini-3-pro-image-preview")
            logger.info(f"📝 原始提示词: {message[:100]}...")
            logger.info(f"📐 长宽比: {aspect_ratio or '默认'}")
            logger.info(f"📏 分辨率: {resolution or '默认（支持 4K）'}")
            logger.info(f"🌡️ 温度: {temperature or '默认'}")
            logger.info(f"🔧 生成器: gemini_3_pro_image.py")
            logger.info("=" * 80)
            
            # JSON 接口无参考图，使用文生图模式
            # 注意：gemini-3-pro-image-preview 支持 4K 分辨率，最多 14 张参考图
            image_data = generate_with_gemini_image3(
                prompt=message,
                reference_images=None,  # JSON 接口无参考图
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                temperature=temperature
            )
            
            # ========== 旧代码已屏蔽（使用其他模型）==========
            # # 使用 Imagen 3.0 Capability（统一文生图和图生图）
            # logger.info("🎯 使用模型: imagen-3.0-capability-001（统一文生图和图生图）")
            # logger.info(f"📝 原始提示词: {message[:100]}...")
            # image_data = generate_with_imagen_3_capability(
            #     prompt=message,
            #     reference_images=None,  # JSON 接口无参考图
            #     aspect_ratio=aspect_ratio,
            #     resolution=resolution,
            #     temperature=temperature
            # )
            
            # ========== 旧代码已屏蔽（等待测试通过后删除）==========
            # # Banana 模式：生成图片（JSON接口无参考图）
            # # 如果前端传入了已优化的提示词，直接使用；否则进行优化
            # # ========== 暂时注释掉提示词优化，直接使用原始提示词 ==========
            # # if optimized_prompt:
            # #     # 使用前端已经优化过的提示词
            # #     logger.info("🖼️ 文生图模式：使用前端已优化的提示词生成图片")
            # #     final_prompt = optimized_prompt
            # # elif skip_optimization:
            # #     # 跳过优化，直接使用原始提示词
            # #     logger.info("🖼️ 文生图模式：跳过优化，直接使用原始提示词生成图片")
            # #     final_prompt = message
            # # else:
            # #     # 进行提示词优化（保持向后兼容）
            # #     logger.info("🖼️ 文生图模式：先优化提示词，再生成图片")
            # #     final_prompt = optimize_prompt(message)
            # #     if not final_prompt or not final_prompt.strip():
            # #         logger.warning("⚠️ 优化返回空值，使用原始提示词")
            # #         final_prompt = message
            # 
            # # 直接使用原始提示词（跳过优化，测试模型自身的优化能力）
            # logger.info("⏭️ 文生图模式：跳过提示词优化，直接使用原始提示词（测试模型自身优化能力）")
            # final_prompt = message
            # 
            # # 使用优化后的提示词生成图片（不再重复优化）
            # logger.info(f"📝 最终使用的提示词: {final_prompt[:100]}...")
            # logger.info(f"🔥 温度参数: {temperature or '未设置（Imagen 4.0 不支持 temperature）'}")
            # 
            # # 使用 Imagen 4.0 Ultra 生成图片（文生图模式，无参考图片）
            # logger.info(f"🎯 使用模型: imagen-4.0-ultra-generate-001")
            # 
            # # 获取 google.genai.Client 实例（用于 Imagen 4.0）
            # client = _get_genai_client_for_imagen()
            # if not client:
            #     logger.error("❌ 无法创建 Google GenAI Client，图片生成失败")
            #     raise Exception("无法创建 Google GenAI Client")
            # 
            # # 将 resolution 参数映射到 image_size（Imagen 4.0 支持 1K 和 2K）
            # # 如果用户传入 4K，降级为 2K（Imagen 4.0 不支持 4K）
            # image_size = None
            # if resolution:
            #     resolution_upper = resolution.upper()
            #     if resolution_upper in ["1K", "2K"]:
            #         image_size = resolution_upper
            #     elif resolution_upper == "4K":
            #         logger.warning("⚠️ Imagen 4.0 不支持 4K 分辨率，将使用 2K")
            #         image_size = "2K"
            #     else:
            #         logger.warning(f"⚠️ 无效的 resolution: {resolution}，将使用默认值 2K")
            #         image_size = "2K"
            # else:
            #     image_size = "2K"  # 默认使用 2K
            # 
            # image_data = generate_with_imagen(client, final_prompt, aspect_ratio, image_size)
        
        # 处理图片生成结果（banana 和 banana_pro 模式共用）
        if mode == "banana" or mode == "banana_pro":
            if image_data:
                # ⚠️ 修改：处理新的返回格式（字典而不是字符串）
                # 生成器现在返回: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
                # 或者错误对象: {"error": True, "error_code": "...", ...}
                
                # ⚠️ 关键修复：先检查是否是错误对象，避免后续访问不存在的 image_data 字段
                if isinstance(image_data, dict) and image_data.get("error"):
                    error_info = image_data
                    error_code = error_info.get("error_code", "UNKNOWN_ERROR")
                    error_type = error_info.get("error_type", "Unknown")
                    error_message = error_info.get("error_message", "未知错误")
                    error_detail = error_info.get("error_detail", error_message)
                    
                    logger.error(f"[process-json] 图片生成失败 - 错误码: {error_code}, 错误类型: {error_type}")
                    logger.error(f"   错误描述: {error_detail}")
                    
                    return {
                        "response": f"⚠️ 图片生成失败。\n\n错误类型: {error_type}\n错误描述: {error_detail}\n\n请检查后端日志获取更多信息，或尝试修改提示词后重试。",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": error_code,
                        "error_type": error_type,
                        "error_message": error_message,
                        "error_detail": error_detail
                    }
                
                # 检查是否是安全策略拦截错误（旧格式，兼容性处理）
                if isinstance(image_data, str) and image_data.startswith("SAFETY_BLOCKED:"):
                    error_message = image_data.replace("SAFETY_BLOCKED:", "").strip()
                    logger.warning(f"[模型版本: {model_version}] 安全策略拦截: {error_message}")
                    return {
                        "response": f"❌ {error_message}\n\n💡 提示：请尝试修改提示词，避免涉及敏感内容、暴力、色情等违反安全策略的内容。",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "error_code": "SAFETY_BLOCKED",
                        "error_type": "SafetyBlocked",
                        "error_message": error_message,
                        "error_detail": "内容违反安全策略，无法生成图片",
                        "model_version": model_version
                    }
                
                # 处理新的字典格式
                if isinstance(image_data, dict):
                    base64_data = image_data.get("image_data")
                    # ⚠️ 关键修复：根据模型版本设置默认格式
                    # Gemini 2.5 通常返回 PNG，Gemini 3 Pro 通常返回 JPEG
                    default_format = "jpeg" if model_version == "3_pro" else "png"
                    image_format = image_data.get("image_format", default_format)
                    
                    if not base64_data:
                        logger.error(f"[模型版本: {model_version}] image_data 字典中缺少 image_data 字段")
                        return {
                            "response": f"⚠️ 图片生成失败：数据格式错误",
                            "success": False,
                            "image_data": None,
                            "image_url": None,
                            "model_version": model_version,
                            "error_code": "INVALID_IMAGE_DATA_FORMAT",
                            "error_type": "InvalidFormat",
                            "error_message": "image_data 字典中缺少 image_data 字段",
                            "error_detail": "数据格式错误：字典中缺少 image_data 字段或值为空"
                        }
                    
                    logger.info(f"[process-json] 准备返回图片数据: 格式={image_format}, Base64长度={len(base64_data)} 字符")
                    
                    # ⚠️ 重要：直接返回二进制图片流，避免 JSON 响应体过大导致超时
                    # 将 Base64 字符串解码为二进制数据
                    try:
                        import base64 as base64_module
                        image_bytes = base64_module.b64decode(base64_data)
                        logger.info(f"[process-json] Base64 解码成功，二进制大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
                        
                        # 根据格式设置 MIME 类型
                        mime_type = f"image/{image_format}"
                        
                        # ⚠️ 使用 io.BytesIO 包装二进制数据，然后通过 Response 返回图片文件流
                        # 这样更符合最佳实践，也便于将来扩展为流式传输
                        image_stream = io.BytesIO(image_bytes)
                        
                        # 设置 Content-Type 和 Content-Disposition 头
                        headers = {
                            "Content-Type": mime_type,
                            "Content-Disposition": f'inline; filename="generated_image.{image_format}"',
                            "X-Model-Version": model_version,  # 通过 Header 传递模型版本信息
                            "Content-Length": str(len(image_bytes)),  # 明确设置长度，避免 IncompleteRead
                        }
                        
                        logger.info(f"[process-json] 返回二进制图片流: {mime_type}, 大小: {len(image_bytes)} bytes")
                        # FastAPI 的 Response 可以直接接受 bytes 或 BytesIO，这里使用 BytesIO 更符合流式传输的最佳实践
                        return Response(
                            content=image_bytes,  # 也可以使用 image_stream.read()，但直接使用 bytes 更高效
                            media_type=mime_type,
                            headers=headers
                        )
                    except Exception as decode_error:
                        logger.error(f"[process-json] Base64 解码失败: {str(decode_error)}")
                        logger.error(f"   错误详情: {traceback.format_exc()}")
                        # 如果解码失败，回退到 JSON 格式返回错误
                        return {
                            "response": f"⚠️ 图片数据处理失败：Base64 解码错误",
                            "success": False,
                            "image_data": None,
                            "image_url": None,
                            "model_version": model_version,
                            "error_code": "BASE64_DECODE_FAILED",
                            "error_type": "DecodeFailed",
                            "error_message": f"Base64 解码失败: {str(decode_error)}",
                            "error_detail": f"无法将 Base64 字符串解码为二进制数据: {str(decode_error)}"
                        }
                else:
                    # 向后兼容：如果是旧格式（字符串），记录警告并尝试处理
                    logger.warning(f"[模型版本: {model_version}] image_data 是旧格式（字符串），期望字典格式")
                    if isinstance(image_data, str):
                        return {
                            "response": f"图片生成成功！(使用 Gemini {model_version})",
                            "success": True,
                            "image_data": image_data,  # 兼容旧格式
                            "image_url": None,
                            "model_version": model_version
                        }
                    else:
                        logger.error(f"[模型版本: {model_version}] image_data 类型错误: {type(image_data)}")
                        return {
                            "response": f"⚠️ 图片生成失败：数据格式错误",
                            "success": False,
                            "image_data": None,
                            "image_url": None,
                            "model_version": model_version,
                            "error_code": "INVALID_FORMAT",
                            "error_type": "InvalidFormat",
                            "error_message": f"image_data 类型错误: {type(image_data).__name__}",
                            "error_detail": f"期望字典或字符串格式，但收到 {type(image_data).__name__}"
                        }
            else:
                # 如果图片生成失败，返回错误信息
                logger.error(f"[process-json] 图片生成失败: 返回值为 None, 模型版本: {model_version}")
                return {
                    "response": f"⚠️ 图片生成失败。\n\n原始提示词: {message}\n\n提示词已自动润色优化，但仍无法生成图片。请检查后端日志获取详细错误信息，或尝试修改提示词后重试。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version,
                    "error_code": "IMAGE_GENERATION_FAILED",
                    "error_type": "GenerationFailed",
                    "error_message": "图片生成失败，返回值为 None",
                    "error_detail": f"generate_with_gemini_image 返回了 None，可能原因：模型调用失败、超时、安全策略拦截或 API 配置问题（模型版本: {model_version}）"
                }
        else:
            # 聊天模式
            response_text = chat(message, history)
            return {
                "response": response_text,
                "success": True
            }
    except Exception as e:
        error_name = type(e).__name__
        error_message = str(e)
        logger.error(f"[process-json] 接口异常: {error_name} - {error_message}")
        
        # 检查异常对象是否包含错误信息（从生成器传递）
        error_code = "PROCESS_JSON_ERROR"
        error_detail = traceback.format_exc()
        
        if hasattr(e, 'error_info'):
            error_info = e.error_info
            error_code = error_info.get("error_code", error_code)
            error_detail = error_info.get("error_detail", error_detail)
        
        return {
            "success": False,
            "response": f"后端报错: {error_message}\n\n异常类型: {error_name}\n\n请查看后端日志获取详细错误信息。",
            "error_code": error_code,
            "error_type": error_name,
            "error_message": error_message,
            "error_detail": error_detail,
            "image_data": None,
            "image_url": None
        }

@app.post("/api/process-json3")
async def process_json3(request: ProcessJsonRequest):
    """Gemini 3 Pro Image 专用处理接口（JSON 格式）"""
    try:
        message = request.message
        mode = request.mode or "banana_pro"  # 默认使用 banana_pro 模式
        history = request.history or []
        aspect_ratio = request.aspect_ratio
        resolution = request.resolution
        temperature = request.temperature  # 温度参数
        optimized_prompt = request.optimized_prompt  # 如果前端已经优化过提示词，直接传入
        skip_optimization = request.skip_optimization  # 是否跳过优化
        
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 强制使用 Gemini 3 Pro Image 模型
        model_version = "3_pro"
        logger.info(f"[process-json3] 使用模型: gemini-3-pro-image-preview, 提示词: {message[:100]}...")
        
        try:
            image_data = generate_with_gemini_image3(
                prompt=message,
                reference_images=None,  # JSON 接口无参考图
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                temperature=temperature
            )
            
            if image_data:
                if isinstance(image_data, dict):
                    # 检查是否是错误信息
                    if image_data.get("error"):
                        logger.error(f"[process-json3] 生成器返回错误: {image_data.get('error_code', 'UNKNOWN')}")
                    else:
                        logger.info(f"[process-json3] 调用完成, 返回格式: 字典, 包含字段: {list(image_data.keys())}")
                elif isinstance(image_data, str):
                    if image_data.startswith("SAFETY_BLOCKED:"):
                        logger.warning("[process-json3] 检测到安全策略拦截标记")
                    else:
                        logger.info(f"[process-json3] 调用完成, 返回格式: 字符串")
                else:
                    logger.warning(f"[process-json3] 未知返回类型: {type(image_data).__name__}")
        except Exception as gen_error:
            logger.error(f"[process-json3] 调用异常: {type(gen_error).__name__} - {str(gen_error)}")
            image_data = None
        
        # 处理图片生成结果（banana_pro 模式：使用字典格式）
        if image_data:
            # ⚠️ 修改：处理新的返回格式（字典而不是字符串）
            # 生成器现在返回: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
            
            # 检查是否是错误信息（生成器返回的错误字典）
            if isinstance(image_data, dict) and image_data.get("error"):
                error_info = image_data
                error_code = error_info.get("error_code", "UNKNOWN_ERROR")
                error_type = error_info.get("error_type", "Unknown")
                error_message = error_info.get("error_message", "未知错误")
                error_detail = error_info.get("error_detail", error_message)
                
                logger.error(f"[process-json3] 图片生成失败 - 错误码: {error_code}, 错误类型: {error_type}")
                logger.error(f"   错误描述: {error_detail}")
                
                return {
                    "response": f"⚠️ 图片生成失败。\n\n错误类型: {error_type}\n错误描述: {error_detail}\n\n请检查后端日志获取更多信息，或尝试修改提示词后重试。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version,
                    "error_code": error_code,
                    "error_type": error_type,
                    "error_message": error_message,
                    "error_detail": error_detail
                }
            
            # 检查是否是安全策略拦截错误（旧格式，兼容性处理）
            if isinstance(image_data, str) and image_data.startswith("SAFETY_BLOCKED:"):
                error_message = image_data.replace("SAFETY_BLOCKED:", "").strip()
                logger.warning(f"[模型版本: {model_version}] 安全策略拦截: {error_message}")
                return {
                    "response": f"❌ {error_message}\n\n💡 提示：请尝试修改提示词，避免涉及敏感内容、暴力、色情等违反安全策略的内容。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "error_code": "SAFETY_BLOCKED",
                    "error_type": "SafetyBlocked",
                    "error_message": error_message,
                    "error_detail": "内容违反安全策略，无法生成图片",
                    "model_version": model_version
                }
            
            # 处理新的字典格式（Gemini 3 Pro 返回格式）
            if isinstance(image_data, dict):
                # ⚠️ 关键修复：先检查是否是错误字典
                if image_data.get("error"):
                    # 这是错误字典，已经在上面处理过了，这里不应该到达
                    error_code = image_data.get("error_code", "UNKNOWN_ERROR")
                    error_type = image_data.get("error_type", "Unknown")
                    error_message = image_data.get("error_message", "未知错误")
                    error_detail = image_data.get("error_detail", error_message)
                    
                    logger.error(f"[process-json3] 生成器返回错误: {error_code}, 类型: {error_type}")
                    logger.error(f"   错误描述: {error_detail}")
                    
                    return {
                        "response": f"⚠️ 图片生成失败。\n\n错误类型: {error_type}\n错误描述: {error_detail}\n\n请检查后端日志获取更多信息，或尝试修改提示词后重试。",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": error_code,
                        "error_type": error_type,
                        "error_message": error_message,
                        "error_detail": error_detail
                    }
                
                # 正常返回字典，提取图片数据
                base64_data = image_data.get("image_data")
                # ⚠️ 关键修复：process-json3 是 Gemini 3 Pro 专用接口，默认格式应该是 JPEG
                image_format = image_data.get("image_format", "jpeg")
                
                if not base64_data:
                    logger.error(f"[process-json3] image_data 字典中缺少 image_data 字段或值为空")
                    logger.error(f"   字典键: {list(image_data.keys()) if isinstance(image_data, dict) else 'N/A'}")
                    logger.error(f"   字典内容: {image_data}")
                    
                    return {
                        "response": f"⚠️ 图片生成失败：数据格式错误（字典中缺少 image_data 字段或值为空）",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": "INVALID_IMAGE_DATA_FORMAT",
                        "error_type": "InvalidFormat",
                        "error_message": "字典中缺少 image_data 字段或值为空",
                        "error_detail": f"返回的字典键: {list(image_data.keys()) if isinstance(image_data, dict) else 'N/A'}"
                    }
                
                logger.info(f"[process-json3] 准备返回图片数据: 格式={image_format}, Base64长度={len(base64_data)} 字符")
                
                # ⚠️ 严格要求：直接返回原始文件流（二进制），禁止返回字典或 JSON
                # 将 Base64 字符串解码为二进制数据
                try:
                    import base64 as base64_module
                    image_bytes = base64_module.b64decode(base64_data)
                    logger.info(f"[process-json3] Base64 解码成功，二进制大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
                    
                    # 根据格式设置 MIME 类型
                    mime_type = f"image/{image_format}"
                    
                    # ⚠️ 严格要求：使用 Response 直接发送原始二进制，不用 FileResponse（避免 BytesIO 指针问题）
                    # 这样传输时带宽占用最小，绝对不会因为 JSON 解析过大而断连
                    logger.info(f"[process-json3] 使用 Response 直接返回原始二进制流（非 JSON）: {mime_type}, 大小: {len(image_bytes)} bytes")
                    # 使用 Response 返回原始二进制文件，禁止返回 JSON
                    return Response(
                        content=image_bytes,  # 直接传递二进制 bytes，避免 BytesIO 指针问题
                        media_type=mime_type,
                        headers={
                            "X-Model-Version": model_version,  # 通过 Header 传递模型版本信息
                            "Content-Length": str(len(image_bytes)),  # 明确设置长度，避免 IncompleteRead
                            "Content-Disposition": f'inline; filename="generated_image.{image_format}"',
                            "Access-Control-Allow-Origin": "*",  # 明确允许跨域
                            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                            "Access-Control-Allow-Headers": "Content-Type, Authorization"
                        }
                    )
                except Exception as decode_error:
                    logger.error(f"[process-json3] Base64 解码失败: {str(decode_error)}")
                    logger.error(f"   错误详情: {traceback.format_exc()}")
                    # 如果解码失败，回退到 JSON 格式返回错误
                    return {
                        "response": f"⚠️ 图片数据处理失败：Base64 解码错误",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": "BASE64_DECODE_FAILED",
                        "error_type": "DecodeFailed",
                        "error_message": f"Base64 解码失败: {str(decode_error)}",
                        "error_detail": f"无法将 Base64 字符串解码为二进制数据: {str(decode_error)}"
                    }
            else:
                # 兼容性处理：如果返回的是字符串（旧格式），记录警告并尝试处理
                logger.error(f"[process-json3] 收到非字典格式的返回值: {type(image_data).__name__}")
                
                # 尝试作为字符串处理（向后兼容）
                return {
                    "response": f"⚠️ 图片生成返回格式异常（期望字典格式，但收到 {type(image_data).__name__}）。请检查后端日志。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version,
                    "error_code": "UNEXPECTED_FORMAT",
                    "received_type": type(image_data).__name__
                }
        else:
            # 如果图片生成失败，返回错误信息
            logger.error(f"[process-json3] 图片生成失败: 返回值={image_data}, 类型={type(image_data).__name__}")
            
            return {
                "response": f"⚠️ 图片生成失败。\n\n原始提示词: {message}\n\n可能的原因：\n1. 模型调用失败或超时\n2. 安全策略拦截\n3. API 配置问题\n\n请检查后端日志获取详细错误信息，或尝试修改提示词后重试。",
                "success": False,
                "image_data": None,
                "image_url": None,
                "model_version": model_version,
                "error_code": "IMAGE_GENERATION_FAILED",
                "error_type": "GenerationFailed",
                "error_message": "图片生成失败，返回值为 None",
                "error_detail": f"generate_with_gemini_image3 返回了 None，可能原因：模型调用失败、超时、安全策略拦截或 API 配置问题"
            }
    except Exception as e:
        error_name = type(e).__name__
        error_message = str(e)
        logger.error(f"[process-json3] 接口异常: {error_name} - {error_message}")
        
        # 检查异常对象是否包含错误信息（从生成器传递）
        error_code = "PROCESS_JSON3_ERROR"
        error_detail = traceback.format_exc()
        
        if hasattr(e, 'error_info'):
            error_info = e.error_info
            error_code = error_info.get("error_code", error_code)
            error_detail = error_info.get("error_detail", error_detail)
        
        return {
            "success": False,
            "response": f"后端报错: {error_message}\n\n异常类型: {error_name}\n\n请查看后端日志获取详细错误信息。",
            "error_code": error_code,
            "error_type": error_name,
            "error_message": error_message,
            "error_detail": error_detail,
            "image_data": None,
            "image_url": None,
            "model_version": "3_pro"
        }

@app.post("/api/process")
async def process(request: Request):
    """统一处理接口（支持文件上传）"""
    request_id = f"{int(time.time() * 1000)}"
    
    # 手动解析 FormData（这样可以正确处理单个或多个文件）
    form_data = await request.form()
    
    # 提取文本字段
    message = form_data.get("message", "")
    mode = form_data.get("mode", "chat")
    history = form_data.get("history")
    aspect_ratio = form_data.get("aspect_ratio")
    resolution = form_data.get("resolution")
    temperature_str = form_data.get("temperature")
    temperature = float(temperature_str) if temperature_str else None
    skip_optimization = form_data.get("skip_optimization")
    
    logger.info(f"[{request_id}] 📥 收到请求 /api/process - mode={mode}, message={message[:50]}..., aspect_ratio={aspect_ratio}, resolution={resolution}")
    
    # 手动解析 FormData 中的 reference_images 文件
    # FastAPI 的 FormData 对于同名字段，需要使用 getlist() 获取所有值
    reference_image_list = []
    try:
        # 使用 getlist() 获取所有同名字段的值（支持多个文件上传）
        reference_images_fields = form_data.getlist('reference_images')
        
        if reference_images_fields:
            logger.info(f"[{request_id}] 📎 从 FormData 中提取到 {len(reference_images_fields)} 个 reference_images 字段")
            # 过滤出所有 UploadFile 类型的对象（可能是 starlette.datastructures.UploadFile 或 fastapi.UploadFile）
            for idx, item in enumerate(reference_images_fields):
                # 检查是否有 UploadFile 的特征（有 filename 和 read 方法）
                if hasattr(item, 'filename') and hasattr(item, 'read'):
                    reference_image_list.append(item)
                    logger.info(f"[{request_id}]   参考图 {idx+1}: filename={item.filename if hasattr(item, 'filename') else 'N/A'}, content_type={item.content_type if hasattr(item, 'content_type') else 'N/A'}, 类型={type(item).__name__}")
                else:
                    logger.warning(f"[{request_id}]   字段 {idx+1} 不是有效的 UploadFile 类型: {type(item)}")
            
            if not reference_image_list:
                logger.warning(f"[{request_id}] ⚠️ 没有找到有效的参考图文件")
            else:
                logger.info(f"[{request_id}] ✅ 成功提取 {len(reference_image_list)} 张参考图")
        else:
            logger.info(f"[{request_id}] 📎 FormData 中没有 reference_images 字段（未上传）")
    except Exception as e:
        logger.error(f"[{request_id}] ❌ 解析 FormData 中的 reference_images 失败: {str(e)}")
        logger.error(f"[{request_id}]   错误详情: {traceback.format_exc()}")
    
    logger.info(f"[{request_id}] ⏭️  skip_optimization: {skip_optimization}")
    
    # 解析 skip_optimization 参数（FormData 传入的是字符串）
    should_skip_optimization = skip_optimization and skip_optimization.lower() == 'true'
    
    try:
        # 解析历史记录
        history_list = []
        if history:
            try:
                import json
                history_list = json.loads(history)
            except:
                pass
        
        # 处理参考图片（现在 reference_image_list 已经是列表）
        processed_reference_images = []
        if reference_image_list:
            logger.info(f"[{request_id}] 📸 开始处理参考图片，收到 {len(reference_image_list)} 张")
            for idx, img_file in enumerate(reference_image_list):
                try:
                    logger.info(f"[{request_id}]   处理参考图片 {idx+1}/{len(reference_image_list)}: filename={img_file.filename}")
                    image_bytes = await img_file.read()
                    logger.info(f"[{request_id}]   参考图片 {idx+1} 文件大小: {len(image_bytes)} bytes")
                    image = Image.open(io.BytesIO(image_bytes))
                    processed_reference_images.append(image)
                    logger.info(f"[{request_id}] ✅ 参考图片 {idx+1} 已处理: {img_file.filename}, 尺寸: {image.size}, 模式: {image.mode}")
                except Exception as e:
                    logger.error(f"[{request_id}] ❌ 处理参考图片 {idx+1} 失败: {str(e)}")
                    logger.error(f"[{request_id}]   错误详情: {traceback.format_exc()}")
        else:
            logger.info(f"[{request_id}] ℹ️  未收到参考图片（reference_images 为空）")
        
        # 更新 reference_image_list 为处理后的图片列表
        reference_image_list = processed_reference_images
        
        # 初始化模型版本标识
        model_version = None
        
        if mode == "banana":
            # ========== Banana 模式：使用 Gemini 2.5 Flash Image 模型 ==========
            model_version = "2.5"
            logger.info(f"[{request_id}] " + "=" * 70)
            logger.info(f"[{request_id}] 🎯 [Banana 模式] 使用模型: gemini-2.5-flash-image")
            logger.info(f"[{request_id}] 📝 原始提示词: {message[:100]}...")
            logger.info(f"[{request_id}] 📐 长宽比: {aspect_ratio or '默认'}")
            logger.info(f"[{request_id}] 🔧 生成器: gemini_2_5_flash_image.py")
            if reference_image_list:
                logger.info(f"[{request_id}] 📸 参考图片数量: {len(reference_image_list)}")
            else:
                logger.info(f"[{request_id}] 📸 无参考图片（文生图模式）")
            logger.info(f"[{request_id}] " + "=" * 70)
            
            # Gemini 2.5 Flash Image 支持参考图片（图生图）和长宽比设置
            # 注意：该模型只支持 1K 分辨率（固定1024像素），不支持 4K
            # 如需 4K 分辨率，请使用 banana_pro 模式
            image_data = generate_with_gemini_2_5_flash_image(
                prompt=message,
                reference_images=reference_image_list if reference_image_list else None,
                aspect_ratio=aspect_ratio
            )
        
        elif mode == "banana_pro":
            # ========== Banana Pro 模式：使用 Gemini 3 Pro Image 模型 ==========
            model_version = "3_pro"
            logger.info(f"[{request_id}] " + "=" * 70)
            logger.info(f"[{request_id}] 🎯 [Banana Pro 模式] 使用模型: gemini-3-pro-image-preview")
            logger.info(f"[{request_id}] 📝 原始提示词: {message[:100]}...")
            logger.info(f"[{request_id}] 📐 长宽比: {aspect_ratio or '默认'}")
            logger.info(f"[{request_id}] 📏 分辨率: {resolution or '默认（支持 4K）'}")
            logger.info(f"[{request_id}] 🌡️ 温度: {temperature or '默认'}")
            logger.info(f"[{request_id}] 📸 参考图片数量: {len(reference_image_list) if reference_image_list else 0}")
            logger.info(f"[{request_id}] 🔧 生成器: gemini_3_pro_image.py")
            logger.info(f"[{request_id}] 💡 注意: Gemini 3 Pro 支持最多 14 张参考图，支持 4K 分辨率")
            logger.info(f"[{request_id}] " + "=" * 70)
            
            # 处理提示词优化逻辑
            if should_skip_optimization:
                # 跳过优化，直接使用提示词
                final_prompt = message
            else:
                # 向后兼容：如果没有跳过优化（旧版本前端可能不传此参数）
                # 图生图：直接使用原始提示词（不优化，因为参考图是主要依据）
                # 文生图：调用 generate_image_with_google 进行优化
                if reference_image_list:
                    final_prompt = message
                else:
                    # 文生图：使用 Gemini 3 Pro Image 直接生成（不再调用 generate_image_with_google）
                    final_prompt = message
            
            # ========== 使用 Gemini 3 Pro Image 模型（Banana Pro 模式）==========
            image_data = generate_with_gemini_image3(
                prompt=final_prompt,
                reference_images=reference_image_list if reference_image_list else None,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                temperature=temperature
            )
            
            # ========== 旧代码已屏蔽（使用其他模型）==========
            # # 文生图使用 Imagen 3.0 Generate，图生图使用 Gemini 3 Pro Image
            # if reference_image_list and len(reference_image_list) > 0:
            #     # 图生图模式：使用 Gemini 3 Pro Image
            #     logger.info(f"[{request_id}] 📸 图生图模式：使用 gemini-3-pro-image-preview")
            #     logger.info(f"[{request_id}] 📝 原始提示词: {final_prompt[:100]}...")
            #     logger.info(f"[{request_id}] 📸 参考图片数量: {len(reference_image_list)}")
            #     image_data = generate_with_gemini_image(
            #         prompt=final_prompt,
            #         reference_images=reference_image_list,
            #         aspect_ratio=aspect_ratio,
            #         temperature=temperature,
            #         resolution=resolution
            #     )
            # else:
            #     # 文生图模式：使用 Imagen 3.0 Generate
            #     logger.info(f"[{request_id}] 🎯 使用模型: imagen-3.0-generate-001（文生图）")
            #     logger.info(f"[{request_id}] 📝 原始提示词: {final_prompt[:100]}...")
            #     image_data = generate_with_imagen_3_capability(
            #         prompt=final_prompt,
            #         reference_images=None,  # 文生图无参考图
            #         aspect_ratio=aspect_ratio,
            #         resolution=resolution,
            #         temperature=temperature
            #     )
            
            # ========== 旧代码已屏蔽（等待测试通过后删除）==========
            # if reference_image_list and len(reference_image_list) > 0:
            #     # 图生图模式：使用 Gemini 3 Pro Image
            #     logger.info(f"[{request_id}] 📸 图生图模式：使用已优化的提示词 + {len(reference_image_list)} 张参考图生成图片")
            #     logger.info(f"[{request_id}]   使用的提示词: {final_prompt[:100]}...")
            #     logger.info(f"[{request_id}]   参考图信息:")
            #     for idx, img in enumerate(reference_image_list):
            #         logger.info(f"[{request_id}]     参考图 {idx+1}: 尺寸={img.size}, 模式={img.mode}")
            #     image_data = generate_with_gemini_image(final_prompt, reference_image_list, aspect_ratio, temperature, resolution)
            # else:
            #     # 文生图模式：使用 Gemini 3 Pro Image
            #     logger.info(f"[{request_id}] 📝 文生图模式：使用已优化的提示词生成图片（无参考图）")
            #     logger.info(f"[{request_id}] 🎯 使用模型: gemini-3-pro-image-preview")
            #     logger.info(f"[{request_id}]   使用的提示词: {final_prompt[:100]}...")
            #     logger.info(f"[{request_id}]   温度参数: {temperature or '使用默认值'}")
            #     image_data = generate_with_gemini_image(final_prompt, None, aspect_ratio, temperature, resolution)
        
        # 处理图片生成结果（banana 和 banana_pro 模式共用）
        if mode == "banana" or mode == "banana_pro":
            if image_data:
                # ⚠️ 修改：处理新的返回格式（字典而不是字符串）
                # 生成器现在返回: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
                # 或者错误对象: {"error": True, "error_code": "...", ...}
                
                # ⚠️ 关键修复：先检查是否是错误对象，避免后续访问不存在的 image_data 字段
                if isinstance(image_data, dict) and image_data.get("error"):
                    error_info = image_data
                    error_code = error_info.get("error_code", "UNKNOWN_ERROR")
                    error_type = error_info.get("error_type", "Unknown")
                    error_message = error_info.get("error_message", "未知错误")
                    error_detail = error_info.get("error_detail", error_message)
                    
                    logger.error(f"[{request_id}] ❌ [模型版本: {model_version}] 图片生成失败: {error_type} - {error_message}")
                    logger.error(f"[{request_id}]   错误代码: {error_code}")
                    logger.error(f"[{request_id}]   错误详情: {error_detail}")
                    
                    return {
                        "response": f"❌ 图片生成失败：{error_message}\n\n💡 详情：{error_detail}",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "error_code": error_code,
                        "error_type": error_type,
                        "error_message": error_message,
                        "error_detail": error_detail,
                        "model_version": model_version
                    }
                
                # 检查是否是安全策略拦截错误（旧格式，兼容性处理）
                if isinstance(image_data, str) and image_data.startswith("SAFETY_BLOCKED:"):
                    error_message = image_data.replace("SAFETY_BLOCKED:", "").strip()
                    logger.warning(f"[{request_id}] ⚠️ [模型版本: {model_version}] 安全策略拦截: {error_message}")
                    return {
                        "response": f"❌ {error_message}\n\n💡 提示：请尝试修改提示词，避免涉及敏感内容、暴力、色情等违反安全策略的内容。",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "error_code": "SAFETY_BLOCKED",
                        "model_version": model_version
                    }
                
                # 处理新的字典格式
                if isinstance(image_data, dict):
                    base64_data = image_data.get("image_data")
                    # ⚠️ 关键修复：根据模型版本设置默认格式
                    # Gemini 2.5 通常返回 PNG，Gemini 3 Pro 通常返回 JPEG
                    default_format = "jpeg" if model_version == "3_pro" else "png"
                    image_format = image_data.get("image_format", default_format)
                    
                    if not base64_data:
                        logger.error(f"[{request_id}] ❌ [模型版本: {model_version}] image_data 字典中缺少 image_data 字段")
                        return {
                            "response": f"⚠️ 图片生成失败：数据格式错误",
                            "success": False,
                            "image_data": None,
                            "image_url": None,
                            "model_version": model_version
                        }
                    
                    logger.info(f"[{request_id}] 📦 [模型版本: {model_version}] 准备返回图片数据:")
                    logger.info(f"[{request_id}]   格式: {image_format}")
                    logger.info(f"[{request_id}]   Base64 数据长度: {len(base64_data)} 字符")
                    logger.info(f"[{request_id}]   Base64 前50字符: {base64_data[:50]}...")
                    
                    # 返回原始 Base64 数据和格式信息，让前端自己构建 Data URL
                    return {
                        "response": f"图片生成成功！(使用 Gemini {model_version})",
                        "success": True,
                        "image_data": base64_data,  # Base64 字符串（不带 data: 前缀）
                        "image_format": image_format,  # 图片格式（png 或 jpeg）
                        "image_url": None,
                        "model_version": model_version
                    }
                else:
                    # 向后兼容：如果是旧格式（字符串），记录警告并尝试处理
                    logger.warning(f"[{request_id}] ⚠️ [模型版本: {model_version}] image_data 是旧格式（字符串），期望字典格式")
                    if isinstance(image_data, str):
                        return {
                            "response": f"图片生成成功！(使用 Gemini {model_version})",
                            "success": True,
                            "image_data": image_data,  # 兼容旧格式
                            "image_url": None,
                            "model_version": model_version
                        }
                    else:
                        logger.error(f"[{request_id}] ❌ [模型版本: {model_version}] image_data 类型错误: {type(image_data)}")
                        return {
                            "response": f"⚠️ 图片生成失败：数据格式错误",
                            "success": False,
                            "image_data": None,
                            "image_url": None,
                            "model_version": model_version
                        }
            else:
                # 如果图片生成失败，返回错误信息
                error_prompt = message if mode == "banana" else (final_prompt if 'final_prompt' in locals() else message)
                return {
                    "response": f"⚠️ 图片生成失败。\n\n原始提示词: {error_prompt}\n\n提示词已自动润色优化，但仍无法生成图片。请检查后端日志获取详细错误信息，或尝试修改提示词后重试。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version
                }
        else:
            # 聊天模式
            response_text = chat(message, history_list)
            return {
                "response": response_text,
                "success": True
            }
    except Exception as e:
        error_msg = f"处理接口错误(Form): {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "PROCESS_ERROR",
            "error_detail": traceback.format_exc(),
            "image_data": None,
            "image_url": None
        }

@app.post("/api/process3")
async def process3(request: Request):
    """Gemini 3 Pro Image 专用处理接口（支持文件上传）"""
    request_id = f"{int(time.time() * 1000)}"
    
    # 手动解析 FormData（这样可以正确处理单个或多个文件）
    form_data = await request.form()
    
    # 提取文本字段
    message = form_data.get("message", "")
    mode = "banana_pro"  # 强制使用 banana_pro 模式
    history = form_data.get("history")
    aspect_ratio = form_data.get("aspect_ratio")
    resolution = form_data.get("resolution")
    temperature_str = form_data.get("temperature")
    temperature = float(temperature_str) if temperature_str else None
    skip_optimization = form_data.get("skip_optimization")
    
    logger.info(f"[{request_id}] 📥 收到请求 /api/process3 - mode={mode}, message={message[:50]}..., aspect_ratio={aspect_ratio}, resolution={resolution}")
    
    # 手动解析 FormData 中的 reference_images 文件
    reference_image_list = []
    try:
        reference_images_fields = form_data.getlist('reference_images')
        
        if reference_images_fields:
            logger.info(f"[{request_id}] 📎 从 FormData 中提取到 {len(reference_images_fields)} 个 reference_images 字段")
            for idx, item in enumerate(reference_images_fields):
                if hasattr(item, 'filename') and hasattr(item, 'read'):
                    reference_image_list.append(item)
                    logger.info(f"[{request_id}]   参考图 {idx+1}: filename={item.filename if hasattr(item, 'filename') else 'N/A'}, content_type={item.content_type if hasattr(item, 'content_type') else 'N/A'}")
                else:
                    logger.warning(f"[{request_id}]   字段 {idx+1} 不是有效的 UploadFile 类型: {type(item)}")
            
            if not reference_image_list:
                logger.warning(f"[{request_id}] ⚠️ 没有找到有效的参考图文件")
            else:
                logger.info(f"[{request_id}] ✅ 成功提取 {len(reference_image_list)} 张参考图")
        else:
            logger.info(f"[{request_id}] 📎 FormData 中没有 reference_images 字段（未上传）")
    except Exception as e:
        logger.error(f"[{request_id}] ❌ 解析 FormData 中的 reference_images 失败: {str(e)}")
        logger.error(f"[{request_id}]   错误详情: {traceback.format_exc()}")
    
    logger.info(f"[{request_id}] ⏭️  skip_optimization: {skip_optimization}")
    
    # 解析 skip_optimization 参数
    should_skip_optimization = skip_optimization and skip_optimization.lower() == 'true'
    
    try:
        # 解析历史记录
        history_list = []
        if history:
            try:
                import json
                history_list = json.loads(history)
            except:
                pass
        
        # 处理参考图片
        processed_reference_images = []
        if reference_image_list:
            logger.info(f"[{request_id}] 📸 开始处理参考图片，收到 {len(reference_image_list)} 张")
            for idx, img_file in enumerate(reference_image_list):
                try:
                    logger.info(f"[{request_id}]   处理参考图片 {idx+1}/{len(reference_image_list)}: filename={img_file.filename}")
                    image_bytes = await img_file.read()
                    logger.info(f"[{request_id}]   参考图片 {idx+1} 文件大小: {len(image_bytes)} bytes")
                    image = Image.open(io.BytesIO(image_bytes))
                    processed_reference_images.append(image)
                    logger.info(f"[{request_id}] ✅ 参考图片 {idx+1} 已处理: {img_file.filename}, 尺寸: {image.size}, 模式: {image.mode}")
                except Exception as e:
                    logger.error(f"[{request_id}] ❌ 处理参考图片 {idx+1} 失败: {str(e)}")
                    logger.error(f"[{request_id}]   错误详情: {traceback.format_exc()}")
        else:
            logger.info(f"[{request_id}] ℹ️  未收到参考图片（reference_images 为空）")
        
        # 更新 reference_image_list 为处理后的图片列表
        reference_image_list = processed_reference_images
        
        # 强制使用 Gemini 3 Pro Image 模型
        model_version = "3_pro"
        logger.info(f"[{request_id}] " + "=" * 70)
        logger.info(f"[{request_id}] 🎯 [process3 接口] 使用模型: gemini-3-pro-image-preview")
        logger.info(f"[{request_id}] 📝 原始提示词: {message[:100]}...")
        logger.info(f"[{request_id}] 📐 长宽比: {aspect_ratio or '默认'}")
        logger.info(f"[{request_id}] 📏 分辨率: {resolution or '默认（支持 4K）'}")
        logger.info(f"[{request_id}] 🌡️ 温度: {temperature or '默认'}")
        logger.info(f"[{request_id}] 📸 参考图片数量: {len(reference_image_list) if reference_image_list else 0}")
        logger.info(f"[{request_id}] 🔧 生成器: gemini_3_pro_image.py")
        logger.info(f"[{request_id}] 💡 注意: Gemini 3 Pro 支持最多 14 张参考图，支持 4K 分辨率")
        logger.info(f"[{request_id}] " + "=" * 70)
        
        # 处理提示词优化逻辑
        if should_skip_optimization:
            final_prompt = message
        else:
            if reference_image_list:
                final_prompt = message
            else:
                final_prompt = message
        
        # 使用 Gemini 3 Pro Image 模型
        image_data = generate_with_gemini_image3(
            prompt=final_prompt,
            reference_images=reference_image_list if reference_image_list else None,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature
        )
        
        # 处理图片生成结果（banana_pro 模式：使用字典格式）
        if image_data:
            # ⚠️ 修改：处理新的返回格式（字典而不是字符串）
            # 生成器现在返回: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
            # 或者错误字典: {"error": True, "error_code": "...", "error_message": "..."}
            
            # ⚠️ 重要：先检查是否是错误字典（包含 error 字段）
            if isinstance(image_data, dict) and image_data.get("error"):
                error_info = image_data
                error_code = error_info.get("error_code", "UNKNOWN_ERROR")
                error_type = error_info.get("error_type", "Unknown")
                error_message = error_info.get("error_message", "未知错误")
                error_detail = error_info.get("error_detail", error_message)
                
                logger.error(f"[{request_id}] [process3] 图片生成失败 - 错误码: {error_code}, 错误类型: {error_type}")
                logger.error(f"[{request_id}]    错误描述: {error_detail}")
                
                return {
                    "response": f"⚠️ 图片生成失败。\n\n错误类型: {error_type}\n错误描述: {error_detail}\n\n请检查后端日志获取更多信息，或尝试修改提示词后重试。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version,
                    "error_code": error_code,
                    "error_type": error_type,
                    "error_message": error_message,
                    "error_detail": error_detail
                }
            
            # 检查是否是安全策略拦截错误（旧格式，兼容性处理）
            if isinstance(image_data, str) and image_data.startswith("SAFETY_BLOCKED:"):
                error_message = image_data.replace("SAFETY_BLOCKED:", "").strip()
                logger.warning(f"[{request_id}] ⚠️ [模型版本: {model_version}] 安全策略拦截: {error_message}")
                return {
                    "response": f"❌ {error_message}\n\n💡 提示：请尝试修改提示词，避免涉及敏感内容、暴力、色情等违反安全策略的内容。",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "error_code": "SAFETY_BLOCKED",
                    "model_version": model_version
                }
            
            # 处理新的字典格式（Gemini 3 Pro 返回格式）
            if isinstance(image_data, dict):
                base64_data = image_data.get("image_data")
                # ⚠️ 关键修复：process3 是 Gemini 3 Pro 专用接口，默认格式应该是 JPEG
                image_format = image_data.get("image_format", "jpeg")
                
                if not base64_data:
                    logger.error(f"[{request_id}] ❌ [模型版本: {model_version}] image_data 字典中缺少 image_data 字段")
                    logger.error(f"[{request_id}]    字典键: {list(image_data.keys()) if isinstance(image_data, dict) else 'N/A'}")
                    logger.error(f"[{request_id}]    字典内容: {image_data}")
                    return {
                        "response": f"⚠️ 图片生成失败：数据格式错误（字典中缺少 image_data 字段或值为空）",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": "INVALID_IMAGE_DATA_FORMAT",
                        "error_type": "InvalidFormat",
                        "error_message": "字典中缺少 image_data 字段或值为空",
                        "error_detail": f"返回的字典键: {list(image_data.keys()) if isinstance(image_data, dict) else 'N/A'}"
                    }
                
                logger.info(f"[{request_id}] 📦 [模型版本: {model_version}] 准备返回图片数据:")
                logger.info(f"[{request_id}]   格式: {image_format}")
                logger.info(f"[{request_id}]   Base64 数据长度: {len(base64_data)} 字符")
                logger.info(f"[{request_id}]   Base64 前50字符: {base64_data[:50]}...")
                
                # ⚠️ Gemini 3 Pro 专用逻辑：返回纯二进制流（不是 JSON）
                # 这样前端可以用 responseType: 'blob' 直接接收图片数据
                try:
                    import base64
                    image_bytes = base64.b64decode(base64_data)
                    
                    # 返回纯二进制流，前端会接收为 Blob
                    from fastapi.responses import Response
                    return Response(
                        content=image_bytes,
                        media_type=f"image/{image_format}",
                        headers={
                            "X-Model-Version": model_version,  # 标记模型版本
                            "Content-Length": str(len(image_bytes)),
                            "Cache-Control": "no-cache"
                        }
                    )
                except Exception as decode_error:
                    logger.error(f"[{request_id}] ❌ Base64 解码失败: {str(decode_error)}")
                    # 如果解码失败，返回错误响应
                    return {
                        "response": f"⚠️ 图片数据解码失败: {str(decode_error)}",
                        "success": False,
                        "image_data": None,
                        "image_url": None,
                        "model_version": model_version,
                        "error_code": "BASE64_DECODE_ERROR"
                    }
            else:
                # 兼容性处理：如果返回的是字符串（旧格式），记录警告并尝试处理
                logger.warning(f"[{request_id}] ⚠️ [模型版本: {model_version}] 收到非字典格式的返回值: {type(image_data)}")
                logger.warning(f"[{request_id}]   期望格式: dict, 实际格式: {type(image_data)}")
                logger.warning(f"[{request_id}]   前50字符: {str(image_data)[:50]}...")
                
                # 尝试作为字符串处理（向后兼容）
                return {
                    "response": f"⚠️ 图片生成返回格式异常（已兼容处理）",
                    "success": False,
                    "image_data": None,
                    "image_url": None,
                    "model_version": model_version,
                    "error_code": "UNEXPECTED_FORMAT"
                }
        else:
            # 如果图片生成失败，返回错误信息
            return {
                "response": f"⚠️ 图片生成失败。\n\n原始提示词: {final_prompt}\n\n提示词已自动润色优化，但仍无法生成图片。请检查后端日志获取详细错误信息，或尝试修改提示词后重试。",
                "success": False,
                "image_data": None,
                "image_url": None,
                "model_version": model_version
            }
    except Exception as e:
        error_msg = f"处理接口错误(Form3): {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "PROCESS3_ERROR",
            "error_detail": traceback.format_exc(),
            "image_data": None,
            "image_url": None
        }

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

@app.post("/api/generate-image")
async def generate_image(request: dict):
    """图片生成接口（使用优化后的提示词，不再重复优化）"""
    try:
        prompt = request.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="提示词不能为空")
        
        aspect_ratio = request.get("aspect_ratio")
        resolution = request.get("resolution")
        skip_optimization = request.get("skip_optimization", False)  # 是否跳过优化（已优化的提示词）
        
        logger.info(f"🖼️ 收到图片生成请求，跳过优化: {skip_optimization}")
        
        if skip_optimization:
            # 如果提示词已经优化过，直接使用，不再优化
            logger.info(f"📝 使用已优化的提示词: {prompt[:100]}...")
            logger.info(f"🎯 使用模型: gemini-3-pro-image-preview")
            temperature = request.get("temperature")  # 获取温度参数（如果有）
            logger.info(f"   温度参数: {temperature or '使用默认值'}")
            image_data = generate_with_gemini_image3(prompt, None, aspect_ratio, temperature)
        else:
            # 如果没有跳过优化，调用 generate_image_with_google（内部会优化）
            logger.info(f"📝 提示词未优化，使用完整流程（包含优化）")
            image_data = generate_image_with_google(prompt, aspect_ratio=aspect_ratio, resolution=resolution, temperature=None)
        
        if image_data:
            return {
                "response": "图片生成成功！",
                "success": True,
                "image_data": image_data,
                "image_url": None
            }
        else:
            return {
                "response": "图片生成失败，请稍后重试",
                "success": False,
                "image_data": None,
                "image_url": None
            }
    except Exception as e:
        error_msg = f"图片生成接口错误: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "response": f"后端报错: {str(e)}",
            "error_code": "GENERATE_IMAGE_ERROR",
            "error_detail": traceback.format_exc(),
            "image_data": None,
            "image_url": None
        }

# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    import traceback
    
    # Cloud Run 要求监听环境变量 PORT；本地默认 8080 以对齐容器
    port = int(os.environ.get("PORT", 8080))
    
    print("=" * 60)
    print("🚀 启动果捷后端服务")
    print("=" * 60)
    print(f"📍 服务地址: http://0.0.0.0:{port}")
    print(f"📝 API 文档: http://0.0.0.0:{port}/docs")
    print("=" * 60)
    
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
