<template>
  <div class="email-dashboard">
    <h1>智能邮件助手</h1>
    <button @click="fetchEmails">处理未读邮件</button>

    <div v-if="loading">处理中...</div>

    <div v-if="results.length">
      <h2>处理结果：</h2>
      <ul>
        <li v-for="item in results" :key="item.original_email_id">
          <strong>{{ item.original_subject }}</strong>
          <p>{{ item.reply_draft }}</p>
          <small>分类: {{ item.classification }}</small>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { processEmails } from '../api/email.js';

const results = ref([]);
const loading = ref(false);

async function fetchEmails() {
  loading.value = true;
  try {
    const data = await processEmails();
    results.value = data.results;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.email-dashboard {
  max-width: 800px;
  margin: auto;
  padding: 2rem;
}
</style>