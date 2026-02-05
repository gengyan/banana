"""
环境变量验证模块 - 启动时验证关键环境变量配置
"""
import os
import logging

logger = logging.getLogger("果捷后端")


def validate_environment_variables():
    """验证关键环境变量是否已加载，输出详细日志"""
    logger.info("🔍 [启动验证] 检查关键环境变量配置")
    
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
    
    # 检查关键环境变量（AI Studio 优先）
    vertex_ai_project = os.getenv("VERTEX_AI_PROJECT")
    google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")
    
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
        "GOOGLE_API_KEY": "已设置" if google_api_key else "未设置",
        "VERTEX_AI_PROJECT": vertex_ai_project or os.getenv("GOOGLE_CLOUD_PROJECT"),
        "GOOGLE_CLOUD_PROJECT": google_cloud_project,
        "VERTEX_AI_LOCATION": os.getenv("VERTEX_AI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION"),
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
            if var_name in ["VERTEX_AI_PROJECT", "GOOGLE_CLOUD_PROJECT", "VERTEX_AI_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"]:
                logger.info(f"   ℹ️ {var_name}: 未设置（AI Studio 模式可忽略）")
            else:
                logger.warning(f"   ⚠️ {var_name}: 未设置")
    
    # 重新评估 all_ok（AI Studio 仅要求 API Key）
    all_ok = True
    
    if not google_api_key:
        logger.error("=" * 80)
        logger.error("🚨 [严重警告] GOOGLE_API_KEY 未设置！")
        logger.error("🚨 [严重警告] 这将导致 AI Studio 图片生成功能无法使用！")
        logger.error("🚨 [严重警告] 请检查：")
        logger.error("   1. backend/.env 是否存在并包含 GOOGLE_API_KEY")
        logger.error("   2. 运行环境是否注入 GOOGLE_API_KEY")
        logger.error("=" * 80)
        all_ok = False
    else:
        logger.info("✅ 认证方式: API Key")
    
    if all_ok:
        logger.info("✅ [启动验证] 环境变量配置检查通过")
    else:
        logger.error("❌ [启动验证] 环境变量配置检查失败，请查看上述警告")
    
    return all_ok
