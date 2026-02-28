"""
版本管理配置文件
所有版本号在这个文件中统一管理，避免多处维护
"""

# 应用版本号 (主要版本.次要版本.补丁版本)
APP_VERSION = "1.1.3"

# 使用说明：
# 1. 更新版本号时，仅需修改 APP_VERSION
# 2. 在 FastAPI 中使用：from version import APP_VERSION; FastAPI(..., version=APP_VERSION)
# 3. 在响应中使用：{"version": APP_VERSION}
