# backend/main.py
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.database import init_db, close_db, get_history, save_history
from backend.database import save_processed_email, get_all_emails, get_processed_email, update_email_reply, mark_email_sent
from backend.database import get_chat_history, save_chat_message, clear_chat_history
from backend.refine_agent import refine_agent
from backend.email_agent import email_agent
from backend.chat_agent import chat_agent
from dotenv import load_dotenv
from backend.config import REFINE_SYSTEM_PROMPT


load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="智能邮件助手 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessResponse(BaseModel):
    message: str
    results: List[Dict[str, Any]]


class RefineRequest(BaseModel):
    email_id: str
    suggestion: str


class RefineResponse(BaseModel):
    email_id: str
    new_reply_draft: str
    debug_messages: List[Dict[str, Any]] = []


class SendEmailRequest(BaseModel):
    email_id: str = ""
    to_email: str
    original_subject: str
    reply_content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []


@app.get("/api/emails/process", response_model=ProcessResponse)
async def process_emails():
    try:
        final_state = await email_agent.ainvoke({"emails": [], "processed_results": [], "actions": []})
        processed_results = final_state.get("processed_results", [])

        # 持久化：保存处理结果（初始邮件+AI草稿全在 processed_emails）
        for email in processed_results:
            await save_processed_email(email)

        return ProcessResponse(
            message=f"成功处理了 {len(processed_results)} 封邮件",
            results=processed_results
        )
    except Exception as e:
        import traceback
        print("❌ /api/emails/process 出现异常:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.post("/api/emails/refine", response_model=RefineResponse)
async def refine_email(req: RefineRequest):
    try:
        email_id = req.email_id
        suggestion = req.suggestion.strip()

        # 从 processed_emails 取原始邮件 + 当前草稿
        email = await get_processed_email(email_id)
        if not email:
            raise HTTPException(status_code=404, detail="邮件 ID 不存在或尚未处理")

        # 构建消息: system + 原始上下文 + 修改历史 + 最新建议
        initial_context = (
            f"原始邮件：\n发件人: {email['from']}\n主题: {email['original_subject']}\n\n"
            f"正文:\n{email['body']}\n\n当前AI回复草稿:\n{email['reply_draft']}"
        )
        messages = [{"role": "system", "content": REFINE_SYSTEM_PROMPT}]
        messages.append({"role": "user", "content": initial_context})
        messages.extend(await get_history(email_id))
        messages.append({"role": "user", "content": suggestion})

        try:
            # 调用 refine_agent
            raw = await refine_agent.ainvoke({"email_id": email_id, "history": messages})

            # LLM 原始返回可能是 dict 或对象
            if isinstance(raw, dict):
                new_reply_draft = raw.get("new_reply_draft")
                agent_history = raw.get("history", [])
            else:
                try:
                    parsed_raw = json.loads(str(raw))
                    new_reply_draft = parsed_raw.get("new_reply_draft", "[无法生成回复]")
                    agent_history = parsed_raw.get("history", [])
                except Exception:
                    new_reply_draft = "[无法生成回复]"
                    agent_history = []

            # 如果 new_reply_draft 为空，尝试取 history 中最后一条 AI 消息
            if not new_reply_draft and agent_history:
                for h in reversed(agent_history):
                    if h.get("role") == "ai":
                        new_reply_draft = h.get("content", "[无法生成回复]")
                        break

            # 保存本次 refine 历史（仅修改对话）
            history = await get_history(email_id)
            history.append({"role": "user", "content": suggestion})
            history.append({"role": "assistant", "content": new_reply_draft})
            await save_history(email_id, history)
            await update_email_reply(email_id, new_reply_draft)

            return RefineResponse(
                email_id=email_id,
                new_reply_draft=new_reply_draft,
                debug_messages=messages
            )

        except Exception as e:
            raise HTTPException(status_code=502, detail=f"调用 LLM 异常: {str(e)}")

    except Exception as e:
        import traceback
        print("❌ /api/emails/refine 出现异常:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.get("/api/emails/history", response_model=ProcessResponse)
async def get_local_emails():
    try:
        emails = await get_all_emails()
        return ProcessResponse(
            message=f"读取了 {len(emails)} 封本地邮件",
            results=emails
        )
    except Exception as e:
        import traceback
        print("❌ /api/emails/history 出现异常:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # 构建完整消息历史：前端历史 + 当前用户消息
        all_messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
        all_messages.append({"role": "user", "content": req.message})
        result = await chat_agent.ainvoke({"messages": all_messages})
        messages = result.get("messages", [])
        # 提取最后一条 AI 消息作为回复
        reply = ""
        tool_calls = []
        for m in reversed(messages):
            if getattr(m, "type", None) == "ai":
                reply = getattr(m, "content", str(m))
                break
        # 收集工具调用信息
        for m in messages:
            if getattr(m, "type", None) == "tool":
                tool_calls.append({
                    "name": getattr(m, "name", ""),
                    "content": getattr(m, "content", str(m)),
                })
        # 持久化：保存用户消息和 AI 回复
        await save_chat_message("user", req.message)
        if reply:
            await save_chat_message("ai", reply)
        return ChatResponse(reply=reply, tool_calls=tool_calls)
    except Exception as e:
        import traceback
        print("❌ /api/chat 出现异常:")
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"Agent 异常: {str(e)}")


@app.get("/api/chat/history")
async def load_chat_history():
    """加载聊天历史。"""
    try:
        history = await get_chat_history()
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取聊天历史失败: {str(e)}")


@app.delete("/api/chat/history")
async def delete_chat_history():
    """清空聊天历史。"""
    try:
        await clear_chat_history()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空聊天历史失败: {str(e)}")


@app.post("/api/emails/send")
async def send_email(req: SendEmailRequest):
    try:
        from backend.email_client import EmailClient
        client = EmailClient()
        success = client.send_reply(req.to_email, req.original_subject, req.reply_content)
        if success:
            if req.email_id:
                await mark_email_sent(req.email_id)
            return {"success": True}
        else:
            raise HTTPException(status_code=502, detail="邮件发送失败")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"邮件发送异常: {str(e)}")

