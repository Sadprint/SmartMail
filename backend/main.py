# backend/main.py
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.refine_agent import refine_agent
from backend.email_agent import email_agent
from dotenv import load_dotenv
from backend.config import REFINE_SYSTEM_PROMPT
from backend.email_client import send_reply


load_dotenv()
app = FastAPI(title="智能邮件助手 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

email_history_memory: Dict[str, List[Dict[str, Any]]] = {}


class ProcessResponse(BaseModel):
    message: str
    results: List[Dict[str, Any]]


class RefineRequest(BaseModel):
    email_id: str
    suggestion: str


class RefineResponse(BaseModel):
    email_id: str
    new_reply_draft: str


class SendEmailRequest(BaseModel):
    to_email: str
    original_subject: str
    reply_content: str


@app.get("/api/emails/process", response_model=ProcessResponse)
async def process_emails():
    try:
        final_state = await email_agent.ainvoke({"emails": [], "processed_results": [], "actions": []})
        processed_results = final_state.get("processed_results", [])

        # 初始化历史记录
        for email in processed_results:
            email_id = email["original_email_id"]
            if email_id not in email_history_memory:
                email_history_memory[email_id] = [
                    {"role": "user", "content": email["debug_info"]["input_to_model"]["user"]},
                    {"role": "ai", "content": email["reply_draft"]},
                ]

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

        if email_id not in email_history_memory:
            raise HTTPException(status_code=404, detail="邮件 ID 不存在或尚未处理")

        history = email_history_memory[email_id]

        # 构建 messages: system + 历史 + 最新用户建议
        messages = [{"role": "system", "content": REFINE_SYSTEM_PROMPT}]
        messages.extend(history)
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

            # 保存本次 refine 历史
            history.append({"role": "user", "content": suggestion})
            history.append({"role": "assistant", "content": new_reply_draft})
            email_history_memory[email_id] = history

            return RefineResponse(
                email_id=email_id,
                new_reply_draft=new_reply_draft
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"调用 LLM 异常: {str(e)}")

    except Exception as e:
        import traceback
        print("❌ /api/emails/refine 出现异常:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.post("/api/emails/send")
async def send_email(req: SendEmailRequest):
    try:
        success = send_reply(req.to_email, req.original_subject, req.reply_content)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="邮件发送失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送异常: {str(e)}")

