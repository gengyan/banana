# 文档结构指南

## 📚 根目录文档（核心指南）

### 1. **readme.md**
项目总体介绍，包括：
- 项目概述和功能说明
- 支持的 AI 模型清单
- 前后端架构分工
- 技术栈说明

### 2. **SCRIPTS.md**
所有脚本文件的完整索引和功能说明：
- 启动脚本（start.sh, start-backend.sh, start-frontend.sh）
- 部署脚本（deploy-server.sh, deploy-web.sh, deploy-web-cn.sh, deploy-all.sh）
- 构建脚本和诊断脚本

### 3. **DEPLOY_GUIDE.md**
部署流程完整指南：
- 4 个核心部署脚本详解
- 环境变量配置
- Cloud Run 部署步骤
- 前后端连接配置

### 4. **SERVER_DEPLOYMENT_GUIDE.md**
服务器部署详细指南：
- 国内服务器部署步骤
- 证书和 HTTPS 配置
- 数据库备份策略
- 监控和日志查看

### 5. **PROXY_STARTUP_GUIDE.md**
代理启动和配置指南：
- 代理环境变量配置
- SOCKS5 和 HTTP 代理设置
- 本地开发和 Cloud Run 环境差异

---

## 📋 document/ 目录文档（参考和故障排查）

### 1. **TROUBLESHOOTING.md**
前后端连接问题排查：
- 快速排查步骤
- 常见错误现象
- 日志查看方法
- 网络和端口检查

### 2. **ERRORS.md**
常见错误及解决方案：
- 后端错误（模块导入、API 错误）
- 前端错误（网络错误、组件错误）
- 部署错误

### 3. **DEPLOYMENT_CHECKLIST.md**
部署前检查清单：
- 环境变量检查
- 依赖安装验证
- API 密钥和认证配置
- 网络和防火墙设置

### 4. **PROXY_SETUP.md**
代理配置详细步骤：
- 代理环境变量说明
- 不同系统的配置方法
- 测试代理连接

### 5. **PRIVATE_KEY_GUIDE.md**
私钥和证书管理指南：
- 密钥生成方式
- 密钥存储位置
- 权限设置要求
- 密钥更新流程

### 6. **PAYMENT_TROUBLESHOOTING.md**
支付功能问题排查：
- 支付接口配置
- 常见支付错误
- 测试方法

### 7. **SWITCHYOMEGA_SETUP.md**
浏览器代理工具设置：
- SwitchyOmega 安装
- 代理规则配置
- 验证代理工作

---

## 🗑️ 已删除的文档（历史诊断，问题已解决）

以下文档已清理（保留在 Git 历史中）：
- `DEPLOY_FIX_LOG.md` - 部署脚本历史修复日志
- `LOGIN_401_FIX.md` - 登录认证历史问题
- `BANANA_IMG_ERROR_DIAGNOSIS.md` - 生图接口历史诊断
- `DATABASE_PERSISTENCE_ANALYSIS.md` - 数据库分析报告
- `SECURITY_AUDIT.md` - 安全检查报告
- `IMAGEN_4_IMPLEMENTATION.md` - 实现说明
- `IMAGEN_4_BLOB_ARCHITECTURE.md` - 架构设计文档
- `document/CLOUD_RUN_DEPLOY.md` - 重复内容
- `document/FIX_CORS.md` - 过时的 CORS 诊断
- `document/HISTORY_STORAGE.md` - 历史存储分析
- `document/PAYMENT_NETWORK_ISSUE.md` - 历史支付问题
- `document/ALIPAY_*.md` - 支付网关配置（已停用）
- `.mhtml` 网页快照 - 参考设计文件
- `test_*.py` - 调试测试文件
- `test_output/` - 测试输出目录

---

## 📖 文档使用流程

### 开发环境启动
1. 查阅 **SCRIPTS.md** → 了解脚本功能
2. 使用 `start.sh` 启动服务
3. 遇到问题查阅 **TROUBLESHOOTING.md**

### 部署操作
1. 查阅 **DEPLOY_GUIDE.md** → 选择部署方式
2. 运行对应的部署脚本
3. 使用 **DEPLOYMENT_CHECKLIST.md** 验证部署
4. 问题排查参考 **ERRORS.md**

### 代理和网络配置
1. 根据环境查阅 **PROXY_STARTUP_GUIDE.md**
2. 参考 **PROXY_SETUP.md** 进行详细配置
3. 如需浏览器代理，使用 **SWITCHYOMEGA_SETUP.md**

### 密钥管理
- 参考 **PRIVATE_KEY_GUIDE.md** 管理 API 密钥和证书

### 支付功能问题
- 参考 **PAYMENT_TROUBLESHOOTING.md**

---

## 📝 维护说明

- **更新频率**：文档与代码同步更新
- **归档位置**：删除的诊断文档保留在 Git 历史
- **目标受众**：开发人员、运维人员、部署工程师
