# 数据库持久化问题分析与解决方案

## 📊 当前状况分析

### ❌ 问题确认：**是的，每次部署会完全覆盖数据库文件**

#### 1. 数据库配置
- **类型**: SQLite (`users.db`)
- **位置**: `/app/users.db` (容器内)
- **大小**: ~80KB (本地)
- **存储**: 存储在容器的文件系统中

#### 2. 部署流程分析

```bash
# 当前部署命令 (deploy-backend-cloud.sh)
gcloud run deploy backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed \
  --timeout 10m \
  --memory 2Gi
```

**Dockerfile 构建过程:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .              # ⚠️ 复制所有文件，包括 users.db
CMD ["./start.sh"]
```

#### 3. 问题根源

Cloud Run 的特性：
- ✅ **无状态设计**: 每个实例都是临时的
- ❌ **无持久化存储**: 容器文件系统是临时的
- ❌ **重启丢失**: 容器重启、扩缩容、部署时所有数据丢失
- ❌ **副本不同步**: 多个实例之间数据不共享

**结果:**
1. 每次部署 → 构建新镜像 → 包含旧的/空的 `users.db`
2. 运行时写入的数据 → 仅存在于该容器实例
3. 下次部署/重启 → **所有用户数据丢失**

---

## 🎯 解决方案对比

### 方案1: Cloud SQL (PostgreSQL/MySQL) ⭐⭐⭐⭐⭐
**推荐用于生产环境**

#### 优点
- ✅ 完全托管的数据库服务
- ✅ 自动备份和高可用
- ✅ 可扩展性强
- ✅ 支持并发访问
- ✅ 数据完全持久化

#### 缺点
- ❌ 需要修改代码 (SQLite → PostgreSQL/MySQL)
- ❌ 有运行成本 (~$10-50/月)
- ❌ 配置相对复杂

#### 实施步骤
```bash
# 1. 创建 Cloud SQL 实例
gcloud sql instances create banana-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-southeast1

# 2. 创建数据库和用户
gcloud sql databases create banana --instance=banana-db

# 3. 部署时连接 Cloud SQL
gcloud run deploy backend \
  --add-cloudsql-instances=PROJECT_ID:asia-southeast1:banana-db
```

---

### 方案2: Firestore (NoSQL) ⭐⭐⭐⭐
**推荐用于中等规模应用**

#### 优点
- ✅ Google Cloud 原生数据库
- ✅ 无需管理服务器
- ✅ 实时同步支持
- ✅ 按使用量付费
- ✅ 免费额度充足

#### 缺点
- ❌ 需要重写数据库逻辑
- ❌ NoSQL 不支持复杂查询
- ❌ 学习成本

#### 实施步骤
```python
# 使用 Firestore SDK
from google.cloud import firestore
db = firestore.Client()
```

---

### 方案3: Cloud Storage + SQLite (混合) ⭐⭐⭐
**适合小型应用，快速迁移**

#### 优点
- ✅ 保持 SQLite，代码改动最小
- ✅ 利用 Cloud Storage 持久化
- ✅ 成本极低 (~$0.01/月)
- ✅ 实施快速

#### 缺点
- ❌ 并发性能差（读写需要同步）
- ❌ 不适合高流量
- ❌ 需要处理文件锁

#### 实施方案
```python
# 启动时从 Cloud Storage 下载数据库
# 运行时使用本地 SQLite
# 定期上传到 Cloud Storage
```

---

### 方案4: Cloud SQL Proxy + SQLite (不推荐) ⭐⭐
**技术上可行但不实用**

Cloud Run 不支持持久卷挂载，此方案不适用。

---

## 💡 推荐方案

### 立即实施 (方案3): Cloud Storage + SQLite

**为什么选择这个方案:**
1. **最小改动**: 保持现有 SQLite 代码
2. **快速上线**: 1-2小时即可完成
3. **低成本**: 几乎免费
4. **适合当前规模**: 10-100 个用户没问题

**实施步骤:**

#### 步骤1: 创建 Cloud Storage Bucket
```bash
gsutil mb -l asia-southeast1 gs://banana-database-backup
```

#### 步骤2: 修改代码添加同步逻辑
```python
# database.py 添加
from google.cloud import storage
import atexit

