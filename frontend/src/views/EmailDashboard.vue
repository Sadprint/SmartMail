<template>
  <div class="dashboard">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <button @click="fetchEmails" :disabled="loading" class="fetch-btn">
        {{ loading ? '获取中...' : '获取邮件' }}
      </button>
      <div v-if="emailList.length" class="info">
        共 {{ emailList.length }} 封邮件
      </div>
    </div>

    <!-- 主体 -->
    <div v-if="loading" class="loading-state">加载中，请稍候...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="!emailList.length" class="empty-state">暂无邮件，点击上方按钮获取</div>
    <div v-else class="main-layout">
      <!-- 左侧邮件列表 -->
      <aside class="email-list">
        <div class="list-header">
          <span>邮件列表</span>
          <span class="total-count">共 {{ emailList.length }} 封</span>
        </div>
        <div class="list-search">
          <input type="text" v-model="searchKeyword" placeholder="搜索主题..." />
          <button v-if="searchKeyword" @click="searchKeyword = ''" class="clear-search">✖</button>
        </div>
        <div class="list-items">
          <div v-for="(email, idx) in filteredEmails" :key="idx"
               class="list-item" :class="{ active: currentIdx === originalIndex(idx) }"
               @click="selectEmail(originalIndex(idx))">
            <div class="item-subject">{{ email.original_subject || '(无主题)' }}</div>
            <div class="item-classification">{{ email.classification }}</div>
          </div>
        </div>
      </aside>

      <!-- 右侧邮件详情 -->
      <main class="email-detail">
        <div class="detail-header">
          <strong>📧 邮件 {{ currentIdx + 1 }} / {{ emailList.length }}</strong>
          <div class="detail-nav">
            <button @click="prevEmail" :disabled="currentIdx === 0">◀ 上一封</button>
            <button @click="nextEmail" :disabled="currentIdx === emailList.length - 1">下一封 ▶</button>
          </div>
        </div>

        <div class="detail-content">
          <div class="field"><strong>主题:</strong> {{ currentEmail.original_subject }}</div>
          <div class="field"><strong>分类:</strong> {{ currentEmail.classification }}</div>

          <!-- AI 回复草稿编辑 -->
          <div class="field">
            <strong>AI 回复草稿:</strong>
            <textarea class="reply-textarea" v-model="currentEmail.reply_draft" rows="6"></textarea>
            <div class="buttons">
              <button @click="openSuggestionDialog" class="suggest-btn" :disabled="refining">
                {{ refining ? '提交中...' : '✏️ 修改建议' }}
              </button>
              <button @click="submitEmail" class="submit-btn" :disabled="sending">
                {{ sending ? '发送中...' : '📤 提交发送' }}
              </button>
            </div>
            <div v-if="currentEmail.sent" class="sent-info">已发送 ✅</div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const loading = ref(false)
const error = ref('')
const emailList = ref([])
const currentIdx = ref(0)
const searchKeyword = ref('')
const refining = ref(false)
const sending = ref(false)

// 过滤后的邮件列表
const filteredEmails = computed(() => {
  if (!searchKeyword.value.trim()) return emailList.value
  const keyword = searchKeyword.value.toLowerCase()
  return emailList.value.filter(email => email.original_subject?.toLowerCase().includes(keyword))
})

// 原列表索引
const originalIndex = (filteredIndex) => {
  const email = filteredEmails.value[filteredIndex]
  return emailList.value.findIndex(e => e === email)
}

// 当前邮件
const currentEmail = computed(() => emailList.value[currentIdx.value] || {})

// 获取邮件
const fetchEmails = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/api/emails/process')
    const data = res.data
    if (data.results && data.results.length) {
      emailList.value = data.results.map(e => ({ ...e, reply_draft: e.reply_draft || '', sent: false }))
      currentIdx.value = 0
      searchKeyword.value = ''
    } else {
      emailList.value = []
      error.value = '后端返回数据为空'
    }
  } catch (err) {
    console.error('fetchEmails 失败:', err)
    error.value = '请求失败，请检查后端服务或 CORS'
  } finally {
    loading.value = false
  }
}

// 切换邮件
const selectEmail = (idx) => { currentIdx.value = idx }
const prevEmail = () => { if (currentIdx.value > 0) currentIdx.value-- }
const nextEmail = () => { if (currentIdx.value < emailList.value.length - 1) currentIdx.value++ }

