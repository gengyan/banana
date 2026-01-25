"""
Gemini 3 Pro Image 图片生成器 (Nano Banana Pro)

使用 Gemini 3 Pro Image (gemini-3-pro-image-preview) 模型进行图片生成
支持：
- 基础生图（文生图）
- 图文交织生成（同时生成文字和图片）
- 图片修改与多轮对话（图生图，支持最多14张参考图片）

与 Gemini 2.5 Flash Image 的区别：
- 2.5 版本：只支持 1K 分辨率，最多 3 张参考图，使用 response_modalities=["IMAGE"]
- 3.0 Pro 版本：支持 4K 分辨率，最多 14 张参考图，使用 response_modalities=[Modality.TEXT, Modality.IMAGE]
"""
import os
import base64
import logging
import traceback
import io
import time
from pathlib import Path
from typing import Optional, List, Tuple, Callable
from functools import wraps
from PIL import Image

# ⚠️ 重要：加载环境变量（确保能读取到 .env 文件中的配置）
# 自动定位并加载 .env 文件（从当前文件向上查找）
# 注意：在 Cloud Run 等生产环境中，环境变量通常通过 --set-env-vars 设置，
# 但为了本地开发和调试，我们仍然需要支持从 .env 文件加载
try:
    from dotenv import load_dotenv, find_dotenv
    
    # 方法1：尝试使用 find_dotenv() 自动查找 .env 文件（从当前目录向上查找）
    env_file = find_dotenv()
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
        # 使用临时 logger（因为正式 logger 还未初始化）
        temp_logger = logging.getLogger("果捷后端")
        temp_logger.info(f"✅ [gemini_3_pro_image] 已加载环境变量文件: {env_file}")
    else:
        # 方法2：如果 find_dotenv() 找不到，手动查找 backend/.env
        current_file = Path(__file__).resolve()
        env_path = current_file.parent.parent / '.env'  # backend/.env
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            temp_logger = logging.getLogger("果捷后端")
            temp_logger.info(f"✅ [gemini_3_pro_image] 已加载环境变量文件: {env_path}")
        else:
            # 方法3：尝试项目根目录
            env_path = current_file.parent.parent.parent / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=False)
                temp_logger = logging.getLogger("果捷后端")
                temp_logger.info(f"✅ [gemini_3_pro_image] 已加载环境变量文件: {env_path}")
            else:
                # 如果都找不到，尝试默认的 load_dotenv()（可能环境变量已通过其他方式设置）
                load_dotenv(override=False)
                temp_logger = logging.getLogger("果捷后端")
                temp_logger.info("✅ [gemini_3_pro_image] 已尝试加载环境变量（未找到 .env 文件，可能使用系统环境变量）")
except ImportError:
    # 如果 python-dotenv 未安装，记录警告但继续运行（可能环境变量已通过其他方式设置）
    temp_logger = logging.getLogger("果捷后端")
    temp_logger.warning("⚠️ [gemini_3_pro_image] python-dotenv 未安装，无法自动加载 .env 文件")

logger = logging.getLogger("果捷后端")

# ========== 代理配置 ==========
# ⚠️ 重要：检测运行环境，只在本地开发环境使用代理
# 在 Google Cloud Run 等云端环境中，不需要代理（直接访问 Google 服务）
def _should_use_proxy():
    """判断是否应该使用代理"""
    # 检测是否在 Cloud Run 环境（通过 K_SERVICE 环境变量）
    if os.getenv('K_SERVICE'):
        logger.info("🌐 检测到 Cloud Run 环境，不使用代理")
        return False
    
    # 检测是否在其他云端环境
    if os.getenv('GAE_ENV') or os.getenv('GOOGLE_CLOUD_PROJECT'):
        # 如果明确设置了 DISABLE_PROXY，则不使用代理
        if os.getenv('DISABLE_PROXY', '').lower() == 'true':
            logger.info("🌐 检测到云端环境且 DISABLE_PROXY=true，不使用代理")
            return False
    
    # ⚠️ 重要：如果明确设置了 DISABLE_PROXY，则不使用代理（即使在本地环境）
    if os.getenv('DISABLE_PROXY', '').lower() == 'true':
        logger.info("🌐 DISABLE_PROXY=true，不使用代理（直接连接）")
        # 清除可能存在的代理环境变量
        proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        for key in proxy_keys:
            if key in os.environ:
                os.environ.pop(key, None)
        return False
    
    # 本地开发环境：检查代理是否可用
    PROXY_HOST = os.getenv('PROXY_HOST', '127.0.0.1')
    PROXY_PORT = os.getenv('PROXY_PORT', '29290')
    PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"
    
    # 如果环境变量中已经设置了代理，使用环境变量的值
    if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
        proxy_url = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
        logger.info(f"🔗 使用环境变量中的代理: {proxy_url}")
        logger.info(f"💡 如果代理连接失败，可以设置 DISABLE_PROXY=true 禁用代理")
        return True
    
    # 本地开发环境：设置代理
    logger.info(f"🔗 本地开发环境，设置代理: HTTP_PROXY={PROXY_URL}, HTTPS_PROXY={PROXY_URL}")
    logger.info(f"💡 如果代理连接失败，可以设置 DISABLE_PROXY=true 禁用代理")
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
    return True

# 根据环境决定是否使用代理
_should_use_proxy()

# 导入 google.genai（新的统一 SDK）
try:
    from google import genai as genai_new
    from google.genai import types
    from google.genai.types import Modality, FinishReason
    GEMINI_NEW_AVAILABLE = True
except ImportError:
    GEMINI_NEW_AVAILABLE = False
    logger.warning("⚠️ google.genai 模块不可用，请使用 pip install --upgrade google-genai 安装")


