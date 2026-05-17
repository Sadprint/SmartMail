import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export async function processEmails() {
  try {
    const response = await axios.get(`${API_BASE}/emails/process`);
    return response.data;
  } catch (err) {
    console.error('处理邮件失败:', err);
    throw err;
  }
}