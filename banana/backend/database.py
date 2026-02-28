#!/usr/bin/env python3
"""
数据库模块 - SQLite 用户管理
"""

import sqlite3
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
from contextlib import contextmanager
from functools import lru_cache

# 在文件顶部导入 config，避免循环导入问题
from config import MANAGER_ACCOUNT, MANAGER_PASSWORD, MANAGER_NICKNAME, MANAGER_LEVEL

logger = logging.getLogger("数据库")

# 尝试导入 bcrypt，如果未安装则使用 hashlib 作为备用
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    import hashlib
    import secrets
    logger.warning("⚠️  bcrypt 未安装，使用 hashlib 作为备用（安全性较低）")
    logger.warning("   建议安装: pip install bcrypt")

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _use_firestore() -> bool:
    return os.getenv("USE_FIRESTORE", "true").lower() == "true"


@lru_cache(maxsize=1)
def _get_firestore_client():
    import importlib.metadata as _importlib_metadata

    if not hasattr(_importlib_metadata, "packages_distributions"):
        try:
            import importlib_metadata as _importlib_metadata_backport

            def _packages_distributions():
                return _importlib_metadata_backport.packages_distributions()

            setattr(_importlib_metadata, "packages_distributions", _packages_distributions)
        except Exception:
            pass

    from google.cloud import firestore
    from google.oauth2 import service_account

    project_id = (
        os.getenv("FIRESTORE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("VERTEX_AI_PROJECT")
    )
    database_id = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
    credentials_path = (
        os.getenv("FIRESTORE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )

    if not project_id:
        raise ValueError("FIRESTORE_PROJECT_ID 未设置")

    try:
        if credentials_path and os.path.exists(credentials_path):
            creds = service_account.Credentials.from_service_account_file(credentials_path)
            return firestore.Client(project=project_id, credentials=creds, database=database_id)
        
        return firestore.Client(project=project_id, database=database_id)
    except Exception as e:
        logger.error(f"⚠️ Firestore 客户端初始化失败: {e}")
        logger.error(f"   项目: {project_id}, 数据库: {database_id}")
        logger.error("   提示: 确保已在 GCP 项目中创建 Firestore 数据库")
        logger.error("   URL: https://console.cloud.google.com/firestore/databases")
        raise


def _fs_users():
    return _get_firestore_client().collection("users")


def _fs_feedbacks():
    return _get_firestore_client().collection("feedbacks")


def _fs_sessions():
    return _get_firestore_client().collection("sessions")


def _fs_quantity_statistics():
    return _get_firestore_client().collection("quantity_statistics")


def get_db_path():
    """获取数据库文件路径"""
    return DB_PATH


@contextmanager
def get_db_connection():
    """
    获取数据库连接的上下文管理器
    自动处理连接的开启和关闭
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使用 Row 工厂，可以通过列名访问
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """
    初始化数据库，创建表结构
    """
    try:
        if _use_firestore():
            logger.info("✅ Firestore 模式启用，跳过 SQLite 表初始化")
            return
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 创建 users 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    account TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nickname TEXT,
                    avatar TEXT,
                    level TEXT DEFAULT 'normal',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_account ON users(account)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON users(created_at)
            """)
            
            # 创建 feedbacks 表（反馈意见表）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    account TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    reply TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    replied_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 创建反馈表索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedbacks(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_account ON feedbacks(account)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedbacks(created_at)
            """)
            
            # 创建 sessions 表（会话存储表 - 替代内存存储）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 创建会话索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_user_id ON sessions(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_expires_at ON sessions(expires_at)
            """)
            
            logger.info("✅ 数据库表初始化完成")
            
            # 设置数据库文件权限（仅所有者可读写）
            try:
                os.chmod(DB_PATH, 0o600)
                logger.info(f"✅ 数据库文件权限已设置: {DB_PATH}")
            except Exception as e:
                logger.warning(f"⚠️ 设置数据库文件权限失败: {e}")
                
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def hash_password(password: str) -> str:
    """
    加密密码（优先使用 bcrypt，否则使用 SHA256）
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码哈希值
    """
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    else:
        # 备用方案：使用 SHA256（安全性较低，仅用于开发测试）
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256()
        hash_obj.update((password + salt).encode('utf-8'))
        hashed = hash_obj.hexdigest()
        return f"sha256:{salt}:{hashed}"  # 格式：sha256:salt:hash


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        password: 明文密码
        password_hash: 加密后的密码哈希值
        
    Returns:
        是否匹配
    """
    try:
        logger.info(f"🔐 [verify_password] 开始验证密码")
        logger.info(f"   密码长度: {len(password)} 字符")
        logger.info(f"   密码哈希类型: {'bcrypt' if password_hash.startswith('$') else 'sha256' if password_hash.startswith('sha256:') else '未知'}")
        logger.info(f"   密码哈希预览: {password_hash[:50]}...")
        
        if BCRYPT_AVAILABLE:
            logger.info(f"   使用 bcrypt 验证")
            result = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            logger.info(f"   bcrypt 验证结果: {'✅ 匹配' if result else '❌ 不匹配'}")
            return result
        else:
            # 备用方案：SHA256 验证
            logger.info(f"   使用 SHA256 验证（bcrypt 未安装）")
            if not password_hash.startswith('sha256:'):
                logger.error(f"   ❌ 密码哈希格式错误: 不是 sha256 格式")
                return False
            
            try:
                _, salt, stored_hash = password_hash.split(':', 2)
                logger.info(f"   提取 salt: {salt[:10]}...")
                logger.info(f"   存储的哈希: {stored_hash[:20]}...")
                
                hash_obj = hashlib.sha256()
                hash_obj.update((password + salt).encode('utf-8'))
                computed_hash = hash_obj.hexdigest()
                logger.info(f"   计算的哈希: {computed_hash[:20]}...")
                
                result = computed_hash == stored_hash
                logger.info(f"   SHA256 验证结果: {'✅ 匹配' if result else '❌ 不匹配'}")
                if not result:
                    logger.warning(f"   哈希不匹配！")
                    logger.warning(f"   存储的: {stored_hash[:40]}...")
                    logger.warning(f"   计算的: {computed_hash[:40]}...")
                
                return result
            except ValueError as e:
                logger.error(f"   ❌ 解析密码哈希失败: {e}")
                logger.error(f"   密码哈希格式: {password_hash[:100]}")
                return False
    except Exception as e:
        logger.error(f"❌ [verify_password] 密码验证异常: {e}")
        logger.error(f"   异常类型: {type(e).__name__}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        return False


def generate_user_id() -> str:
    """生成用户ID"""
    return f"user_{int(datetime.now().timestamp() * 1000)}_{os.urandom(4).hex()}"


def create_user(
    account: str,
    password: str,
    nickname: Optional[str] = None,
    avatar: Optional[str] = None,
    level: str = 'normal'
) -> Dict:
    """
    创建新用户
    
    Args:
        account: 账号（邮箱或手机号）
        password: 明文密码
        nickname: 昵称
        avatar: 头像
        level: 用户等级
        
    Returns:
        用户信息字典（不包含密码）
    """
    try:
        if _use_firestore():
            # 检查账号是否已存在
            existing = _fs_users().where("account", "==", account).limit(1).stream()
            if next(existing, None):
                raise ValueError(f"账号 {account} 已被注册")

            user_id = generate_user_id()
            password_hash = hash_password(password)

            if not nickname:
                nickname = account.split('@')[0] if '@' in account else account[:3] + '***'

            now = datetime.now().isoformat()
            data = {
                "id": user_id,
                "account": account,
                "password_hash": password_hash,
                "nickname": nickname,
                "avatar": avatar,
                "level": level,
                "created_at": now,
                "updated_at": now,
            }
            _fs_users().document(user_id).set(data)

            logger.info(f"✅ 用户创建成功: {account} (ID: {user_id})")
            return {
                'id': user_id,
                'account': account,
                'nickname': nickname,
                'avatar': avatar,
                'level': level,
                'createdAt': now,
                'updatedAt': now
            }

        # 检查账号是否已存在
        existing_user = get_user_by_account(account)
        if existing_user:
            raise ValueError(f"账号 {account} 已被注册")
        
        # 生成用户ID
        user_id = generate_user_id()
        
        # 加密密码
        password_hash = hash_password(password)
        
        # 设置默认昵称
        if not nickname:
            nickname = account.split('@')[0] if '@' in account else account[:3] + '***'
        
        # 创建时间
        now = datetime.now().isoformat()
        
        # 插入数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, account, password_hash, nickname, avatar, level, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, account, password_hash, nickname, avatar, level, now, now))
            
            logger.info(f"✅ 用户创建成功: {account} (ID: {user_id})")
        
        # 返回用户信息（不包含密码）
        return {
            'id': user_id,
            'account': account,
            'nickname': nickname,
            'avatar': avatar,
            'level': level,
            'createdAt': now,
            'updatedAt': now
        }
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    根据用户ID获取用户信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        用户信息字典（不包含密码），如果不存在返回 None
    """
    try:
        if _use_firestore():
            doc = _fs_users().document(user_id).get()
            if not doc.exists:
                return None
            row = doc.to_dict() or {}
            return {
                'id': row.get('id') or user_id,
                'account': row.get('account'),
                'nickname': row.get('nickname'),
                'avatar': row.get('avatar'),
                'level': row.get('level'),
                'createdAt': row.get('created_at'),
                'updatedAt': row.get('updated_at')
            }
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'account': row['account'],
                    'nickname': row['nickname'],
                    'avatar': row['avatar'],
                    'level': row['level'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at']
                }
            return None
            
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        return None


def get_user_by_account(account: str) -> Optional[Dict]:
    """
    根据账号获取用户信息（包含密码哈希，用于登录验证）
    
    Args:
        account: 账号
        
    Returns:
        用户信息字典（包含密码哈希），如果不存在返回 None
    """
    try:
        if _use_firestore():
            docs = _fs_users().where("account", "==", account).limit(1).stream()
            doc = next(docs, None)
            if not doc:
                return None
            row = doc.to_dict() or {}
            return {
                'id': row.get('id') or doc.id,
                'account': row.get('account'),
                'password_hash': row.get('password_hash'),
                'nickname': row.get('nickname'),
                'avatar': row.get('avatar'),
                'level': row.get('level'),
                'createdAt': row.get('created_at'),
                'updatedAt': row.get('updated_at')
            }
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE account = ?", (account,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'account': row['account'],
                    'password_hash': row['password_hash'],  # 包含密码哈希（用于验证）
                    'nickname': row['nickname'],
                    'avatar': row['avatar'],
                    'level': row['level'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at']
                }
            return None
            
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        return None


def verify_user_login(account: str, password: str) -> Optional[Dict]:
    """
    验证用户登录
    
    Args:
        account: 账号
        password: 明文密码
        
    Returns:
        用户信息字典（不包含密码），如果验证失败返回 None
    """
    try:
        logger.info(f"🔍 [verify_user_login] 开始验证: 账号={account}, 密码长度={len(password)}")
        
        user = get_user_by_account(account)
        if not user:
            logger.warning(f"❌ [verify_user_login] 登录失败: 账号 {account} 不存在")
            return None
        
        logger.info(f"✅ [verify_user_login] 找到用户: ID={user['id']}, 账号={user['account']}")
        logger.info(f"   密码哈希类型: {'bcrypt' if user['password_hash'].startswith('$') else 'sha256' if user['password_hash'].startswith('sha256:') else '未知'}")
        logger.info(f"   密码哈希预览: {user['password_hash'][:50]}...")
        
        # 验证密码
        logger.info(f"🔐 [verify_user_login] 开始验证密码...")
        password_match = verify_password(password, user['password_hash'])
        logger.info(f"   密码验证结果: {'✅ 匹配' if password_match else '❌ 不匹配'}")
        
        if not password_match:
            logger.warning(f"❌ [verify_user_login] 登录失败: 账号 {account} 密码错误")
            logger.warning(f"   输入的密码长度: {len(password)}")
            logger.warning(f"   密码哈希类型: {'bcrypt' if user['password_hash'].startswith('$') else 'sha256' if user['password_hash'].startswith('sha256:') else '未知'}")
            return None
        
        # 返回用户信息（不包含密码）
        user_without_password = {
            'id': user['id'],
            'account': user['account'],
            'nickname': user['nickname'],
            'avatar': user['avatar'],
            'level': user['level'],
            'createdAt': user['createdAt'],
            'updatedAt': user['updatedAt']
        }
        
        logger.info(f"✅ 用户登录成功: {account}")
        return user_without_password
        
    except Exception as e:
        logger.error(f"验证登录失败: {e}")
        return None


def update_user(user_id: str, updates: Dict) -> Optional[Dict]:
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        updates: 要更新的字段字典（支持：nickname, avatar, level）
        
    Returns:
        更新后的用户信息字典（不包含密码），如果失败返回 None
    """
    try:
        if _use_firestore():
            user = get_user_by_id(user_id)
            if not user:
                raise ValueError(f"用户 {user_id} 不存在")

            allowed_fields = ['nickname', 'avatar', 'level', 'password_hash']
            payload = {k: updates[k] for k in allowed_fields if k in updates}
            if not payload:
                return user

            payload['updated_at'] = datetime.now().isoformat()
            _fs_users().document(user_id).set(payload, merge=True)
            logger.info(f"✅ 用户信息更新成功: {user_id}")
            return get_user_by_id(user_id)

        # 检查用户是否存在
        user = get_user_by_id(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        # 构建更新语句
        allowed_fields = ['nickname', 'avatar', 'level', 'password_hash']
        set_clauses = []
        values = []
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = ?")
                values.append(updates[field])
        
        if not set_clauses:
            return user  # 没有要更新的字段
        
        # 添加更新时间
        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(user_id)  # WHERE 条件的值
        
        # 执行更新
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, values)
            
            logger.info(f"✅ 用户信息更新成功: {user_id}")
        
        # 返回更新后的用户信息
        return get_user_by_id(user_id)
        
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        return None


def get_all_users() -> List[Dict]:
    """
    获取所有用户列表（管理员功能）
    
    Returns:
        用户信息列表（不包含密码）
    """
    try:
        if _use_firestore():
            docs = _fs_users().order_by("created_at", direction="DESCENDING").stream()
            users = []
            for doc in docs:
                row = doc.to_dict() or {}
                users.append({
                    'id': row.get('id') or doc.id,
                    'account': row.get('account'),
                    'nickname': row.get('nickname'),
                    'avatar': row.get('avatar'),
                    'level': row.get('level'),
                    'createdAt': row.get('created_at'),
                    'updatedAt': row.get('updated_at')
                })
            return users
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, account, nickname, avatar, level, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    'id': row['id'],
                    'account': row['account'],
                    'nickname': row['nickname'],
                    'avatar': row['avatar'],
                    'level': row['level'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at']
                })
            
            return users
            
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return []


def create_manager_account(account: str = None, password: str = None, nickname: str = None, level: str = None):
    """
    创建管理员账号
    
    参数从 config 模块获取，可通过环境变量覆盖。
    
    Args:
        account: 管理员账号（默认从 config.MANAGER_ACCOUNT 获取）
        password: 管理员密码（默认从 config.MANAGER_PASSWORD 获取）
        nickname: 管理员昵称（默认从 config.MANAGER_NICKNAME 获取）
        level: 管理员级别（默认从 config.MANAGER_LEVEL 获取）
        
    Raises:
        ValueError: 如果必要参数未提供或密码未设置
    """
    # 使用参数或从配置获取默认值
    account = account or MANAGER_ACCOUNT
    password = password or MANAGER_PASSWORD
    nickname = nickname or MANAGER_NICKNAME
    level = level or MANAGER_LEVEL
    
    try:
        # 验证必要参数
        if not password:
            logger.warning(
                "⚠️  管理员密码未设置，跳过创建管理员账号\n"
                "   如需创建管理员账号，请设置环境变量: export MANAGER_PASSWORD='your_secure_password'"
            )
            # 检查是否已有管理员账号（仅用于日志记录）
            existing = get_user_by_account(account)
            if existing:
                logger.info(f"ℹ️  管理员账号 '{account}' 已存在")
            return None
        
        # 检查账号是否已存在
        existing = get_user_by_account(account)
        if existing:
            logger.info(f"ℹ️  管理员账号 '{account}' 已存在，跳过创建")
            return existing
        
        # 创建管理员账号
        manager = create_user(
            account=account,
            password=password,
            nickname=nickname,
            level=level
        )
        
        logger.info(f"✅ 管理员账号创建成功")
        logger.info(f"   账号: {account}")
        logger.info(f"   昵称: {nickname}")
        logger.info(f"   级别: {level}")
        logger.info(f"   用户ID: {manager['id']}")
        
        return manager
        
    except Exception as e:
        logger.error(f"创建管理员账号失败: {e}")
        raise


# ==================== 反馈相关函数 ====================

def generate_feedback_id() -> str:
    """生成反馈ID"""
    return f"feedback_{int(datetime.now().timestamp() * 1000)}_{os.urandom(4).hex()}"


def create_feedback(
    user_id: str,
    account: str,
    feedback: str,
    contact: str
) -> Dict:
    """
    创建反馈记录
    
    Args:
        user_id: 用户ID
        account: 用户账号
        feedback: 反馈内容
        contact: 联系方式
        
    Returns:
        反馈信息字典
    """
    try:
        if _use_firestore():
            feedback_id = generate_feedback_id()
            now = datetime.now().isoformat()
            data = {
                "id": feedback_id,
                "user_id": user_id,
                "account": account,
                "feedback": feedback,
                "contact": contact,
                "reply": None,
                "created_at": now,
                "updated_at": now,
                "replied_at": None,
            }
            _fs_feedbacks().document(feedback_id).set(data)
            logger.info(f"✅ 反馈创建成功: {feedback_id} (用户: {account})")
            return {
                'id': feedback_id,
                'user_id': user_id,
                'account': account,
                'feedback': feedback,
                'contact': contact,
                'reply': None,
                'createdAt': now,
                'updatedAt': now,
                'repliedAt': None
            }
        feedback_id = generate_feedback_id()
        now = datetime.now().isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedbacks (id, user_id, account, feedback, contact, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (feedback_id, user_id, account, feedback, contact, now, now))
            
            logger.info(f"✅ 反馈创建成功: {feedback_id} (用户: {account})")
        
        return {
            'id': feedback_id,
            'user_id': user_id,
            'account': account,
            'feedback': feedback,
            'contact': contact,
            'reply': None,
            'createdAt': now,
            'updatedAt': now,
            'repliedAt': None
        }
        
    except Exception as e:
        logger.error(f"创建反馈失败: {e}")
        raise


def get_feedbacks_by_user_id(user_id: str) -> List[Dict]:
    """
    获取指定用户的所有反馈记录
    
    Args:
        user_id: 用户ID
        
    Returns:
        反馈记录列表
    """
    try:
        if _use_firestore():
            docs = (
                _fs_feedbacks()
                .where("user_id", "==", user_id)
                .order_by("created_at", direction="DESCENDING")
                .stream()
            )
            feedbacks = []
            for doc in docs:
                row = doc.to_dict() or {}
                feedbacks.append({
                    'id': row.get('id') or doc.id,
                    'user_id': row.get('user_id'),
                    'account': row.get('account'),
                    'feedback': row.get('feedback'),
                    'contact': row.get('contact'),
                    'reply': row.get('reply'),
                    'createdAt': row.get('created_at'),
                    'updatedAt': row.get('updated_at'),
                    'repliedAt': row.get('replied_at')
                })
            return feedbacks
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feedbacks
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            
            feedbacks = []
            for row in rows:
                feedbacks.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'account': row['account'],
                    'feedback': row['feedback'],
                    'contact': row['contact'],
                    'reply': row['reply'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at'],
                    'repliedAt': row['replied_at']
                })
            
            return feedbacks
            
    except Exception as e:
        logger.error(f"获取用户反馈失败: {e}")
        return []


def get_all_feedbacks() -> List[Dict]:
    """
    获取所有反馈记录（管理员功能）
    
    Returns:
        反馈记录列表
    """
    try:
        if _use_firestore():
            docs = _fs_feedbacks().order_by("created_at", direction="DESCENDING").stream()
            feedbacks = []
            for doc in docs:
                row = doc.to_dict() or {}
                feedbacks.append({
                    'id': row.get('id') or doc.id,
                    'user_id': row.get('user_id'),
                    'account': row.get('account'),
                    'feedback': row.get('feedback'),
                    'contact': row.get('contact'),
                    'reply': row.get('reply'),
                    'createdAt': row.get('created_at'),
                    'updatedAt': row.get('updated_at'),
                    'repliedAt': row.get('replied_at')
                })
            return feedbacks
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feedbacks
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            
            feedbacks = []
            for row in rows:
                feedbacks.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'account': row['account'],
                    'feedback': row['feedback'],
                    'contact': row['contact'],
                    'reply': row['reply'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at'],
                    'repliedAt': row['replied_at']
                })
            
            return feedbacks
            
    except Exception as e:
        logger.error(f"获取所有反馈失败: {e}")
        return []


def get_feedback_by_id(feedback_id: str) -> Optional[Dict]:
    """
    根据反馈ID获取反馈记录
    
    Args:
        feedback_id: 反馈ID
        
    Returns:
        反馈信息字典，如果不存在返回 None
    """
    try:
        if _use_firestore():
            doc = _fs_feedbacks().document(feedback_id).get()
            if not doc.exists:
                return None
            row = doc.to_dict() or {}
            return {
                'id': row.get('id') or doc.id,
                'user_id': row.get('user_id'),
                'account': row.get('account'),
                'feedback': row.get('feedback'),
                'contact': row.get('contact'),
                'reply': row.get('reply'),
                'createdAt': row.get('created_at'),
                'updatedAt': row.get('updated_at'),
                'repliedAt': row.get('replied_at')
            }
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedbacks WHERE id = ?", (feedback_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'account': row['account'],
                    'feedback': row['feedback'],
                    'contact': row['contact'],
                    'reply': row['reply'],
                    'createdAt': row['created_at'],
                    'updatedAt': row['updated_at'],
                    'repliedAt': row['replied_at']
                }
            return None
            
    except Exception as e:
        logger.error(f"获取反馈失败: {e}")
        return None


def update_feedback_reply(feedback_id: str, reply: str) -> Optional[Dict]:
    """
    更新反馈的回复内容（管理员功能）
    
    Args:
        feedback_id: 反馈ID
        reply: 回复内容
        
    Returns:
        更新后的反馈信息字典，如果失败返回 None
    """
    try:
        if _use_firestore():
            feedback = get_feedback_by_id(feedback_id)
            if not feedback:
                raise ValueError(f"反馈 {feedback_id} 不存在")
            now = datetime.now().isoformat()
            _fs_feedbacks().document(feedback_id).set({
                "reply": reply,
                "replied_at": now,
                "updated_at": now,
            }, merge=True)
            logger.info(f"✅ 反馈回复更新成功: {feedback_id}")
            return get_feedback_by_id(feedback_id)
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            raise ValueError(f"反馈 {feedback_id} 不存在")
        
        now = datetime.now().isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feedbacks
                SET reply = ?, replied_at = ?, updated_at = ?
                WHERE id = ?
            """, (reply, now, now, feedback_id))
            
            logger.info(f"✅ 反馈回复更新成功: {feedback_id}")
        
        return get_feedback_by_id(feedback_id)
        
    except Exception as e:
        logger.error(f"更新反馈回复失败: {e}")
        return None


