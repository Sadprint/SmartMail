import os

import pymysql
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_community.chat_models import ChatZhipuAI

from .database import _get_conn
from .config import CHAT_SYSTEM_PROMPT

load_dotenv()


# ── 数据库工具 @tool 包装 ──

@tool
def get_local_emails() -> str:
    """获取本地已处理的所有邮件列表。返回格式化的文本摘要。"""
    conn = _get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "SELECT email_id, `from`, original_subject, classification, sent, body "
                "FROM processed_emails ORDER BY created_at DESC LIMIT 50"
            )
            rows = cur.fetchall()
        if not rows:
            return "本地暂无已处理的邮件。"
        lines = [f"共 {len(rows)} 封本地邮件：\n"]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"--- 第 {i} 封 ---\n"
                f"邮件ID: {r['email_id']}\n"
                f"发件人: {r['from']}\n"
                f"主题: {r['original_subject']}\n"
                f"分类: {r['classification']}\n"
                f"已发送: {'是' if r['sent'] else '否'}\n"
            )
        return "\n".join(lines)
    finally:
        conn.close()


@tool
def search_emails(keyword: str) -> str:
    """按关键词搜索本地邮件。返回格式化的文本结果。"""
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
            rows = cur.fetchall()
        if not rows:
            return f"未找到与 '{keyword}' 相关的邮件。"
        lines = [f"找到 {len(rows)} 封与 '{keyword}' 相关的邮件：\n"]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"--- 第 {i} 封 ---\n"
                f"邮件ID: {r['email_id']}\n"
                f"发件人: {r['from']}\n"
                f"主题: {r['original_subject']}\n"
                f"分类: {r['classification']}\n"
                f"已发送: {'是' if r['sent'] else '否'}\n"
            )
        return "\n".join(lines)
    finally:
        conn.close()


@tool
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


@tool
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


@tool
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


# ── 创建 Agent ──

def create_chat_agent():
    llm = ChatZhipuAI(
        model="glm-4-flash",
        temperature=0.7,
        api_key=os.getenv("ZHIPUAI_API_KEY"),
    )

    from .email_client import get_unread_emails, send_reply

    agent = create_agent(
        model=llm,
        tools=[
            get_unread_emails,
            send_reply,
            get_local_emails,
            search_emails,
            get_email_detail,
            get_email_stats,
            delete_local_email,
        ],
        system_prompt=CHAT_SYSTEM_PROMPT,
    )

    return agent


chat_agent = create_chat_agent()
