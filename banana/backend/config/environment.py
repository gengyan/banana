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
                # 从元数据服务器获取项目 ID（使用非常短的超时，不要阻塞启动）
                metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
                headers = {"Metadata-Flavor": "Google"}
                response = requests.get(metadata_url, headers=headers, timeout=1)
                if response.status_code == 200:
                    project_id_from_metadata = response.text.strip()
                    logger.info(f"✅ 从元数据服务器获取到项目 ID: {project_id_from_metadata}")
                    os.environ['GOOGLE_CLOUD_PROJECT'] = project_id_from_metadata
                    os.environ['VERTEX_AI_PROJECT'] = project_id_from_metadata
                    google_cloud_project = project_id_from_metadata
                    vertex_ai_project = project_id_from_metadata
                else:
                    logger.warning(f"⚠️ 元数据服务器返回状态码: {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning("⚠️ 元数据服务器请求超时（预期行为，可能不在Cloud Run环境中）")
            except Exception as e:
                logger.warning(f"⚠️ 无法从元数据服务器获取项目 ID: {str(e)}")
                logger.warning("   这通常意味着：")
                logger.warning("   1) 已通过环境变量设置了项目ID")
                logger.warning("   2) 或者某些环境变量配置不完整")
    
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
    
    if all_ok:
        logger.info("✅ [启动验证] 环境变量配置检查通过")
    else:
        logger.error("❌ [启动验证] 环境变量配置检查失败，请查看上述警告")
    
    return all_ok