def get_user_feedback_count(user_id: str) -> int:
    """
    获取用户的反馈数量
    
    Args:
        user_id: 用户ID
        
    Returns:
        反馈数量
    """
    try:
        if _use_firestore():
            docs = _fs_feedbacks().where("user_id", "==", user_id).stream()
            return sum(1 for _ in docs)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM feedbacks WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row['count'] if row else 0
    except Exception as e:
        logger.error(f"获取用户反馈数量失败: {e}")
        return 0


def increment_quantity_statistics(account: str, date_str: Optional[str] = None, request_type: Optional[str] = None) -> bool:
    """
    记录某账号某天的请求次数（Firestore: quantity_statistics）。

    Args:
        account: 登录账号
        date_str: 日期字符串 (YYYY-MM-DD)，默认使用本地日期
        request_type: 请求类型（可选，记录最后一次请求类型）

    Returns:
        True 表示写入成功，False 表示失败或未启用 Firestore
    """
    if not account:
        return False

    if not date_str:
        date_str = datetime.now().date().isoformat()

    if not _use_firestore():
        logger.warning("⚠️ Firestore 未启用，数量统计跳过")
        return False

    try:
        from google.cloud import firestore

        doc_id = f"{account}_{date_str}"
        doc_ref = _fs_quantity_statistics().document(doc_id)
        now = datetime.now().isoformat()

        @firestore.transactional
        def _update(transaction):
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                update_payload = {
                    "count": firestore.Increment(1),
                    "updated_at": now,
                }
                if request_type:
                    update_payload["last_request_type"] = request_type
                transaction.update(doc_ref, update_payload)
            else:
                data = {
                    "account": account,
                    "date": date_str,
                    "count": 1,
                    "created_at": now,
                    "updated_at": now,
                }
                if request_type:
                    data["last_request_type"] = request_type
                transaction.set(doc_ref, data)

        transaction = _get_firestore_client().transaction()
        _update(transaction)
        logger.info(f"✅ 数量统计更新成功: {account} {date_str}")
        return True
    except Exception as e:
        logger.error(f"❌ 数量统计更新失败: {e}")
        return False