DB_BUCKET = "banana-database-backup"
DB_BLOB_NAME = "users.db"

def download_db_from_storage():
    """启动时从 Cloud Storage 下载数据库"""
    try:
        client = storage.Client()
        bucket = client.bucket(DB_BUCKET)
        blob = bucket.blob(DB_BLOB_NAME)
        
        if blob.exists():
            blob.download_to_filename(DB_PATH)
            print(f"✅ 数据库已从 Cloud Storage 恢复")
        else:
            print(f"ℹ️ Cloud Storage 中无数据库，使用新数据库")
    except Exception as e:
        print(f"⚠️ 下载数据库失败: {e}")

def upload_db_to_storage():
    """定期上传数据库到 Cloud Storage"""
    try:
        client = storage.Client()
        bucket = client.bucket(DB_BUCKET)
        blob = bucket.blob(DB_BLOB_NAME)
        blob.upload_from_filename(DB_PATH)
        print(f"✅ 数据库已备份到 Cloud Storage")
    except Exception as e:
        print(f"⚠️ 上传数据库失败: {e}")

# 启动时下载
download_db_from_storage()

# 关闭时上传
atexit.register(upload_db_to_storage)

# 定期上传（每5分钟）
import threading
def periodic_backup():
    while True:
        time.sleep(300)  # 5分钟
        upload_db_to_storage()

threading.Thread(target=periodic_backup, daemon=True).start()
```

#### 步骤3: 更新依赖
```bash
# requirements.txt 添加
google-cloud-storage>=2.10.0
```

#### 步骤4: 配置权限
```bash
# 给 Cloud Run 服务账号添加 Storage 权限
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

#### 步骤5: 重新部署
```bash
bash deploy-backend-cloud.sh
```

---

### 长期规划 (方案1): 迁移到 Cloud SQL

当用户量增长时 (>100 用户)，迁移到 Cloud SQL：

```python
# 使用 SQLAlchemy 支持多数据库
from sqlalchemy import create_engine

# PostgreSQL
DATABASE_URL = "postgresql://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE"
engine = create_engine(DATABASE_URL)
```

---

## 📋 行动清单

### 🔴 紧急 (本周内完成)
- [ ] 实施方案3: Cloud Storage 备份
- [ ] 测试数据持久化
- [ ] 验证部署后数据不丢失

### 🟡 重要 (本月内完成)
- [ ] 设置自动备份计划
- [ ] 监控备份状态
- [ ] 文档化恢复流程

### 🟢 长期 (根据需要)
- [ ] 评估迁移到 Cloud SQL
- [ ] 性能测试和优化
- [ ] 设置告警和监控

---

## ⚠️ 当前风险

### 1. 数据丢失风险
**严重度**: 🔴 高
- 每次部署丢失所有用户数据
- 容器重启丢失数据
- 无备份恢复机制

### 2. 并发问题
**严重度**: 🟡 中
- 多个 Cloud Run 实例可能使用不同数据库副本
- 数据不一致

### 3. 扩展性限制
**严重度**: 🟢 低
- SQLite 不适合高并发
- 但当前规模可接受

---

## 💰 成本估算

| 方案 | 月成本 | 说明 |
|------|--------|------|
| Cloud Storage | ~$0.01 | 80KB 存储 + 少量传输 |
| Firestore | $0-5 | 免费额度内 |
| Cloud SQL (f1-micro) | ~$10 | 最小实例 |
| Cloud SQL (db-n1-standard-1) | ~$50 | 生产级 |

---

## 🎓 学习资源

- [Cloud Run 持久化存储最佳实践](https://cloud.google.com/run/docs/tutorials/cloud-sql)
- [Cloud Storage Python 客户端](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)
- [Firestore 快速入门](https://firebase.google.com/docs/firestore/quickstart)

---

## 总结

✅ **立即行动**: 实施 Cloud Storage 备份方案  
📅 **计划**: 2-3 个月后评估 Cloud SQL 迁移  
🎯 **目标**: 确保数据永不丢失
