# SmartMail — AI 智能邮件助手

基于 **FastAPI + Vue 3 + LangChain 1.0** 构建的智能邮件管理系统。支持 Agent 对话式全自动处理和传统半自动管理两种模式。

---
## 效果图片
![邮件管理界面](/images/邮件管理.png)
显示所有未发送的邮件，可以查看对应的主题，内容，提供修改建议，提交发送请求。

![邮件管理界面](/images/邮件智能助手.png)
主要对话界面，可以直接和ai进行沟通，然后ai会根据对话内容，自行决定调用什么工具，给出对应的回答。还可以帮用户发送邮件，修改内容。同时实现了多轮对话记忆。

![查询邮件](/images/对话.png)
通过对话，让ai查看对应邮件的内容显示。

![修改建议](/images/对话1.png)
发送修改建议

![修改内容](/images/对话2.png)
修改的对话内容如上


## 功能特性

### 🤖 邮箱智能助手（Agent 对话）
- 自然语言驱动的邮件管理，Agent 自主决定调用哪些工具
- 自动检查未读邮件、智能分类、生成回复草稿
- 搜索邮件、查看详情、统计数据、删除记录
- 对话历史持久化到 MySQL，刷新页面不丢失
- 一键开启新对话

### 📧 邮件管理（半自动）
- 一键获取未读邮件并批量生成 AI 草稿
- 邮件列表浏览、搜索过滤、逐封查看
- 原始邮件正文展示 + AI 草稿可编辑
- 多轮修改建议（refine），带对话上下文
- 一键发送回复

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (async) |
| AI 引擎 | LangChain 1.0 + LangGraph |
| LLM | 智谱 AI ChatZhipuAI (glm-4-flash) |
| 数据库 | MySQL (aiomysql 异步池 + pymysql 同步) |
| 邮箱协议 | IMAP (读取) / SMTP (发送) |
| 前端框架 | Vue 3 (Composition API) |
| 前端路由 | Vue Router 4 |
| 构建工具 | Vite |

---

## 项目结构

```
SmartMail/
├── backend/
│   ├── main.py              # FastAPI 入口，7 个 API 端点
│   ├── chat_agent.py         # Agent 核心（7 个工具）+ @tool 数据库包装
│   ├── email_agent.py        # 旧工作流（LangGraph StateGraph）
│   ├── refine_agent.py       # 旧修改建议工作流
│   ├── email_client.py       # IMAP/SMTP 封装 + @tool 邮件工具
│   ├── database.py           # MySQL 连接池 + CRUD + 同步工具函数
│   └── config.py             # 三个 System Prompt（Chat/Email/Refine）
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── ChatAssistant.vue   # Agent 对话页面
│       │   └── EmailDashboard.vue  # 邮件管理页面
│       ├── layouts/
│       │   └── AppLayout.vue       # 侧边栏导航布局
│       └── router/
│           └── index.js            # 路由配置（/ 和 /chat）
├── pyproject.toml            # Python 依赖（uv/pip 管理）
├── package.json              # Node.js 依赖
└── .env                      # 环境变量（需自行创建）
```

---

## 环境配置

### 1. MySQL 数据库

```sql
CREATE DATABASE smartmail CHARACTER SET utf8mb4;
```

表结构由应用启动时自动创建（`init_db`）。

### 2. .env 文件

在项目根目录创建 `.env`：

```env
# 邮箱配置（QQ 邮箱）
EMAIL_ACCOUNT=your_email@qq.com
EMAIL_PASSWORD=your_imap_auth_code
IMAP_SERVER=imap.qq.com
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465

# AI 模型
ZHIPUAI_API_KEY=your_zhipuai_api_key

# MySQL 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=smartmail
```

> QQ 邮箱需在设置中开启 IMAP/SMTP 服务，密码填授权码而非登录密码。

---

## 快速启动

### 1. 安装依赖

```bash
# Python 依赖
uv sync
# 或 pip install -e .

# 前端依赖
npm install
```

### 2. 启动后端

```bash
uvicorn backend.main:app --reload --port 8000
```

### 3. 启动前端

```bash
npm run dev
```

访问 `http://localhost:5173`。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/emails/process` | 获取未读邮件并批量生成 AI 草稿 |
| GET | `/api/emails/history` | 读取本地已处理邮件列表 |
| POST | `/api/emails/refine` | 对单封邮件提交修改建议，生成新草稿 |
| POST | `/api/emails/send` | 发送邮件回复，标记本地已发送 |
| POST | `/api/chat` | Agent 对话（支持历史上下文） |
| GET | `/api/chat/history` | 加载对话历史 |
| DELETE | `/api/chat/history` | 清空对话历史 |

---

## 使用指南

### 邮箱智能助手（/chat）

1. 点击导航栏「🤖 邮箱智能助手」
2. 输入指令或点击快捷按钮（检查新邮件 / 查看本地邮件 / 邮件统计）
3. Agent 自动调用工具执行，结果展示在对话中
4. 对话历史自动保存，刷新页面后恢复
5. 点击「🆕 新对话」清空历史

### 邮件管理（/）

1. 点击导航栏「📧 邮件管理」
2. 点击「📥 更新邮件」从邮箱拉取未读邮件并生成 AI 草稿
3. 点击「📂 读取本地邮件」查看已处理列表
4. 在左侧列表选择邮件，右侧查看详情
5. 编辑 AI 草稿后点击「✏️ 修改建议」继续优化
6. 点击「📤 提交发送」通过 SMTP 发送

---

## 数据库表

| 表 | 用途 |
|----|------|
| `processed_emails` | 已处理邮件（正文、草稿、分类、发送状态） |
| `email_history` | 单封邮件的 refine 对话上下文（最多保留 3 轮） |
| `chat_history` | Agent 对话记录 |

---

## 架构说明

### Agent 模式（chat_agent.py）

使用 `create_agent` 创建真正的 LangChain Agent，LLM 自主决定调用哪些工具。注册了 7 个工具：

- `get_unread_emails` — 获取未读邮件
- `get_local_emails` — 查看本地邮件列表
- `search_emails` — 按关键词搜索
- `get_email_detail` — 查看邮件详情
- `get_email_stats` — 邮件统计
- `delete_local_email` — 删除本地记录
- `send_reply` — 发送回复

### 工作流模式（email_agent.py + refine_agent.py）

使用 LangGraph StateGraph 的固定流程：获取邮件 → 逐封调用 LLM → 生成草稿。代码决定执行顺序，LLM 只做文本处理。

---

## 注意事项

- 邮箱建议使用专用测试账户
- QQ 邮箱 IMAP/SMTP 需提前在设置中开启
- `.env` 包含敏感信息，已由 `.gitignore` 排除
- 对话历史保存在 MySQL，不会因服务重启丢失