# ==================== 会话管理函数 ====================

def create_session(session_token: str, user_id: str, expires_at: str) -> bool:
    """
    创建会话记录（数据库持久化）
    
    Args:
        session_token: 会话令牌
        user_id: 用户ID
        expires_at: 过期时间
        
    Returns:
        创建成功返回 True，失败返回 False
    """
    try:
        if _use_firestore():
            created_at = datetime.now().isoformat()
            data = {
                "session_token": session_token,
                "user_id": user_id,
                "created_at": created_at,
                "expires_at": expires_at,
            }
            _fs_sessions().document(session_token).set(data)
            logger.info(f"✅ 会话创建成功: {session_token[:20]}... (user_id: {user_id})")
            return True
        created_at = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (session_token, user_id, created_at, expires_at))
            logger.info(f"✅ 会话创建成功: {session_token[:20]}... (user_id: {user_id})")
        return True
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        return False


def get_user_from_session(session_token: str) -> Optional[Dict]:
    """
    从会话令牌获取用户信息
    
    Args:
        session_token: 会话令牌
        
    Returns:
        用户信息字典，如果无效返回 None
    """
    try:
        if _use_firestore():
            now = datetime.now().isoformat()
            doc = _fs_sessions().document(session_token).get()
            if not doc.exists:
                logger.warning(f"⚠️ 会话无效或已过期: {session_token[:20]}...")
                return None
            data = doc.to_dict() or {}
            if data.get("expires_at") and data.get("expires_at") <= now:
                logger.warning(f"⚠️ 会话无效或已过期: {session_token[:20]}...")
                return None
            user_id = data.get("user_id")
            user = get_user_by_id(user_id) if user_id else None
            if user:
                logger.info(f"✅ 从会话获取用户: {user.get('account')} (session: {session_token[:20]}...)")
            else:
                logger.warning(f"⚠️ 用户不存在: {user_id}")
            return user
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 查询会话
            cursor.execute("""
                SELECT user_id, expires_at FROM sessions 
                WHERE session_token = ? AND expires_at > ?
            """, (session_token, now))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"⚠️ 会话无效或已过期: {session_token[:20]}...")
                return None
            
            user_id = row['user_id']
            
            # 获取用户信息
            user = get_user_by_id(user_id)
            if user:
                logger.info(f"✅ 从会话获取用户: {user.get('account')} (session: {session_token[:20]}...)")
            else:
                logger.warning(f"⚠️ 用户不存在: {user_id}")
            
            return user
            
    except Exception as e:
        logger.error(f"从会话获取用户失败: {e}")
        return None


def delete_session(session_token: str) -> bool:
    """
    删除会话记录（用户登出）
    
    Args:
        session_token: 会话令牌
        
    Returns:
        删除成功返回 True，失败返回 False
    """
    try:
        if _use_firestore():
            _fs_sessions().document(session_token).delete()
            logger.info(f"✅ 会话删除成功: {session_token[:20]}...")
            return True
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            logger.info(f"✅ 会话删除成功: {session_token[:20]}...")
        return True
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return False


def delete_expired_sessions() -> int:
    """
    清理过期的会话记录
    
    Returns:
        删除的会话数量
    """
    try:
        if _use_firestore():
            now = datetime.now().isoformat()
            docs = _fs_sessions().where("expires_at", "<=", now).stream()
            count = 0
            batch = _get_firestore_client().batch()
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count % 400 == 0:
                    batch.commit()
                    batch = _get_firestore_client().batch()
            if count % 400 != 0:
                batch.commit()
            logger.info(f"✅ 清理过期会话: 删除 {count} 条记录")
            return count
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            deleted = cursor.rowcount
            logger.info(f"✅ 清理过期会话: 删除 {deleted} 条记录")
        return deleted
    except Exception as e:
        logger.error(f"清理过期会话失败: {e}")
        return 0
