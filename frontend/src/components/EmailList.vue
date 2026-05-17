<template>
  <div class="email-list">
    <h2>未读邮件处理结果</h2>
    <button @click="fetchEmails" :disabled="loading">
      {{ loading ? "处理中..." : "获取未读邮件" }}
    </button>

    <p v-if="message">{{ message }}</p>

    <ul v-if="emails.length">
      <li v-for="email in emails" :key="email.original_email_id" class="email-item">
        <strong>主题:</strong> {{ email.original_subject }}<br>
        <strong>分类:</strong> {{ email.classification }}<br>
        <strong>AI 回复草稿:</strong>
        <pre>{{ email.reply_draft }}</pre>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";

const emails = ref([]);
const message = ref("");
const loading = ref(false);

const API_BASE = "http://localhost:8000/api";

async function fetchEmails() {
  loading.value = true;
  message.value = "";
  emails.value = [];

  try {
    const res = await axios.get(`${API_BASE}/emails/process`);
    message.value = res.data.message;
    emails.value = res.data.results;
  } catch (err) {
    console.error(err);
    message.value = "获取失败，请检查后端是否运行";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.email-item {
  margin-bottom: 1rem;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
pre {
  background: #f5f5f5;
  padding: 0.5rem;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>