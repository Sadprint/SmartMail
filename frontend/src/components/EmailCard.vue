<!-- views/EmailDashboard.vue -->
<template>
  <div class="email-dashboard">
    <div class="toolbar">
      <div class="email-selector">
        <button @click="emailStore.prevEmail" :disabled="!emailStore.hasEmails || emailStore.currentIndex === 0">
          ◀ 上一封
        </button>
        <span class="counter">
          第 {{ emailStore.currentIndex + 1 }} / {{ emailStore.emailCount }} 封
        </span>
        <button @click="emailStore.nextEmail" :disabled="!emailStore.hasEmails || emailStore.currentIndex === emailStore.emailCount - 1">
          下一封 ▶
        </button>
        <select
          v-if="emailStore.hasEmails"
          v-model="selectedIndex"
          @change="emailStore.setCurrentIndex(Number(selectedIndex))"
          class="index-select"
        >
          <option v-for="(_, idx) in emailStore.emailList" :key="idx" :value="idx">
            邮件 #{{ idx + 1 }}
          </option>
        </select>
      </div>
      <button @click="fetchEmails" :disabled="emailStore.loading" class="refresh-btn">
        {{ emailStore.loading ? '获取中...' : '重新获取邮件' }}
      </button>
    </div>

    <div v-if="emailStore.loading" class="loading">加载中，请稍候...</div>
    <div v-else-if="emailStore.error" class="error">{{ emailStore.error }}</div>
    <div v-else-if="!emailStore.hasEmails" class="empty">暂无邮件，点击「重新获取邮件」</div>
    <div v-else class="email-viewer">
      <EmailCard
        :email="emailStore.currentEmail"
        :index="emailStore.currentIndex"
        :visible="emailStore.currentDebugVisible"
        @toggle="emailStore.toggleCurrentDebug"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEmailStore } from '@/stores/emailStore'
import EmailCard from '@/components/EmailCard.vue'

const emailStore = useEmailStore()

// 用于下拉选择器的绑定（v-model 双向绑定）
const selectedIndex = computed({
  get: () => emailStore.currentIndex,
  set: (val) => emailStore.setCurrentIndex(val)
})

const fetchEmails = () => {
  emailStore.fetchEmails()
}
</script>

<style scoped>
.email-dashboard {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}
.email-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  padding: 8px 16px;
  border-radius: 40px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.email-selector button {
  background: #e2e8f0;
  border: none;
  padding: 6px 12px;
  border-radius: 30px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}
.email-selector button:hover:not(:disabled) {
  background: #cbd5e1;
}
.email-selector button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.counter {
  font-weight: 500;
  min-width: 100px;
  text-align: center;
}
.index-select {
  padding: 6px 10px;
  border-radius: 20px;
  border: 1px solid #ccc;
  background: white;
  font-size: 14px;
}
.refresh-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 40px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}
.refresh-btn:hover:not(:disabled) {
  background: #2563eb;
}
.loading, .error, .empty {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 20px;
  margin-top: 20px;
}
.email-viewer {
  flex: 1;
  overflow-y: auto;
  margin-top: 10px;
}
</style>