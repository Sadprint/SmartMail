# 智能邮件助手（AI Email Assistant）

一个基于 FastAPI + Vue 3 + LangChain 的智能邮件处理系统，可以自动读取未读邮件、生成 AI 回复草稿、支持用户修改草稿并直接发送邮件。  

---

## 功能

1. **自动获取未读邮件**  
   - 通过 IMAP 连接邮箱读取未读邮件  
   - 显示发件人、主题、日期、邮件内容摘要  

2. **AI 回复草稿生成**  
   - 使用智谱 AI（ChatZhipuAI）生成初始回复  
   - 支持用户查看 AI 草稿  

3. **用户修改与提交**  
   - 用户可以在输入框中修改 AI 草稿  
   - 点击发送按钮，直接将修改后的文本通过 SMTP 发送  

4. **邮件历史记录**  
   - 每封邮件的 AI 草稿与用户修改记录都会保存在内存中  
   - 支持多次 refine（修改）  

---

## 项目结构
project/
│
├─ backend/
│ ├─ main.py # FastAPI 后端入口
│ ├─ email_agent.py # 邮件处理智能体
│ ├─ refine_agent.py # 单封邮件 refine 智能体
│ ├─ email_client.py # IMAP/SMTP 封装
│ └─ config.py # 系统 prompt 配置
│
├─ frontend/
│ └─ EmailDashboard.vue # Vue 3 前端页面
│
├─ .env # 邮箱账号/密码/API_KEY 等配置
└─ README.md


---

## 环境依赖

### 后端

- Python 3.10+
- FastAPI
- pydantic
- python-dotenv
- LangChain & langgraph
- 智谱 API key (ZHIPUAI_API_KEY)
- 邮箱账号及 IMAP/SMTP 配置

### 前端

- Vue 3
- Axios
- 支持现代浏览器

---

## 环境变量 (.env 示例)

```env
EMAIL_ACCOUNT=your_email@example.com
EMAIL_PASSWORD=your_email_password
IMAP_SERVER=imap.example.com
SMTP_SERVER=smtp.example.com
SMTP_PORT=465

ZHIPUAI_API_KEY=your_zhipuai_api_key
```

## 快速启动
### 1.后端
```
# 安装依赖
pip install fastapi uvicorn python-dotenv pydantic langchain langgraph langchain_community

# 运行后端
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
后端接口：
方法	路径	描述
GET	/api/emails/process	获取未读邮件并生成 AI 草稿
POST	/api/emails/refine	对单封邮件进行 AI 草稿 refine
POST	/api/emails/send	发送邮件（用户可修改 AI 草稿后发送）

### 2. 前端
```
# 安装依赖
npm install

# 启动前端
npm run dev
```
前端访问：http://localhost:5173/（默认 Vite 端口）

## 使用说明

1. **打开前端页面**
2. **点击 获取邮件，加载未读邮件列表**
3. **点击某封邮件查看 AI 草稿**
4. **在文本框中修改草稿（可不修改）**
5. **点击 发送邮件，修改后的内容会通过邮箱发送**

## 注意事项
邮箱账号建议使用专用账户，确保 IMAP/SMTP 已开启
多次 refine 历史保存在内存中，重启服务会丢失
确保 ZHIPUAI_API_KEY 可用，否则无法生成 AI 草稿