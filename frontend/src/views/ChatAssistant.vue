<template>
  <div class="chat-page">
    <div class="chat-container">
      <!-- 快捷指令 -->
      <div class="quick-commands">
        <button @click="sendPreset('请帮我检查未读邮件，正常邮件请生成回复草稿')" :disabled="loading">
          📥 检查新邮件
        </button>
        <button @click="sendPreset('请帮我列出本地已处理的邮件')" :disabled="loading">
          📂 查看本地邮件
        </button>
        <button @click="sendPreset('请帮我查看邮件统计')" :disabled="loading">
          📊 邮件统计
        </button>
        <button @click="clearChat" :disabled="loading" class="clear-btn">
          🆕 新对话
        </button>
      </div>

      <!-- 对话区域 -->
      <div class="chat-messages" ref="chatBox">
        <div v-if="!messages.length" class="chat-welcome">
          <div class="welcome-icon">🤖</div>
          <h2>邮箱智能助手</h2>
          <p>我可以帮你检查邮件、查找邮件、生成回复草稿、发送邮件等。<br/>直接输入指令或点击上方快捷按钮开始。</p>
        </div>
        <div v-for="(msg, i) in messages" :key="i" class="chat-item" :class="msg.role">
          <div class="chat-role">{{ msg.role === 'user' ? '你' : '🤖 AI' }}</div>
          <div class="chat-content">{{ msg.content }}</div>
          <div v-if="msg.toolCalls?.length" class="chat-tools">
            🔧 调用了：{{ msg.toolCalls.map(t => t.name).join(', ') }}
          </div>
        </div>
        <div v-if="loading" class="chat-loading">AI 思考中...</div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-row">
        <input
          v-model="input"
          @keyup.enter="sendMessage"
          placeholder="输入指令，如：帮我检查邮件"
          :disabled="loading"
        />
        <button @click="sendMessage" :disabled="loading || !input.trim()">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import axios from 'axios'

const input = ref('')
const messages = ref([])
const loading = ref(false)
const chatBox = ref(null)

// 启动时加载历史
onMounted(async () => {
  try {
    const res = await axios.get('/api/chat/history')
    if (res.data.history?.length) {
      messages.value = res.data.history
    }
  } catch (e) {
    console.error('加载聊天历史失败:', e)
  }
})

// 清空历史
const clearChat = async () => {
  if (!messages.value.length || loading.value) return
  try {
    await axios.delete('/api/chat/history')
  } catch (e) {
    console.error('清空聊天历史失败:', e)
  }
  messages.value = []
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

const callApi = async (text, history) => {
  loading.value = true
  await scrollToBottom()
  try {
    const res = await axios.post('/api/chat', { message: text, history })
    messages.value.push({
      role: 'ai',
      content: res.data.reply || '(无回复)',
      toolCalls: res.data.tool_calls || []
    })
  } catch (err) {
    console.error('请求失败:', err)
    messages.value.push({ role: 'ai', content: '抱歉，请求失败，请稍后重试。' })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const sendMessage = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  // 先取历史（不含当前消息），再 push
  const history = messages.value.map(m => ({ role: m.role, content: m.content }))
  messages.value.push({ role: 'user', content: text })
  callApi(text, history)
}

const sendPreset = (text) => {
  if (loading.value) return
  const history = messages.value.map(m => ({ role: m.role, content: m.content }))
  messages.value.push({ role: 'user', content: text })
  callApi(text, history)
}
</script>

<style scoped>
.chat-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 24px;
}
.chat-container {
  width: 100%;
  max-width: 800px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
}
.quick-commands {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #fafcff;
  flex-wrap: wrap;
}
.quick-commands button {
  padding: 8px 18px;
  border-radius: 20px;
  border: 1px solid #3b82f6;
  background: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.quick-commands button:hover:not(:disabled) {
  background: #eef2ff;
}
.quick-commands button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.clear-btn {
  margin-left: auto;
  border-color: #ef4444 !important;
  color: #ef4444 !important;
}
.clear-btn:hover:not(:disabled) {
  background: #fef2f2 !important;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.chat-welcome {
  text-align: center;
  margin: auto;
  color: #64748b;
}
.chat-welcome .welcome-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.chat-welcome h2 {
  margin: 0 0 8px;
  color: #1e293b;
  font-size: 22px;
}
.chat-welcome p {
  font-size: 14px;
  line-height: 1.7;
  margin: 0;
}
.chat-item {
  max-width: 85%;
}
.chat-item.user {
  align-self: flex-end;
}
.chat-item.ai {
  align-self: flex-start;
}
.chat-role {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}
.chat-content {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.chat-item.user .chat-content {
  background: #667eea;
  color: white;
}
.chat-item.ai .chat-content {
  background: #f1f5f9;
  color: #1e293b;
}
.chat-tools {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.chat-loading {
  font-size: 13px;
  color: #94a3b8;
  padding: 4px 0;
  align-self: flex-start;
}
.chat-input-row {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
}
.chat-input-row input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #cbd5e1;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
}
.chat-input-row button {
  padding: 10px 24px;
  border-radius: 24px;
  border: none;
  background: #667eea;
  color: white;
  cursor: pointer;
  font-size: 14px;
}
.chat-input-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
