import os
import warnings
from typing import List, Dict, Any

import aiomysql
import pymysql
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=pymysql.Warning)

load_dotenv()

_pool = None


async def init_db():
    global _pool
    _pool = await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        db=os.getenv("MYSQL_DATABASE", "smartmail"),
        charset="utf8mb4",
        autocommit=True,
    )
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SET SESSION sql_notes = 0")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS email_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email_id (email_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) NOT NULL UNIQUE,
                    `from` VARCHAR(500) NOT NULL,
                    original_subject VARCHAR(500) NOT NULL,
                    body TEXT NOT NULL,
                    reply_draft TEXT NOT NULL,
                    classification VARCHAR(50) NOT NULL DEFAULT 'unknown',
                    sent TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_pe_email_id (email_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # 兼容旧表：不存在 body 列则添加
            try:
                await cur.execute("ALTER TABLE processed_emails ADD COLUMN body TEXT NOT NULL AFTER original_subject")
            except Exception:
                pass
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            await cur.execute("SET SESSION sql_notes = 1")


async def close_db():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()


async def get_history(email_id: str) -> List[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT role, content FROM email_history WHERE email_id = %s ORDER BY created_at ASC",
                (email_id,),
            )
            rows = await cur.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]


async def save_history(email_id: str, messages: List[Dict[str, Any]]):
    # 仅保留最近3轮修改（6条消息）
    if len(messages) > 6:
        messages = messages[-6:]
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM email_history WHERE email_id = %s", (email_id,))
            for msg in messages:
                await cur.execute(
                    "INSERT INTO email_history (email_id, role, content) VALUES (%s, %s, %s)",
                    (email_id, msg["role"], msg["content"]),
                )


async def get_all_emails() -> List[Dict[str, Any]]:
    """读取所有本地已处理的邮件。"""
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT email_id AS original_email_id, `from`, original_subject, body, reply_draft, classification, sent, created_at "
                "FROM processed_emails ORDER BY created_at DESC"
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_processed_email(email_id: str) -> Dict[str, Any]:
    """获取单封已处理邮件的原始信息。"""
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT `from`, original_subject, body, reply_draft "
                "FROM processed_emails WHERE email_id = %s",
                (email_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else {}


async def save_processed_email(email: Dict[str, Any]):
    """保存或更新单封处理结果。"""
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO processed_emails (email_id, `from`, original_subject, body, reply_draft, classification) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE reply_draft = VALUES(reply_draft), classification = VALUES(classification)",
                (email["original_email_id"], email["from"], email["original_subject"],
                 email.get("body", ""), email["reply_draft"], email["classification"]),
            )


async def update_email_reply(email_id: str, reply_draft: str):
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE processed_emails SET reply_draft = %s WHERE email_id = %s",
                (reply_draft, email_id),
            )


async def mark_email_sent(email_id: str):
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE processed_emails SET sent = 1 WHERE email_id = %s",
                (email_id,),
            )


# ── LangChain 工具函数（同步，供 Agent 调用）──

import pymysql

_db_config = {}


def _get_db_config():
    global _db_config
    if not _db_config:
        _db_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "smartmail"),
            "charset": "utf8mb4",
        }
    return _db_config


def _get_conn():
    return pymysql.connect(**_get_db_config())


def search_emails(keyword: str) -> list:
    """按关键词搜索已处理的邮件，匹配发件人、主题。返回匹配的邮件列表。"""
    conn = _get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            like = f"%{keyword}%"
            cur.execute(
                "SELECT email_id, `from`, original_subject, classification, sent "
                "FROM processed_emails WHERE `from` LIKE %s OR original_subject LIKE %s "
                "ORDER BY created_at DESC LIMIT 20",
                (like, like),
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_email_detail(email_id: str) -> dict:
    """获取某封邮件的完整信息，包括原始内容、分类、当前草稿。"""
    conn = _get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "SELECT email_id, `from`, original_subject, body, reply_draft, classification, sent "
                "FROM processed_emails WHERE email_id = %s",
                (email_id,),
            )
            row = cur.fetchone()
            return row or {}
    finally:
        conn.close()


def get_email_stats() -> dict:
    """获取邮件统计：本地总数、已发送数、各分类数量。"""
    conn = _get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total FROM processed_emails")
            total = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS sent FROM processed_emails WHERE sent = 1")
            sent = cur.fetchone()["sent"]
            cur.execute(
                "SELECT classification, COUNT(*) AS cnt FROM processed_emails GROUP BY classification"
            )
            by_type = {r["classification"]: r["cnt"] for r in cur.fetchall()}
            return {"total": total, "sent": sent, "by_type": by_type}
    finally:
        conn.close()


def delete_local_email(email_id: str) -> bool:
    """从本地数据库删除指定邮件记录。"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM processed_emails WHERE email_id = %s", (email_id,))
            cur.execute("DELETE FROM email_history WHERE email_id = %s", (email_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


# ── 聊天历史持久化 ──

async def get_chat_history() -> list:
    """获取所有聊天历史记录。"""
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT role, content FROM chat_history ORDER BY created_at ASC"
            )
            rows = await cur.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]


async def save_chat_message(role: str, content: str):
    """保存一条聊天消息。"""
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO chat_history (role, content) VALUES (%s, %s)",
                (role, content),
            )


async def clear_chat_history():
    """清空所有聊天历史。"""
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM chat_history")