// 修改建议（调用 refine 接口）
const openSuggestionDialog = async () => {
  const suggestion = prompt('请输入对 AI 回复的修改建议：')
  if (!suggestion || !suggestion.trim()) return
  refining.value = true
  try {
    const response = await axios.post('/api/emails/refine', {
      email_id: currentEmail.value.original_email_id,
      suggestion
    })
    currentEmail.value.reply_draft = response.data.new_reply_draft || currentEmail.value.reply_draft
    alert('AI 回复已更新！')
  } catch (err) {
    console.error('修改建议失败:', err)
    alert('修改失败，请稍后重试。')
  } finally {
    refining.value = false
  }
}

// 提交发送（调用 send 接口）
const submitEmail = async () => {
  if (!currentEmail.value.reply_draft) return
  sending.value = true
  try {
    await axios.post('/api/emails/send', {
      to_email: currentEmail.from,
      original_subject: currentEmail.original_subject,
      reply_content: replyContent
    })

    currentEmail.value.sent = true
    alert('邮件发送成功！')
  } catch (err) {
    console.error('发送邮件失败:', err)
    alert('发送失败，请稍后重试。')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; padding: 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.fetch-btn { padding: 8px 24px; border-radius: 24px; border: none; background: #667eea; color: white; cursor: pointer; }
.fetch-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.info { font-size: 14px; color: #475569; }

/* 主体布局 */
.main-layout { display: flex; gap: 20px; min-height: 400px; overflow: hidden; }
.email-list { width: 320px; flex-shrink: 0; background: white; border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.list-header { display: flex; justify-content: space-between; padding: 16px 20px; font-weight: 600; border-bottom: 1px solid #e2e8f0; background: #fafcff; }
.list-search { padding: 12px; border-bottom: 1px solid #e2e8f0; position: relative; }
.list-search input { width: 100%; padding: 8px 32px 8px 12px; border: 1px solid #cbd5e1; border-radius: 30px; font-size: 14px; outline: none; }
.clear-search { position: absolute; right: 20px; top: 50%; transform: translateY(-50%); border: none; background: none; cursor: pointer; color: #94a3b8; font-size: 16px; }
.list-items { flex: 1; overflow-y: auto; }
.list-item { padding: 12px 16px; border-bottom: 1px solid #f0f2f5; cursor: pointer; transition: background 0.1s; }
.list-item:hover { background: #f1f5f9; }
.list-item.active { background: #eef2ff; border-left: 3px solid #3b82f6; }
.item-subject { font-weight: 500; font-size: 14px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-classification { font-size: 12px; color: #64748b; }

/* 右侧邮件详情 */
.email-detail { flex: 1; background: rgba(255,255,255,0.9); border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 16px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; background: #fafcff; }
.detail-nav button { background: #e2e8f0; border: none; padding: 6px 16px; border-radius: 20px; margin-left: 8px; cursor: pointer; }
.detail-nav button:disabled { opacity: 0.4; cursor: not-allowed; }
.detail-content { flex: 1; overflow-y: auto; padding: 16px 0; }
.field { margin-bottom: 16px; line-height: 1.5; }
.field strong { display: inline-block; width: 100px; color: #475569; }

/* AI 回复草稿 */
.reply-textarea { width: 100%; padding: 12px; border-radius: 12px; border: 1px solid #cbd5e1; resize: vertical; font-size: 14px; font-family: inherit; }
.buttons { margin-top: 8px; display: flex; gap: 12px; }
.suggest-btn { padding: 4px 12px; border-radius: 20px; border: 1px solid #3b82f6; color: #3b82f6; background: none; cursor: pointer; }
.suggest-btn:hover:not(:disabled) { background: #eef2ff; }
.submit-btn { padding: 4px 12px; border-radius: 20px; border: 1px solid #10b981; color: #10b981; background: none; cursor: pointer; }
.submit-btn:hover:not(:disabled) { background: #dcfce7; }
.suggest-btn:disabled, .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sent-info { margin-top: 8px; color: #10b981; font-weight: 500; }

/* 状态样式 */
.loading-state, .error-state, .empty-state { flex: 1; display: flex; justify-content: center; align-items: center; border-radius: 24px; color: #64748b; background: white; }
.error-state { color: #dc2626; }
</style>