# ========== 重试装饰器（已禁用：失败即返回，不重试）==========
# ⚠️ 注意：根据用户要求，调用 Google 服务失败即返回，不需要重试
# 此装饰器保留但不再使用，直接调用函数即可
def retry_on_network_error(max_retries: int = 1, delay: float = 0.0):
    """重试装饰器（已禁用：失败即返回，不重试）
    
    ⚠️ 根据用户要求，调用 Google 服务失败即返回，不需要重试
    此装饰器保留但不再使用，直接调用函数即可
    
    Args:
        max_retries: 最大重试次数（已设置为 1，即不重试）
        delay: 重试延迟（秒，已设置为 0，即不延迟）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 直接调用函数，不进行重试
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _get_genai_client():
    """获取或创建 google.genai Client 实例（Vertex AI 模式）
    
    使用 Vertex AI 模式，通过服务账户凭据进行身份验证
    
    环境变量要求：
    - VERTEX_AI_PROJECT 或 GOOGLE_CLOUD_PROJECT: Vertex AI 项目 ID
    - VERTEX_AI_LOCATION 或 GOOGLE_CLOUD_LOCATION: Vertex AI 位置（默认: global）
    - GOOGLE_APPLICATION_CREDENTIALS: 服务账户凭据 JSON 文件路径（或自动查找 google-key.json）
    
    可选代理配置：
    - PROXY_HOST: 代理主机地址（默认: 127.0.0.1）
    - PROXY_PORT: 代理端口（如果设置，将自动配置 HTTP_PROXY 和 HTTPS_PROXY）
    - HTTP_PROXY: HTTP 代理 URL（如果已设置，将直接使用）
    - HTTPS_PROXY: HTTPS 代理 URL（如果已设置，将直接使用）
    
    注意：此函数专门用于 gemini-3-pro-image-preview 模型
    """
    if not GEMINI_NEW_AVAILABLE:
        return None
    
    # ⚠️ 重要：使用 dotenv 准确加载 backend/.env
    # 即使文件开头已经加载过，这里再次确保加载（防止模块导入顺序问题）
    try:
        from dotenv import load_dotenv
        
        # 获取当前文件的绝对路径
        current_file = Path(__file__).resolve()
        # 准确加载 backend/.env 文件
        backend_env_path = current_file.parent.parent / '.env'  # backend/.env
        
        if backend_env_path.exists():
            load_dotenv(dotenv_path=backend_env_path, override=False)
            logger.info(f"✅ [_get_genai_client] 已准确加载 backend/.env 文件: {backend_env_path}")
        else:
            logger.warning(f"⚠️ [_get_genai_client] backend/.env 文件不存在: {backend_env_path}")
            # 回退到自动查找
            from dotenv import find_dotenv
            env_file = find_dotenv()
            if env_file:
                load_dotenv(dotenv_path=env_file, override=False)
                logger.info(f"✅ [_get_genai_client] 已加载环境变量文件（自动查找）: {env_file}")
            else:
                logger.warning("⚠️ [_get_genai_client] 未找到 .env 文件，将使用系统环境变量")
    except ImportError:
        logger.warning("⚠️ python-dotenv 未安装，跳过环境变量加载")
    
    # ⚠️ 重要：显式加载 .env 文件（使用容器根目录路径）
    # 参考 Google 建议：使用 os.path.join(os.getcwd(), '.env') 确保在容器根目录加载
    try:
        from dotenv import load_dotenv
        env_paths = [
            os.path.join(os.getcwd(), '.env'),  # 容器根目录
            os.path.join(os.path.dirname(__file__), '..', '.env'),  # backend/.env
            os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # 项目根目录
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, override=False)
                logger.info(f"✅ [_get_genai_client] 已加载环境变量文件: {env_path}")
                env_loaded = True
                break
        
        if not env_loaded:
            load_dotenv(override=False)
            logger.warning("⚠️ [_get_genai_client] 未找到 .env 文件，将使用系统环境变量")
    except ImportError:
        logger.warning("⚠️ python-dotenv 未安装，跳过环境变量加载")
    
    # 检查 Vertex AI 环境变量（参考官方demo：支持 api_key 或服务账户凭据）
    # ⚠️ Fallback 机制：如果 VERTEX_AI_PROJECT 缺失，尝试读取 GOOGLE_CLOUD_PROJECT 作为备份
    vertex_ai_project = os.getenv("VERTEX_AI_PROJECT")
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # Fallback 机制
    if not vertex_ai_project and google_cloud_project:
        logger.info(f"✅ 使用 Fallback 机制: GOOGLE_CLOUD_PROJECT ({google_cloud_project}) -> VERTEX_AI_PROJECT")
        os.environ['VERTEX_AI_PROJECT'] = google_cloud_project
        vertex_ai_project = google_cloud_project
    
    vertex_ai_location = os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    
    # 优先使用 API Key（参考官方demo）
    api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
    google_app_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # ⚠️ 自动获取 google-key.json 的绝对路径并赋值给 os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    # ⚠️ 绝对路径校验：如果文件丢失，通过日志显示当前容器里的文件列表
    if not google_app_credentials:
        current_file = Path(__file__).resolve()
        # 查找 google-key.json（多个可能位置）
        google_key_paths = [
            current_file.parent.parent / 'google-key.json',  # backend/google-key.json
            current_file.parent.parent.parent / 'google-key.json',  # 项目根目录
            Path(os.getcwd()) / 'google-key.json',  # 容器根目录
        ]
        
        google_key_found = False
        for google_key_path in google_key_paths:
            if google_key_path.exists():
                # 获取绝对路径
                google_app_credentials = str(google_key_path.resolve())
                # 赋值给环境变量
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_app_credentials
                logger.info(f"✅ 自动获取 google-key.json 绝对路径并设置: {google_app_credentials}")
                google_key_found = True
                break
        
        if not google_key_found:
            logger.warning("⚠️ 未找到 google-key.json 文件，将尝试使用 API Key 或其他认证方式")
            # 绝对路径校验：如果文件丢失，通过日志显示当前容器里的文件列表
            logger.warning("📋 当前容器文件列表（用于调试）:")
            try:
                current_dir = os.getcwd()
                files_in_dir = os.listdir(current_dir)
                logger.warning(f"   当前目录 ({current_dir}): {', '.join(files_in_dir[:30])}...")  # 显示前30个文件
            except Exception as e:
                logger.warning(f"   无法列出目录文件: {e}")
    
    # ⚠️ 在初始化前，打印 os.path.exists(credentials_path) 来确认文件是否存在
    if google_app_credentials:
        credentials_path = Path(google_app_credentials).resolve()
        credentials_exists = os.path.exists(credentials_path)
        logger.info(f"🔍 检查凭据文件（在初始化 Client 之前）:")
        logger.info(f"   凭据文件路径: {credentials_path}")
        logger.info(f"   os.path.exists(credentials_path): {credentials_exists}")
        
        if not credentials_exists:
            logger.error(f"❌ 凭据文件不存在: {credentials_path}")
            logger.error("💡 请确保 google-key.json 文件存在于 backend/ 目录下")
            # 如果使用服务账户凭据且文件不存在，且没有 API Key，则返回 None
            if not api_key:
                logger.error("❌ 无法使用服务账户凭据（文件不存在），且未提供 API Key")
                return None
    
    # 调试信息：打印环境变量状态（帮助排查问题）
    logger.info(f"🔍 环境变量检查:")
    logger.info(f"   VERTEX_AI_PROJECT: {os.getenv('VERTEX_AI_PROJECT', '未设置')}")
    logger.info(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', '未设置')}")
    logger.info(f"   VERTEX_AI_LOCATION: {os.getenv('VERTEX_AI_LOCATION', '未设置')}")
    logger.info(f"   GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION', '未设置')}")
    logger.info(f"   GOOGLE_CLOUD_API_KEY: {'已设置' if api_key else '未设置'}")
    logger.info(f"   GOOGLE_APPLICATION_CREDENTIALS: {google_app_credentials or '未设置'}")
    logger.info(f"📋 检测到的项目 ID: {vertex_ai_project or '未找到'}")
    
    # 必须使用 Vertex AI 模式
    if not vertex_ai_project:
        logger.error("❌ VERTEX_AI_PROJECT 未设置，无法使用 Vertex AI 模式")
        logger.error("💡 请设置 VERTEX_AI_PROJECT 或 GOOGLE_CLOUD_PROJECT 环境变量")
        logger.error("💡 检查 backend/.env 文件是否存在，以及是否包含正确的配置")
        logger.error("💡 如果使用 Cloud Run，请确保通过 --set-env-vars 设置了环境变量")
        return None
    
    # 检查认证方式：优先使用 API Key，否则使用服务账户凭据
    if not api_key and not google_app_credentials:
        logger.error("❌ 未设置认证方式，无法使用 Vertex AI 模式")
        logger.error("💡 请设置 GOOGLE_CLOUD_API_KEY 或 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
        return None
    
    if google_app_credentials and not os.path.exists(google_app_credentials):
        logger.error(f"❌ 服务账户凭据文件不存在: {google_app_credentials}")
        return None
    
    logger.info(f"🔧 使用 Vertex AI 模式: project={vertex_ai_project}, location={vertex_ai_location}")
    if api_key:
        logger.info("   认证方式: API Key")
    else:
        logger.info("   认证方式: 服务账户凭据")
    
    try:
        # ⚠️ 设置超时时间：10分钟（600秒 = 600000毫秒），匹配前端和 Cloud Run 的超时设置
        # 根据 Google genai SDK 文档，超时通过 HttpOptions 设置，单位为毫秒
        http_options = types.HttpOptions(timeout=600_000)  # 600秒 = 600000毫秒（10分钟）
        
        # ⚠️ 重要：在 Cloud Run 等云端环境，不需要设置代理
        # 代理配置已在文件开头根据环境自动处理
        
        # 参考官方demo：使用 vertexai=True 和 api_key（如果提供）
        if api_key:
            # 使用 API Key 认证（参考官方demo）
            client = genai_new.Client(
                vertexai=True,
                api_key=api_key,
                http_options=http_options
            )
        else:
            # 使用服务账户凭据认证
            # 确保 GOOGLE_APPLICATION_CREDENTIALS 已设置（在自动查找 google-key.json 时已设置）
            if google_app_credentials:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials
            client = genai_new.Client(
                vertexai=True,
                project=vertex_ai_project,
                location=vertex_ai_location,
                http_options=http_options
            )
        logger.info("✅ Vertex AI Client 创建成功")
        return client
    except Exception as e:
        logger.error(f"❌ 创建 Vertex AI Client 失败: {e}")
        logger.error(f"📋 错误详情: {traceback.format_exc()}")
        return None


def _generate_content_with_timeout(client, model_id: str, contents, config, function_name: str = "生图", timeout: int = 600):
    """带超时的 generate_content 包装函数（失败即返回，不重试）
    
    ⚠️ 根据用户要求：
    - 设置超时时间为10分钟（600秒），匹配前端和 Cloud Run 的超时设置
    - 调用 Google 服务失败即返回，不需要重试
    
    Args:
        client: genai Client 实例
        model_id: 模型 ID
        contents: 消息内容
        config: GenerateContentConfig 配置
        function_name: 函数名称（用于日志）
        timeout: 超时时间（秒，默认600秒/10分钟，不低于100秒）
    
    Returns:
        generate_content 的响应对象
    
    Raises:
        Exception: 如果请求失败，直接抛出异常（不重试）
    """
    logger.info(f"[{function_name}] 发送请求到 Google API (Vertex AI) (超时: {timeout}秒)")
    
    # 确保超时时间不低于100秒
    if timeout < 100:
        logger.warning(f"⚠️ 超时时间 {timeout} 秒低于100秒，自动调整为100秒")
        timeout = 100
    
    try:
        # ⚠️ 注意：超时时间已在创建 Client 时通过 HttpOptions 设置
        # 这里直接调用 generate_content，超时由 Client 的 http_options 控制
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config
        )
        logger.info(f"[{function_name}] 请求成功")
        return response
    except Exception as e:
        # 在异常时打印代理状态和错误信息
        error_name = type(e).__name__
        error_message = str(e)
        logger.error(f"[{function_name}] 请求失败: {error_name} - {error_message}")
        
        # 创建详细的错误信息字典
        error_info = {
            "error_type": error_name,
            "error_message": error_message,
            "error_code": None,
            "error_detail": None
        }
        
        # 识别特定的错误类型并设置错误码
        if "ProxyError" in error_name or "proxy" in error_message.lower():
            error_info["error_code"] = "PROXY_ERROR"
            error_info["error_detail"] = f"代理连接失败: {error_message}"
            logger.error(f"💡 代理配置问题，请检查:")
            logger.error(f"   1. 代理服务是否在 {os.getenv('PROXY_HOST', '127.0.0.1')}:{os.getenv('PROXY_PORT', '29290')} 运行")
            logger.error(f"   2. 或设置 DISABLE_PROXY=true 禁用代理")
        elif "ChunkedEncodingError" in error_name or "ended prematurely" in error_message.lower():
            error_info["error_code"] = "CHUNKED_ENCODING_ERROR"
            error_info["error_detail"] = f"Google API 响应不完整（分块传输中断）: {error_message}"
            logger.error(f"💡 分块传输错误，可能原因:")
            logger.error(f"   1. 网络连接不稳定（代理或直连）")
            logger.error(f"   2. Google API 超时或限流")
            logger.error(f"   3. 请求体过大或复杂")
            logger.error(f"   建议: 简化提示词或暂时禁用代理（DISABLE_PROXY=true）")
        elif "Timeout" in error_name or "timeout" in error_message.lower() or "超时" in error_message:
            error_info["error_code"] = "TIMEOUT_ERROR"
            error_info["error_detail"] = f"Vertex AI 请求超时（超时设置: {timeout}秒）: {error_message}"
        elif "SAFETY" in error_message.upper() or "安全" in error_message:
            error_info["error_code"] = "SAFETY_BLOCKED"
            error_info["error_detail"] = f"安全策略拦截: {error_message}"
        elif "API" in error_name or "api" in error_message.lower():
            error_info["error_code"] = "API_ERROR"
            error_info["error_detail"] = f"API 调用失败: {error_message}"
        else:
            error_info["error_code"] = "UNKNOWN_ERROR"
            error_info["error_detail"] = f"未知错误: {error_message}"
        
        # 将错误信息附加到异常对象，以便上层捕获
        e.error_info = error_info
        # 直接抛出异常，不进行重试
        raise


def _optimize_prompt_for_image_generation(prompt: str) -> str:
    """优化提示词，确保触发图片生成引擎
    
    根据官方最佳实践，在 Prompt 中明确包含 "Generate an image of..." 字样
    """
    prompt_lower = prompt.lower()
    
    # 如果提示词已经包含图片生成相关的关键词，直接返回
    image_keywords = [
        "generate an image",
        "create an image",
        "draw",
        "picture of",
        "image of",
        "photo of",
        "illustration of"
    ]
    
    if any(keyword in prompt_lower for keyword in image_keywords):
        return prompt
    
    # 否则，在开头添加 "Generate an image of"
    return f"Generate an image of {prompt}"


def _is_base64_string(data: str) -> bool:
    """检查字符串是否是 Base64 编码的图片数据
    
    Args:
        data: 待检查的字符串
    
    Returns:
        如果是 Base64 图片数据返回 True，否则返回 False
    """
    if not isinstance(data, str) or len(data) < 4:
        return False
    # JPEG: /9j/, PNG: iVBOR, GIF: R0lGO
    return data.startswith('/9j/') or data.startswith('iVBOR') or data.startswith('R0lGO')


def _extract_image_from_response(response, function_name: str = "生图") -> Optional[Tuple[any, str]]:
    """从响应中提取图片数据（健壮的提取方法）
    
    支持多种响应结构：
    - response.parts
    - response.candidates[0].content.parts
    
    Args:
        response: generate_content 的响应对象
        function_name: 函数名称（用于日志）
    
    Returns:
        (image_data, mime_type) 元组，image_data 可能是 bytes 或 str（Base64）
        如果是安全策略拦截，返回 ("SAFETY_BLOCKED", "error")，失败返回 None
    """
    try:
        logger.info(f"🔍 [{function_name}] 开始解析响应，查找图片数据...")
        
        # ⚠️ 调试：输出响应结构
        logger.info(f"📋 [{function_name}] 响应类型: {type(response)}")
        logger.info(f"📋 [{function_name}] 响应属性: {dir(response)}")
        if hasattr(response, 'candidates'):
            logger.info(f"📋 [{function_name}] candidates 数量: {len(response.candidates) if response.candidates else 0}")
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                logger.info(f"📋 [{function_name}] candidate[0] 类型: {type(candidate)}")
                logger.info(f"📋 [{function_name}] candidate[0] 属性: {dir(candidate)}")
                if hasattr(candidate, 'content'):
                    logger.info(f"📋 [{function_name}] content 类型: {type(candidate.content)}")
                    if hasattr(candidate.content, 'parts'):
                        logger.info(f"📋 [{function_name}] parts 数量: {len(candidate.content.parts) if candidate.content.parts else 0}")
                        if candidate.content.parts:
                            for idx, part in enumerate(candidate.content.parts):
                                logger.info(f"📋 [{function_name}] part[{idx}] 类型: {type(part)}")
                                logger.info(f"📋 [{function_name}] part[{idx}] 属性: {dir(part)}")
        
        
        image_data = None
        # ⚠️ 关键修复：Gemini 3 Pro Image 默认返回 JPEG 格式（不是 PNG）
        mime_type = "image/jpeg"  # 改为 JPEG（Gemini 3 Pro 的标准格式）
        
        # 方式1：尝试从 response.parts 提取
        if hasattr(response, 'parts') and response.parts:
            for idx, part in enumerate(response.parts):
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    try:
                        raw_data = part.inline_data.data
                        # ⚠️ 重要：从响应中获取实际的 MIME 类型（如果返回了）
                        response_mime_type = getattr(part.inline_data, 'mime_type', None)
                        if response_mime_type:
                            mime_type = response_mime_type
                            logger.info(f"✅ [{function_name}] 从响应中获取 MIME 类型: {mime_type}")
                        else:
                            logger.info(f"ℹ️ [{function_name}] 响应未提供 MIME 类型，使用默认值: {mime_type}")
                        
                        # 处理 raw_data：如果是 Base64 字符串直接返回，避免二次编码
                        if isinstance(raw_data, str):
                            if _is_base64_string(raw_data):
                                image_data = raw_data
                                logger.info(f"✅ [{function_name}] 检测到 Base64 字符串，直接返回（避免二次编码）")
                            else:
                                try:
                                    image_data = base64.b64decode(raw_data)
                                    logger.info(f"✅ [{function_name}] Base64 解码成功，解码后大小: {len(image_data)} bytes")
                                except Exception as e:
                                    logger.warning(f"⚠️ [{function_name}] Base64 解码失败: {e}")
                                    continue
                        elif isinstance(raw_data, bytes):
                            image_data = raw_data
                            logger.info(f"✅ [{function_name}] 数据已经是 bytes 类型，大小: {len(image_data)} bytes")
                        else:
                            logger.error(f"❌ [{function_name}] 不支持的数据类型: {type(raw_data)}")
                            continue
                        
                        if image_data:
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ [{function_name}] 提取 response.parts[{idx}] 失败: {e}")
                        continue
        
        # 方式2：尝试从 response.candidates[0].content.parts 提取（标准结构）
        if not image_data and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # 检查 finish_reason（安全过滤等）- 使用字符串判断避免 AttributeError
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                # 获取 finish_reason 的字符串表示并转为大写
                reason_str = str(finish_reason).upper()
                
                # 检查是否包含安全相关的关键词
                if "SAFETY" in reason_str:
                    error_type = "IMAGE_SAFETY" if "IMAGE" in reason_str else "SAFETY"
                    logger.error(f"❌ [{function_name}] 图片生成因安全策略被拦截 ({error_type})")
                    logger.error(f"   finish_reason: {finish_reason}")
                    # 返回特殊值，标识为安全策略拦截
                    return ("SAFETY_BLOCKED", "error")
            
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for idx, part in enumerate(candidate.content.parts):
                            if hasattr(part, 'inline_data') and part.inline_data is not None:
                                try:
                                    raw_data = part.inline_data.data
                                    # ⚠️ 重要：从响应中获取实际的 MIME 类型（如果返回了）
                                    response_mime_type = getattr(part.inline_data, 'mime_type', None)
                                    if response_mime_type:
                                        mime_type = response_mime_type
                                        logger.info(f"✅ [{function_name}] 从响应中获取 MIME 类型: {mime_type}")
                                    else:
                                        logger.info(f"ℹ️ [{function_name}] 响应未提供 MIME 类型，使用默认值: {mime_type}")
                                    
                                    # 处理 raw_data：如果是 Base64 字符串直接返回，避免二次编码
                                    if isinstance(raw_data, str):
                                        if _is_base64_string(raw_data):
                                            image_data = raw_data
                                            logger.info(f"✅ [{function_name}] 检测到 Base64 字符串，直接返回（避免二次编码）")
                                        else:
                                            try:
                                                image_data = base64.b64decode(raw_data)
                                                logger.info(f"✅ [{function_name}] Base64 解码成功，解码后大小: {len(image_data)} bytes")
                                            except Exception as e:
                                                logger.warning(f"⚠️ [{function_name}] Base64 解码失败: {e}")
                                                continue
                                    elif isinstance(raw_data, bytes):
                                        image_data = raw_data
                                        logger.info(f"✅ [{function_name}] 数据已经是 bytes 类型，大小: {len(image_data)} bytes")
                                    else:
                                        logger.error(f"❌ [{function_name}] 不支持的数据类型: {type(raw_data)}")
                                        continue
                                    
                                    if image_data:
                                        break
                                except Exception as e:
                                    logger.warning(f"⚠️ [{function_name}] 提取 candidate.parts[{idx}] 失败: {e}")
                                    continue
        
        # 方式3：尝试使用 as_image() 方法（备用方案）
        if not image_data:
            parts_to_check = []
            if hasattr(response, 'parts') and response.parts:
                parts_to_check = response.parts
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        parts_to_check = candidate.content.parts
            
            for part in parts_to_check:
                if hasattr(part, 'as_image'):
                    try:
                        image = part.as_image()
                        if image:
                            img_buffer = io.BytesIO()
                            image.save(img_buffer, format='PNG')
                            image_data = img_buffer.getvalue()
                            mime_type = "image/png"
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ [{function_name}] as_image() 失败: {e}")
                        continue
        
        if not image_data:
            logger.error(f"❌ [{function_name}] 失败: 响应中未找到图片数据")
            return None
        
        # 如果 image_data 是字符串（Base64），直接返回
        if isinstance(image_data, str):
            return (image_data, mime_type)
        
        # 如果 image_data 是 bytes，进行验证（但不阻断流程）
        if not isinstance(image_data, bytes):
            logger.error(f"❌ [{function_name}] image_data 类型不正确: {type(image_data)}")
            return None
        
        # 尝试用 PIL 验证图片数据（但不阻断流程）
        try:
            img = Image.open(io.BytesIO(image_data))
            img.load()
            logger.info(f"✅ [{function_name}] 图片验证成功: {img.size[0]}x{img.size[1]} pixels")
        except Exception as e:
            logger.warning(f"⚠️ [{function_name}] PIL 验证失败（但不阻断流程）: {e}")
        
        return (image_data, mime_type)
        
    except Exception as e:
        logger.error(f"❌ [{function_name}] 提取图片数据失败: {e}")
        logger.error(f"📋 错误详情: {traceback.format_exc()}")
        return None


def generate_image(prompt: str, reference_images: Optional[List[Image.Image]] = None,
                                  aspect_ratio: Optional[str] = None, temperature: Optional[float] = None, 
                   resolution: Optional[str] = None) -> Optional[dict]:
    """
    基础生图功能（文生图或图生图）
    
    使用 Gemini 3 Pro Image 模型，支持：
    - 文生图：仅提供提示词
    - 图生图：提供提示词 + 参考图片（最多14张）
    
    与 Gemini 2.5 Flash Image 的区别：
    - 2.5: response_modalities=["IMAGE"], 最多3张参考图, 只支持1K
    - 3.0 Pro: response_modalities=[Modality.TEXT, Modality.IMAGE], 最多14张参考图, 支持4K
    
    Args:
        prompt: 图片生成提示词
        reference_images: 参考图片列表（PIL Image 对象），可选。最多14张
        aspect_ratio: 长宽比（可选），例如 "16:9", "4:3", "1:1" 等
        temperature: 温度参数（可选，默认 0.4）
        resolution: 图片分辨率（可选），"1K", "2K", "4K"
    
    Returns:
        包含图片数据的字典: {"image_data": "base64_string", "image_format": "png"|"jpeg"}
        失败返回 None
    """
    has_reference = reference_images and len(reference_images) > 0
    mode_str = "图生图" if has_reference else "文生图"
    logger.info("=" * 80)
    logger.info(f"🖼️ [Gemini 3 Pro Image] 开始{mode_str}")
    logger.info(f"📝 提示词: {prompt[:150]}...")
    if has_reference:
        logger.info(f"📸 参考图片数量: {len(reference_images)}（最多14张）")
    if aspect_ratio:
        logger.info(f"📐 长宽比: {aspect_ratio}")
    if resolution:
        logger.info(f"📏 分辨率: {resolution}（支持 4K）")
    if temperature is not None:
        logger.info(f"🌡️ 温度: {temperature}")
    logger.info(f"🔧 生成器: gemini_3_pro_image.py")
    logger.info("=" * 80)
    
    if not GEMINI_NEW_AVAILABLE:
        logger.error("❌ google.genai 模块不可用，无法使用 Gemini 3 Pro Image")
        return {
            "error": True,
            "error_type": "ModuleNotAvailable",
            "error_message": "google.genai 模块不可用，无法使用 Gemini 3 Pro Image",
            "error_code": "MODULE_NOT_AVAILABLE",
            "error_detail": "google.genai 模块未安装或导入失败，请检查依赖"
        }
    
    client = _get_genai_client()
    if not client:
        logger.error("❌ 无法创建 genai Client")
        return {
            "error": True,
            "error_type": "ClientCreationFailed",
            "error_message": "无法创建 genai Client",
            "error_code": "CLIENT_CREATION_FAILED",
            "error_detail": "无法创建 Google GenAI Client，请检查环境变量和凭证配置"
        }
    
    try:
        model_id = 'gemini-3-pro-image-preview'
        logger.info(f"🎯 使用模型: {model_id}")
        
        # 优化提示词并构建消息内容（参考官方demo使用 types.Content 和 types.Part）
        optimized_prompt = _optimize_prompt_for_image_generation(prompt)
        parts = []
        
        # 添加参考图片（最多14张）
        image_parts_count = 0
        if has_reference:
            for idx, ref_img in enumerate(reference_images[:14]):
                try:
                    if ref_img is None:
                        logger.warning(f"⚠️ 参考图片 {idx+1} 为 None，跳过")
                        continue
                    
                    if ref_img.mode != 'RGB':
                        ref_img = ref_img.convert('RGB')
                    # 将 PIL Image 转换为 bytes，然后使用 types.Part.from_bytes
                    img_bytes = io.BytesIO()
                    ref_img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    parts.append(types.Part.from_bytes(
                        data=img_bytes.read(),
                        mime_type="image/png"
                    ))
                    image_parts_count += 1
                    logger.info(f"✅ 成功添加参考图片 {idx+1}/{len(reference_images[:14])}")
                except Exception as img_error:
                    error_msg = f"处理参考图片 {idx+1} 失败: {str(img_error)}"
                    logger.error(f"❌ {error_msg}")
                    logger.error(f"📋 错误详情: {traceback.format_exc()}")
                    # 如果处理参考图片失败，抛出异常，让外层捕获并返回错误字典
                    raise Exception(f"参考图片处理失败（第 {idx+1} 张）: {str(img_error)}") from img_error
            
            # 验证：如果声明有参考图，但实际没有成功添加任何图片，返回错误
            if image_parts_count == 0:
                logger.error(f"❌ 声明有参考图片，但所有图片处理失败或为空")
                return {
                    "error": True,
                    "error_type": "ReferenceImageProcessingFailed",
                    "error_message": "所有参考图片处理失败或为空",
                    "error_code": "REFERENCE_IMAGE_PROCESSING_FAILED",
                    "error_detail": f"提供了 {len(reference_images)} 张参考图片，但所有图片处理失败或为空，无法继续生成"
                }
        
        # 添加文本提示词
        parts.append(types.Part.from_text(text=optimized_prompt))
        
        # 构建 Content 对象（参考官方demo）
        contents = [
            types.Content(
                role="user",
                parts=parts
            )
        ]
        
        # 构建 GenerateContentConfig（仅保留：长宽比、图片质量、温度）
        response_modalities_list = ["TEXT", "IMAGE"]  # 基础需求：同时返回文本和图片
        logger.info(f"📋 response_modalities: {response_modalities_list}（{'图生图模式' if has_reference else '文生图模式'}）")

        # ⚠️ 注意：当前 SDK 版本的 GenerateContentConfig 不支持 image_config 参数
        # aspect_ratio 和 image_size 参数需要通过其他方式传递或由模型自动处理
        aspect = aspect_ratio or "3:2"
        image_size = (resolution.upper() if resolution else "2K")
        
        logger.info(f"📐 期望的长宽比: {aspect}（注意：当前 SDK 可能不支持通过 config 设置）")
        logger.info(f"📏 期望的分辨率: {image_size}（注意：当前 SDK 可能不支持通过 config 设置）")
        logger.info(f"💡 提示：如果需要特定长宽比或分辨率，请在提示词中明确说明")

        # 其他参数按需启用，默认注释保留：top_p、max_output_tokens、safety_settings、output_mime_type
        config = types.GenerateContentConfig(
            response_modalities=response_modalities_list,
            temperature=temperature if temperature is not None else 1.0,
            # top_p=0.95,
            # max_output_tokens=32768,
            # safety_settings=[
            #     types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            #     types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            #     types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            #     types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            # ],
            # output_mime_type="image/png",
        )
        
        logger.info(f"🌡️ 温度: {temperature if temperature is not None else 1.0}")
        
        logger.info(f"📤 发送请求到 Google API (Vertex AI)，模型: {model_id}, 参考图: {len(reference_images) if has_reference else 0} 张")
        logger.info(f"   端点: Vertex AI")
        logger.info(f"   项目: {os.getenv('VERTEX_AI_PROJECT', os.getenv('GOOGLE_CLOUD_PROJECT', 'N/A'))}")
        logger.info(f"   位置: {os.getenv('VERTEX_AI_LOCATION', os.getenv('GOOGLE_CLOUD_LOCATION', 'global'))}")
        
        # ⚠️ 使用带超时的 generate_content 包装函数（失败即返回，不重试）
        # 超时时间设置为600秒/10分钟（匹配前端和 Cloud Run 的超时设置）
        response = _generate_content_with_timeout(
            client=client,
            model_id=model_id,
            contents=contents,
            config=config,
            function_name=f"Gemini 3 Pro Image {mode_str}",
            timeout=600  # 超时时间设置为600秒/10分钟（匹配前端和 Cloud Run 的超时设置）
        )
        
        # 使用通用的图片提取函数
        result = _extract_image_from_response(response, f"Gemini 3 Pro Image {mode_str}")
        if not result:
            logger.error(f"❌ [Gemini 3 Pro Image {mode_str}] _extract_image_from_response 返回 None")
            return {
                "error": True,
                "error_type": "ImageExtractionFailed",
                "error_message": "无法从响应中提取图片数据",
                "error_code": "IMAGE_EXTRACTION_FAILED",
                "error_detail": "_extract_image_from_response 返回了 None，可能原因：响应中未找到图片数据、安全策略拦截或数据格式错误"
            }
        
        image_data, mime_type = result
        
        # ⚠️ 验证提取结果
        if not image_data:
            logger.error(f"❌ [Gemini 3 Pro Image {mode_str}] 提取的 image_data 为空")
            return {
                "error": True,
                "error_type": "EmptyImageData",
                "error_message": "提取的图片数据为空",
                "error_code": "EMPTY_IMAGE_DATA",
                "error_detail": "从响应中提取的 image_data 为空，可能原因：响应格式异常或图片数据缺失"
            }
        
        # 检查是否是安全策略拦截错误
        if image_data == "SAFETY_BLOCKED" and mime_type == "error":
            logger.error(f"❌ [Gemini 3 Pro Image {mode_str}] 安全策略拦截，返回友好的错误提示")
            # 返回特殊字符串，标识为安全策略错误（前端会识别并显示友好提示）
            return "SAFETY_BLOCKED:内容违反安全策略，无法生成图片。请修改提示词后重试。"
        
        # ⚠️ 关键修复：如果 image_data 已经是 Base64 字符串，直接使用，不要再次编码
        # 需要检测两种情况：
        # 1. 标准 Base64 图片字符串（以 /9j/ 或 iVBOR 开头）- 直接使用
        # 2. 二次编码的 Base64 字符串（以 LzlqLz 开头，这是 /9j/ 的 Base64 编码）- 需要先解码一次
        if isinstance(image_data, str):
            # 检查是否是标准 Base64 图片字符串（一次编码）
            if _is_base64_string(image_data):
                logger.info(f"✅ [Gemini 3 Pro Image {mode_str}] 检测到标准 Base64 字符串（一次编码），直接使用")
                logger.info(f"   Base64 字符串前缀: {image_data[:20]}")
                # ⚠️ 关键修复：根据 Base64 字符串前缀判断格式（兼容 PNG 和 JPEG）
                # /9j/ 开头 = JPEG, iVBOR 开头 = PNG
                if image_data.startswith('/9j/'):
                    image_format = 'jpeg'
                    logger.info(f"   根据前缀 /9j/ 判断格式为: jpeg")
                elif image_data.startswith('iVBOR') or image_data.startswith('iVBO'):
                    image_format = 'png'
                    logger.info(f"   根据前缀 iVBOR/iVBO 判断格式为: png")
                else:
                    # 如果 mime_type 有值，使用 mime_type，否则默认 jpeg（Gemini 3 Pro 通常返回 JPEG）
                    image_format = mime_type.replace('image/', '') if mime_type.startswith('image/') else 'jpeg'
                    logger.info(f"   使用 mime_type 或默认格式: {image_format}")
                
                return {
                    "image_data": image_data,
                    "image_format": image_format
                }
            # 检查是否是二次编码的 Base64 字符串（以 LzlqLz 开头，这是 /9j/ 的 Base64 编码）
            elif image_data.startswith('LzlqLz') or image_data.startswith('LzlqLw'):
                logger.warning(f"⚠️ [Gemini 3 Pro Image {mode_str}] 检测到二次 Base64 编码的字符串（以 LzlqLz 开头）")
                logger.warning(f"   这是 /9j/ 的 Base64 编码，说明数据被二次编码了")
                logger.warning(f"   需要先解码一次，得到标准 Base64 字符串")
                try:
                    # 先解码一次，得到标准 Base64 字符串（/9j/ 开头）
                    decoded_base64 = base64.b64decode(image_data).decode('utf-8', errors='ignore')
                    logger.info(f"✅ 二次编码解码成功，得到标准 Base64 字符串")
                    logger.info(f"   解码后前缀: {decoded_base64[:20]}")
                    logger.info(f"   解码后长度: {len(decoded_base64)} 字符")
                    
                    # 验证解码后的字符串是否是标准 Base64 图片字符串
                    if _is_base64_string(decoded_base64):
                        logger.info(f"✅ 验证通过：解码后是标准 Base64 图片字符串，直接使用（避免再次编码）")
                        # ⚠️ 关键修复：根据 Base64 字符串前缀判断格式（兼容 PNG 和 JPEG）
                        if decoded_base64.startswith('/9j/'):
                            image_format = 'jpeg'
                            logger.info(f"   根据前缀 /9j/ 判断格式为: jpeg")
                        elif decoded_base64.startswith('iVBOR') or decoded_base64.startswith('iVBO'):
                            image_format = 'png'
                            logger.info(f"   根据前缀 iVBOR/iVBO 判断格式为: png")
                        else:
                            # 如果 mime_type 有值，使用 mime_type，否则默认 jpeg
                            image_format = mime_type.replace('image/', '') if mime_type.startswith('image/') else 'jpeg'
                            logger.info(f"   使用 mime_type 或默认格式: {image_format}")
                        
                        return {
                            "image_data": decoded_base64,
                            "image_format": image_format
                        }
                    else:
                        logger.warning(f"⚠️ 解码后的字符串不是标准 Base64 图片格式")
                        logger.warning(f"   解码后前缀: {decoded_base64[:50]}")
                        logger.warning(f"   尝试再次解码为 bytes（可能是三次编码？）")
                        try:
                            # 如果解码后不是标准格式，尝试再次解码为 bytes
                            image_bytes = base64.b64decode(decoded_base64)
                            logger.info(f"✅ 二次解码成功，得到 bytes，大小: {len(image_bytes)} bytes")
                        except Exception as e:
                            logger.error(f"❌ 二次解码失败: {e}")
                            return {
                                "error": True,
                                "error_type": "Base64DecodeFailed",
                                "error_message": f"Base64 二次解码失败: {str(e)}",
                                "error_code": "BASE64_DECODE_FAILED",
                                "error_detail": "无法解码二次编码的 Base64 字符串为图片数据，可能原因：数据格式错误或编码异常"
                            }
                    # 如果二次解码成功，继续处理（不返回，继续执行后续逻辑）
                except Exception as e:
                    logger.error(f"❌ 二次编码解码失败: {e}")
                    logger.error(f"   尝试直接解码原始字符串为 bytes")
                    try:
                        image_bytes = base64.b64decode(image_data)
                        logger.info(f"✅ 直接解码成功，解码后大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
                    except Exception as decode_error:
                        logger.error(f"❌ 直接解码也失败: {decode_error}")
                        return {
                            "error": True,
                            "error_type": "Base64DecodeFailed",
                            "error_message": f"Base64 解码失败: {str(decode_error)}",
                            "error_code": "BASE64_DECODE_FAILED",
                            "error_detail": "无法解码 Base64 字符串为图片数据，可能原因：数据格式错误或编码异常"
                        }
                    # 如果直接解码成功，继续处理
                    # 注意：这里不返回，继续执行后续逻辑
            else:
                # 既不是标准 Base64，也不是二次编码，尝试直接解码为 bytes
                logger.info(f"ℹ️ [Gemini 3 Pro Image {mode_str}] 字符串不是标准 Base64 图片格式，尝试解码为 bytes")
                logger.info(f"   字符串前缀: {image_data[:20]}")
                try:
                    image_bytes = base64.b64decode(image_data)
                    logger.info(f"✅ Base64 解码成功，解码后大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
                except Exception as e:
                    logger.error(f"❌ Base64 解码失败: {e}")
                    return {
                        "error": True,
                        "error_type": "Base64DecodeFailed",
                        "error_message": f"Base64 解码失败: {str(e)}",
                        "error_code": "BASE64_DECODE_FAILED",
                        "error_detail": f"无法解码 Base64 字符串为图片数据: {str(e)}"
                    }
        elif isinstance(image_data, bytes):
            image_bytes = image_data
            logger.info(f"✅ [Gemini 3 Pro Image {mode_str}] 数据已经是 bytes 类型，大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        else:
            logger.error(f"❌ [Gemini 3 Pro Image {mode_str}] 不支持的数据类型: {type(image_data)}")
            return {
                "error": True,
                "error_type": "UnsupportedDataType",
                "error_message": f"不支持的数据类型: {type(image_data)}",
                "error_code": "UNSUPPORTED_DATA_TYPE",
                "error_detail": f"从响应中提取的图片数据类型不支持: {type(image_data).__name__}，期望 str 或 bytes"
            }
        
        logger.info(f"✅ Gemini 3 Pro Image {mode_str}成功")
        logger.info(f"   图片数据大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
        logger.info(f"   响应中的 MIME 类型: {mime_type}")
        
        # ⚠️ 关键修复：使用 PIL 自动检测图片格式，纠正可能错误的 MIME 类型
        # 因为 Gemini API 可能返回错误的 MIME 类型（例如返回 image/jpeg 但实际是 PNG）
        detected_mime_type = mime_type  # 默认使用响应中的 MIME 类型
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()  # 强制加载图片数据，确保格式检测准确
            img_format = img.format
            
            if img_format:
                format_lower = img_format.lower()
                logger.info(f"✅ PIL 检测到图片格式: {format_lower} (图片尺寸: {img.size[0]}x{img.size[1]})")
                
                # 根据 PIL 检测到的格式确定 MIME 类型
                if format_lower == 'png':
                    detected_mime_type = 'image/png'
                elif format_lower in ['jpeg', 'jpg']:
                    detected_mime_type = 'image/jpeg'
                else:
                    logger.warning(f"⚠️ PIL 检测到未知格式: {format_lower}，使用默认 PNG")
                    detected_mime_type = 'image/png'
                
                # 如果检测到的格式与响应中的不一致，使用检测到的格式
                if detected_mime_type != mime_type:
                    logger.warning(f"⚠️ MIME 类型冲突: 响应={mime_type}, PIL检测={detected_mime_type}")
                    logger.warning(f"⚠️ 使用 PIL 检测到的格式（更可靠）: {detected_mime_type}")
                    mime_type = detected_mime_type
                else:
                    logger.info(f"✅ MIME 类型验证通过: {mime_type}")
            else:
                logger.warning(f"⚠️ PIL 无法识别格式，使用响应中的 MIME 类型: {mime_type}")
        except Exception as img_error:
            logger.warning(f"⚠️ PIL 验证失败（但不阻断流程）: {img_error}")
            logger.warning(f"⚠️ 使用响应中的 MIME 类型: {mime_type}")
        
        # ⚠️ 修改：只返回 Base64 字符串和格式信息，不构建 Data URL
        # 让前端自己根据格式构建 Data URL
        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"✅ Base64 编码成功，编码后长度: {len(image_b64)} 字符")
            
            # ⚠️ 关键修复：提取格式（从 mime_type 中提取，例如 'image/png' -> 'png'）
            # Gemini 3 Pro 通常返回 JPEG，所以默认使用 'jpeg' 而不是 'png'
            image_format = mime_type.replace('image/', '') if mime_type.startswith('image/') else 'jpeg'
            
            # 返回包含 Base64 字符串和格式的字典
            # 格式：{"image_data": "base64_string", "image_format": "png"}
            logger.info(f"✅ 返回原始图片数据（Base64 + 格式信息），格式: {image_format}")
            logger.info(f"   Base64 前50字符: {image_b64[:50]}...")
            return {
                "image_data": image_b64,
                "image_format": image_format
            }
        except Exception as e:
            logger.error(f"❌ Base64 编码失败: {e}")
            return {
                "error": True,
                "error_type": "Base64EncodeFailed",
                "error_message": f"Base64 编码失败: {str(e)}",
                "error_code": "BASE64_ENCODE_FAILED",
                "error_detail": f"无法将图片二进制数据编码为 Base64: {str(e)}"
            }
        
    except Exception as e:
        error_name = type(e).__name__
        error_message = str(e)
        logger.error(f"Gemini 3 Pro Image {mode_str}失败: {error_name} - {error_message}")
        
        # 检查异常对象是否包含错误信息（从 _generate_content_with_timeout 传递）
        if hasattr(e, 'error_info'):
            error_info = e.error_info
        else:
            # 如果没有，创建默认错误信息
            error_info = {
                "error_type": error_name,
                "error_message": error_message,
                "error_code": "GENERATION_ERROR",
                "error_detail": f"图片生成失败: {error_message}"
            }
        
        # 返回错误信息字典而不是 None，让调用方能够获取详细错误信息
        return {
            "error": True,
            **error_info
        }


# ========== 向后兼容的接口函数 ==========

def generate_with_gemini_image3(prompt: str, reference_images: Optional[List[Image.Image]] = None,
                                aspect_ratio: Optional[str] = None, temperature: Optional[float] = None,
                                resolution: Optional[str] = None) -> Optional[dict]:
    """
    Gemini 3 Pro Image 生图接口函数（用于 main.py）
    
    函数名中的 "3" 表示 Gemini 3 Pro 版本
    
    Args:
        prompt: 图片生成提示词
        reference_images: 参考图片列表（PIL Image 对象），可选。最多14张
        aspect_ratio: 长宽比（可选），例如 "16:9", "4:3", "1:1" 等
        temperature: 温度参数（可选，默认 0.4）
        resolution: 图片分辨率（可选），"1K", "2K", "4K"
    
    Returns:
        生成的图片 base64 data URL，失败返回 None
    """
    return generate_image(
        prompt=prompt,
        reference_images=reference_images,
        aspect_ratio=aspect_ratio,
        temperature=temperature,
        resolution=resolution
    )
