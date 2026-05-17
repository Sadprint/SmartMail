# backend/agent.py
import os
from typing import Annotated, List, Any
import operator
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_community.chat_models import ChatZhipuAI
from .email_client import get_unread_emails, send_reply
from dotenv import load_dotenv
from pydantic import BaseModel
import re, json

load_dotenv()


# 定义智能体的状态
class AgentState(BaseModel):
    emails: List[dict]  # 未读邮件列表
    processed_results: Annotated[List[dict], operator.add]  # 处理结果列表
    actions: Annotated[List[str], operator.add]  # 操作日志


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

    system_prompt = SystemMessage(content="""
你是一个专业的邮件助理。你的任务是处理用户的未读邮件。
1. 对于正常邮件，生成一个简洁、礼貌的回复草稿。
2. 将垃圾邮件或无关紧要的邮件内容忽略。
""")

    # 使用 create_agent 声明式配置
    agent = create_agent(
        model=llm,
        tools=[get_unread_emails, send_reply],
        system_prompt=system_prompt,
        # 中间件可选：添加速率限制、PII 脱敏等
    )

    # 工作流节点
    def fetch_emails(state: AgentState) -> dict:
        """节点1：获取所有未读邮件。"""
        print("📧 获取未读邮件...")
        emails = get_unread_emails.invoke({})
        return {"emails": emails, "actions": ["获取未读邮件"]}

    def process_emails(state: AgentState) -> dict:
        state_dict = dict(state)  # BaseModel 转 dict
        results = []

        for email in state_dict["emails"]:
            email_input_text = f"发件人: {email['from']}\n主题: {email['subject']}\n正文: {email['body']}"
            agent_input_info = {
                "system": system_prompt.content,
                "user": email_input_text
            }

            debug_info = {
                "input_to_model": agent_input_info,
                "raw_output": None,
                "parsed_json": None,
                "error": None
            }

            try:
                # 调用 agent
                raw = agent.invoke({
                    "messages": [
                        {"role": "system", "content": system_prompt.content},
                        {"role": "user", "content": email_input_text}
                    ]
                })

                debug_info["raw_output"] = raw  # 直接记录返回的 dict

                # 提取 AIMessage
                messages = raw.get("messages", [])
                ai_msgs = [m for m in messages if m.__class__.__name__ == "AIMessage"]

                if ai_msgs:
                    text = ai_msgs[-1].content
                else:
                    text = ""
                    debug_info["error"] = "未找到 AIMessage"

                # 清理 Markdown ```json ```
                text_clean = re.sub(r"```json|```", "", text).strip()

                # 尝试解析 JSON
                try:
                    parsed = json.loads(text_clean)
                    debug_info["parsed_json"] = parsed
                except Exception as e:
                    parsed = {}
                    debug_info["error"] = f"JSON 解析失败: {e}"

                results.append({
                    "original_email_id": email["id"],
                    "original_subject": email["subject"],
                    "reply_draft": parsed.get("reply_draft", "[无法生成回复]"),
                    "classification": parsed.get("classification", "unknown"),
                    "raw_content": text,
                    "debug_info": debug_info
                })

            except Exception as e:
                debug_info["error"] = str(e)
                results.append({
                    "original_email_id": email.get("id"),
                    "original_subject": email.get("subject", "[未知]"),
                    "reply_draft": "[处理失败]",
                    "classification": "error",
                    "raw_content": "",
                    "debug_info": debug_info
                })

        return {"processed_results": results, "actions": ["批量处理邮件"]}

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
