# backend/refine_agent.py
import os
import re
import json
from typing import List, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import SystemMessage, AIMessage
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END

from .config import REFINE_SYSTEM_PROMPT

load_dotenv()


class RefineAgentState(BaseModel):
    email_id: str
    history: List[Dict[str, Any]] = []
    actions: List[str] = []
    new_reply_draft: str = ""


class RefineAgentInput(BaseModel):
    messages: List[Dict[str, Any]]


def create_refine_agent():
    """创建单封邮件 refine Agent"""
    llm = ChatZhipuAI(
        model="glm-4-flash",
        temperature=0.7,
        api_key=os.getenv("ZHIPUAI_API_KEY"),
    )

    system_prompt = SystemMessage(content=REFINE_SYSTEM_PROMPT)

    # 创建 Agent
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=system_prompt,
    )

    # 工作流节点
    def refine_email_node(state: RefineAgentState) -> dict:
        """
        state.history: [{"role": "system/user/assistant", "content": str, ...}]
        """
        messages = [{"role": "system", "content": REFINE_SYSTEM_PROMPT}]

        for msg in state.history:
            if msg.get("role") != "system" or msg.get("content") != REFINE_SYSTEM_PROMPT:
                messages.append(msg)

        # 调用 LLM
        raw = agent.invoke({"messages": messages})
        new_reply_draft = "[无法生成回复]"
        ai_msg = None
        if isinstance(raw, dict) and "messages" in raw:
            for msg in reversed(raw["messages"]):
                if isinstance(msg, AIMessage):
                    ai_msg = msg
                    break
        if ai_msg:
            content = ai_msg.content.strip()
            try:
                parsed = json.loads(re.sub(r"```json|```", "", content).strip())
                new_reply_draft = parsed.get("reply_draft", "[无法生成回复]")
            except Exception:
                new_reply_draft = content or "[无法生成回复]"

        # 更新状态
        state.new_reply_draft = new_reply_draft
        state.actions.append("refined_email")

        return {
            "email_id": state.email_id,
            "new_reply_draft": new_reply_draft,
            "stage": "refine",
            "debug_info": {
                "raw_output": raw,
                "messages_sent": messages
            }
        }

    # 构建状态图
    workflow = StateGraph(RefineAgentState)
    workflow.add_node("refine_email", refine_email_node)
    workflow.set_entry_point("refine_email")
    workflow.add_edge("refine_email", END)

    return workflow.compile()


# 全局 refine_agent
refine_agent = create_refine_agent()
