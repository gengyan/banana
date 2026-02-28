"""
代理配置模块 - 统一管理 HTTP/SOCKS5/直连代理配置
"""
import os
import logging

logger = logging.getLogger("果捷后端")


def setup_proxy():
    """
    配置代理（需要在导入 Google API 之前处理）

    本地调试：用 ./start.sh，会 export HTTP_PROXY，或走「本地开发」默认 127.0.0.1:29290
    服务器/Docker：强制禁用代理，直连 Google API
    """
    proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']

    # 检测 Docker 容器（/.dockerenv 或 /run/.containerenv）
    is_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
    is_cloud_run = bool(os.getenv('K_SERVICE'))

    # Docker/Podman/Cloud Run：强制清除代理，直连（服务器无本地代理）
    if is_docker or is_cloud_run:
        os.environ["DISABLE_PROXY"] = "true"  # 供 generators 识别
        for key in proxy_keys:
            os.environ.pop(key, None)
        print("✅ 代理已禁用（Docker/Cloud Run 环境），直接连接")
        return
    # 本地环境
    disproxy_val = os.getenv("DISABLE_PROXY", "").strip()
    disable_proxy = disproxy_val.lower() == "true"
    use_proxy_flag = os.getenv("USE_PROXY", "").lower() == "true"
    use_socks5_proxy = os.getenv("USE_SOCKS5_PROXY", "").lower() == "true"

    if disable_proxy:
        print("✅ 代理已禁用（DISABLE_PROXY=true），直接连接")
        # 清除所有代理环境变量（包括从 .env 文件加载的）
        proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        for key in proxy_keys:
            if key in os.environ:
                os.environ.pop(key, None)  # 使用 pop 确保完全移除
                print(f"   ✅ 已移除代理环境变量: {key}")
    else:
        # 优先检查 SOCKS5 代理配置
        socks5_proxy = os.getenv("SOCKS5_PROXY", "").strip()
        if use_socks5_proxy and socks5_proxy:
            print(f"✅ 使用 SOCKS5 代理: {socks5_proxy}")
            os.environ['ALL_PROXY'] = socks5_proxy
            os.environ['all_proxy'] = socks5_proxy
            # 验证 pysocks 库是否已安装
            try:
                import socks
                print("✅ pysocks 库已安装，SOCKS5 代理支持完整")
            except ImportError:
                print("⚠️ pysocks 库未安装，SOCKS5 代理可能不工作。请运行: pip install pysocks")
        else:
            # 仅当 USE_PROXY=true 或已显式设置代理环境变量时启用 HTTP 代理
            existing_proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("http_proxy") or os.getenv("https_proxy")
            if use_proxy_flag or existing_proxy:
                # 优先使用已存在的代理环境变量
                proxy_url = existing_proxy or os.getenv("PROXY_URL", "").strip()
                if not proxy_url:
                    # 兼容 PROXY_HOST/PROXY_PORT/PROXY_TYPE（http|https|socks5）组合
                    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1").strip()
                    proxy_port = os.getenv("PROXY_PORT", "").strip()
                    proxy_type = os.getenv("PROXY_TYPE", "http").strip().lower()
                    if proxy_port:
                        proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
                if proxy_url:
                    print(f"✅ 使用代理: {proxy_url}")
                    # 设置环境变量，让 Google API 客户端使用代理
                    os.environ['HTTP_PROXY'] = proxy_url
                    os.environ['HTTPS_PROXY'] = proxy_url
                    os.environ['http_proxy'] = proxy_url
                    os.environ['https_proxy'] = proxy_url
                else:
                    print("⚠️ USE_PROXY=true 但未提供 PROXY_URL/PROXY_HOST/PROXY_PORT，跳过代理配置，使用直连")
            else:
                # 本地开发环境：自动使用默认 HTTP 代理（127.0.0.1:29290）
                # 这保证本地开发时后端能访问 Google API（通过代理）
                proxy_host = os.getenv("PROXY_HOST", "127.0.0.1").strip()
                proxy_port = os.getenv("PROXY_PORT", "29290").strip()
                proxy_type = os.getenv("PROXY_TYPE", "http").strip().lower()
                default_proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
                print(f"✅ 本地开发环境，自动设置代理: {default_proxy_url}")
                os.environ['HTTP_PROXY'] = default_proxy_url
                os.environ['HTTPS_PROXY'] = default_proxy_url
                os.environ['http_proxy'] = default_proxy_url
                os.environ['https_proxy'] = default_proxy_url
                print("💡 如果代理不可用，可设置 DISABLE_PROXY=true 禁用代理")

    # 可选：启动时快速连通性检查（受 CHECK_PROXY_ON_START 控制）
    try:
        if os.getenv("CHECK_PROXY_ON_START", "").lower() == "true":
            import requests as _rq
            _timeout = float(os.getenv("PROXY_CHECK_TIMEOUT", "3"))
            _url = "https://aiplatform.googleapis.com"
            resp = _rq.get(_url, timeout=_timeout)
            print(f"🔌 代理连通性检查成功（{_url} -> {resp.status_code}）")
    except Exception as _e:
        print(f"🟥 代理连通性检查失败：{_e}")
        print("💡 请确认本机代理已启动，或设置 DISABLE_PROXY=true 禁用代理后重试")


def check_proxy_connectivity():
    """
    检查代理连通性（用于 /proxy-health 端点）
    """
    status = {
        "HTTP_PROXY": os.getenv("HTTP_PROXY") or os.getenv("http_proxy"),
        "HTTPS_PROXY": os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
        "PROXY_URL": os.getenv("PROXY_URL"),
        "DISABLE_PROXY": os.getenv("DISABLE_PROXY"),
    }
    try:
        import requests as _rq
        _timeout = float(os.getenv("PROXY_CHECK_TIMEOUT", "5"))
        _url = "https://aiplatform.googleapis.com"
        resp = _rq.get(_url, timeout=_timeout)
        status["connectivity"] = {"ok": True, "status_code": resp.status_code}
        return status
    except Exception as e:
        status["connectivity"] = {"ok": False, "error": str(e)}
        return status
