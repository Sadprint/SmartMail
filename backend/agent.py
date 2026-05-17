# backend/agent.py
import os
from typing import Annotated, List, Any, Dict
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

    system_prompt = SystemMessage(content="""
    你是一个专业的邮件助理，专门处理用户的未读邮件。

    输入格式：每封邮件会提供“发件人”、“主题”、“正文”。请根据这些信息判断。

    任务：
    1. 对于需要用户回复的正常邮件（如来自同事、朋友、客户、邀请、咨询等），生成一个简洁、礼貌的回复草稿。
    2. 对于垃圾邮件、广告、诈骗邮件，回复草稿固定为 "不需要回复"。
    3. 对于系统通知类邮件（如密码重置、登录提醒、账户验证、安全提醒等），回复草稿固定为 "不需要回复"。
    4. 对于欢迎/订阅邮件（如注册欢迎、订阅确认、活动推荐等），回复草稿固定为 "不需要回复"。
    5. 如果无法明确判断邮件类型，classification 设为 "unknown"，reply_draft 设为 "需要人工处理"。

    输出格式：
    必须严格输出一个 JSON 对象，只包含两个字段，不要输出其他内容。
    {
      "reply_draft": "生成的回复草稿 或 '不需要回复' 或 '需要人工处理'",
      "classification": "正常邮件" | "垃圾邮件" | "系统通知" | "欢迎邮件" | "unknown"
    }

    严格要求：
    - 只输出纯文本 JSON，不要使用 Markdown 代码块。
    - JSON 必须有效，字符串使用双引号；如果草稿内包含双引号，请使用反斜杠转义（\"）。
    - 不要输出任何解释、注释或多余空格/换行。
    - 返回classification的时候必须是我给你的5种情况之一(非常重要)

    示例：
    输入：
    发件人: "张三" <zhangsan@example.com>
    主题: 关于下周的会议
    正文: 我们下周一开会，你能参加吗？
    输出：
    {"reply_draft": "您好，我可以参加下周一的会议。谢谢提醒。", "classification": "正常邮件"}

    输入：
    发件人: GitHub <noreply@github.com>
    主题: [GitHub] Your password was reset
    正文: Hello, your password was reset...
    输出：
    {"reply_draft": "不需要回复", "classification": "系统通知"}

    输入：
    发件人: "某某理财" <ad@spam.com>
    主题: 免费领取100万奖金
    正文: 点击链接领取...
    输出：
    {"reply_draft": "不需要回复", "classification": "垃圾邮件"}

    输入：
    发件人: Docker <welcome@docker.com>
    主题: 欢迎加入 Docker！
    正文: 你现在已经可以使用 Docker 平台...
    输出：
    {"reply_draft": "不需要回复", "classification": "欢迎邮件"}
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
