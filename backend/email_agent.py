# backend/email_agent.py
import json
import os
import re
from typing import List, Any, Dict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from .config import EMAIL_SYSTEM_PROMPT
from .email_client import get_unread_emails, send_reply

load_dotenv()


# 定义智能体的状态
class AgentState(BaseModel):
    emails: List[Dict[str, Any]]
    processed_results: List[Dict[str, Any]]
    actions: List[str]


# 定义 Agent 输入模型（BaseModel 工业化做法）
class EmailAgentInput(BaseModel):
    message: str


def create_email_agent():
    """创建并返回一个编译好的 LangGraph 工作流。"""
    # 模型初始化
    llm = ChatZhipuAI(
        model="glm-4-flash",  # 智谱模型
        temperature=0.7,
        api_key=os.getenv("ZHIPUAI_API_KEY"),
    )

    system_prompt = SystemMessage(content=EMAIL_SYSTEM_PROMPT)
    # 使用 create_agent 声明式配置
    agent = create_agent(
        model=llm,
        tools=[get_unread_emails, send_reply],
        system_prompt=system_prompt,
        # 中间件可选：添加速率限制、PII 脱敏等
    )

    # 工作流节点
    def fetch_emails(state: AgentState) -> dict:
        print("📧 获取未读邮件...")
        emails = get_unread_emails.invoke({})
        print(f"📧 未读邮件数量: {len(emails)}")
        for i, email in enumerate(emails, 1):
            print(f"邮件 {i}: 发件人={email['from']}, 主题={email['subject']}")
        return {"emails": emails, "actions": ["获取未读邮件"]}

    def process_emails(state: AgentState) -> dict:
        state_dict = state.model_dump()
        results = []

        for idx, email in enumerate(state_dict["emails"], start=1):
            try:
                email_text = f"发件人: {email['from']}\n主题: {email['subject']}\n正文: {email['body']}"
                agent_input = EmailAgentInput(message=email_text)

                # 调用 LLM
                try:
                    raw = agent.invoke({
                        "messages": [
                            {"role": "system", "content": system_prompt.content},
                            {"role": "user", "content": email_text}
                        ]
                    })
                except Exception as e:
                    raw = None
                    print(f"❌ 调用 agent.invoke 时失败: {e}")

                llm_text = ""
                parsed = {}

                if raw:
                    try:
                        # 如果 raw 是 dict 且有 messages
                        messages = getattr(raw, "messages", None) or raw.get("messages", None)
                        if messages:
                            # 找到 AIMessage
                            ai_msg = next((m for m in messages if getattr(m, "type", None) == "ai"), None)
                            if ai_msg:
                                llm_text = getattr(ai_msg, "content", str(ai_msg))
                            else:
                                # 没有 AIMessage 就直接尝试取 raw.content
                                llm_text = getattr(raw, "content", str(raw))
                        else:
                            # 直接取 content
                            llm_text = getattr(raw, "content", str(raw))

                        # 尝试解析 JSON
                        parsed = json.loads(re.sub(r"```json|```", "", llm_text).strip())
                    except Exception as e:
                        parsed = {}
                        print(f"JSON 解析失败: {e}")

                reply_draft = parsed.get("reply_draft", "[无法生成回复]")
                classification = parsed.get("classification", "unknown")

                # 构建结果
                results.append({
                    "original_email_id": email.get("id"),
                    "original_subject": email.get("subject"),
                    "reply_draft": reply_draft,
                    "classification": classification,
                    "raw_content": llm_text,
                    "stage": "initial",
                    "debug_info": {
                        "input_to_model": {"system": system_prompt.content, "user": email_text},
                        "raw_output": raw,
                        "parsed_json": parsed if parsed else None,
                        "error": locals().get("error", None)
                    }
                })

            except Exception as e:
                results.append({
                    "original_email_id": email.get("id"),
                    "original_subject": email.get("subject", "[未知]"),
                    "reply_draft": "[处理失败]",
                    "classification": "error",
                    "raw_content": str(e),
                    "debug_info": {}
                })

        state.processed_results = results

        return {
            "message": f"成功处理了 {len(results)} 封邮件",
            "processed_results": results  # 这里必须是 processed_results
        }

    def should_continue(state: AgentState) -> str:
        """条件路由：有邮件继续处理，否则结束"""
        if state.emails:
            return "process_emails"
        return END

    # 构建状态图
    workflow = StateGraph(AgentState)
    workflow.add_node("fetch_emails", fetch_emails)
    workflow.add_node("process_emails", process_emails)

    workflow.set_entry_point("fetch_emails")
    workflow.add_conditional_edges("fetch_emails", should_continue)
    workflow.add_edge("process_emails", END)

    # 编译并返回
    return workflow.compile()


# 为 FastAPI 创建一个全局的 agent 实例
email_agent = create_email_agent()
