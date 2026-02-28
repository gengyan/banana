#!/usr/bin/env python3
"""
将 SQLite users.db 迁移到 Firestore（banana-db）。

使用方式：
  FIRESTORE_SERVICE_ACCOUNT_JSON=/path/to/key.json \
  python3 migrate_sqlite_to_firestore.py

可选参数：
  --db /path/to/users.db
  --project your-gcp-project-id
  --dry-run
"""
import importlib.metadata as _importlib_metadata

# 兼容 Python 3.9 缺失 packages_distributions
if not hasattr(_importlib_metadata, "packages_distributions"):
    try:
        import importlib_metadata as _importlib_metadata_backport

        def _packages_distributions():
            return _importlib_metadata_backport.packages_distributions()

        setattr(_importlib_metadata, "packages_distributions", _packages_distributions)
    except Exception:
        pass
import argparse
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Iterable, List, Optional, Sequence

from google.cloud import firestore
from google.cloud.firestore_v1 import _helpers, types
from google.cloud.firestore_v1.services.firestore import FirestoreClient
from google.oauth2 import service_account

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _load_firestore_client(project_id: Optional[str], credentials_path: Optional[str], database_id: Optional[str]):
    if credentials_path:
        creds = service_account.Credentials.from_service_account_file(credentials_path)
        return firestore.Client(project=project_id, credentials=creds, database=database_id)
    return firestore.Client(project=project_id, database=database_id)


def _load_firestore_rest_client(credentials_path: str) -> FirestoreClient:
    creds = service_account.Credentials.from_service_account_file(credentials_path)
    return FirestoreClient(credentials=creds, transport="rest")


def _encode_fields(data: Dict[str, Any]) -> Dict[str, types.Value]:
    fields: Dict[str, types.Value] = {}
    for key, value in data.items():
        fields[key] = _helpers.encode_value(value)
    return fields


def _commit_rest(
    client: FirestoreClient,
    project_id: str,
    database_id: str,
    collection_name: str,
    rows: Sequence[sqlite3.Row],
    id_field: str,
):
    database_path = f"projects/{project_id}/databases/{database_id}"
    writes: List[types.Write] = []

    for row in rows:
        data = _row_to_dict(row)
        doc_id = data.get(id_field)
        if not doc_id:
            continue
        data["_migrated_at"] = datetime.utcnow().isoformat()
        doc_name = f"{database_path}/documents/{collection_name}/{doc_id}"
        document = types.Document(name=doc_name, fields=_encode_fields(data))
        writes.append(types.Write(update=document))

    if not writes:
        return

    client.commit(request={"database": database_path, "writes": writes})


def _fetch_all(conn: sqlite3.Connection, sql: str) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _batched(items: Iterable[Dict[str, Any]], batch_size: int = 500):
    batch: List[Dict[str, Any]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def migrate_collection(
    client: firestore.Client,
    collection_name: str,
    rows: List[sqlite3.Row],
    id_field: str,
    dry_run: bool,
):
    total = len(rows)
    print(f"📦 迁移集合 {collection_name}: {total} 条")
    if total == 0:
        return

    for batch_rows in _batched(rows, 500):
        if dry_run:
            continue
        batch = client.batch()
        for row in batch_rows:
            data = _row_to_dict(row)
            doc_id = data.get(id_field)
            if not doc_id:
                continue
            data["_migrated_at"] = datetime.utcnow().isoformat()
            doc_ref = client.collection(collection_name).document(str(doc_id))
            batch.set(doc_ref, data, merge=True)
        batch.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite 数据库路径")
    parser.add_argument("--project", default=os.getenv("FIRESTORE_PROJECT_ID"), help="GCP Project ID")
    parser.add_argument("--database", default=os.getenv("FIRESTORE_DATABASE_ID", "(default)"), help="Firestore database ID")
    parser.add_argument(
        "--transport",
        default=os.getenv("FIRESTORE_TRANSPORT", "grpc"),
        choices=["grpc", "rest"],
        help="Firestore 传输协议（grpc 或 rest）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写入")
    args = parser.parse_args()

    credentials_path = os.getenv("FIRESTORE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        print("❌ 未提供 Firestore 服务账号 JSON。请设置 FIRESTORE_SERVICE_ACCOUNT_JSON 或 GOOGLE_APPLICATION_CREDENTIALS")
        return

    if not os.path.exists(args.db):
        print(f"❌ SQLite 数据库不存在: {args.db}")
        return

    if not args.project:
        print("❌ 未提供 FIRESTORE_PROJECT_ID")
        return

    use_rest = args.transport == "rest"
    client = _load_firestore_client(args.project, credentials_path, args.database) if not use_rest else None
    rest_client = _load_firestore_rest_client(credentials_path) if use_rest else None

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        users = _fetch_all(conn, "SELECT * FROM users")
        feedbacks = _fetch_all(conn, "SELECT * FROM feedbacks")
        sessions = _fetch_all(conn, "SELECT * FROM sessions")

        if use_rest:
            if not args.dry_run:
                for batch_rows in _batched(users, 500):
                    _commit_rest(rest_client, args.project, args.database, "users", batch_rows, "id")
                for batch_rows in _batched(feedbacks, 500):
                    _commit_rest(rest_client, args.project, args.database, "feedbacks", batch_rows, "id")
                for batch_rows in _batched(sessions, 500):
                    _commit_rest(rest_client, args.project, args.database, "sessions", batch_rows, "session_token")
            else:
                print(f"📦 迁移集合 users: {len(users)} 条")
                print(f"📦 迁移集合 feedbacks: {len(feedbacks)} 条")
                print(f"📦 迁移集合 sessions: {len(sessions)} 条")
        else:
            migrate_collection(client, "users", users, "id", args.dry_run)
            migrate_collection(client, "feedbacks", feedbacks, "id", args.dry_run)
            migrate_collection(client, "sessions", sessions, "session_token", args.dry_run)

        print("✅ 迁移完成")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
