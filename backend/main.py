# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.agent import email_agent
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="智能邮件助手 API")

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


@app.get("/api/emails/process", response_model=ProcessResponse)
async def process_emails():
    try:
        final_state = await email_agent.ainvoke({"emails": [], "processed_results": [], "actions": []})
        processed_results = final_state.get("processed_results", [])
        return ProcessResponse(
            message=f"成功处理了 {len(processed_results)} 封邮件",
            results=processed_results
        )
    except Exception as e:
        import traceback
        print("❌ /api/emails/process 出现异常:")
        traceback.print_exc()  # <- 打印完整堆栈
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")