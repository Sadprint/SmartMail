# backend/email_client.py
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Dict, Any
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

class EmailClient:
    """封装所有与邮件服务器交互的底层细节。"""
    def __init__(self):
        self.email_account = os.getenv("EMAIL_ACCOUNT")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.imap_server = os.getenv("IMAP_SERVER")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))

    def _connect_imap(self):
        """建立 IMAP 连接并登录。"""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email_account, self.email_password)
        return mail

    def _decode_mime_words(self, text: str) -> str:
        """处理邮件标题、发件人等的中文编码问题。"""
        if not text:
            return ""
        decoded_parts = decode_header(text)
        decoded_strings = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_strings.append(part.decode(charset or "utf-8", errors="ignore"))
                except LookupError:
                    decoded_strings.append(part.decode("utf-8", errors="ignore"))
            else:
                decoded_strings.append(part)
        return " ".join(decoded_strings)

    def _get_email_body(self, msg: email.message.Message) -> str:
        """从邮件对象中提取正文，优先提取纯文本。"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        else:
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                payload = msg.get_payload(decode=True)
                return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
        return "[无文本内容]"

    # 1. 读取未读邮件
    def get_unread_emails(self) -> List[Dict[str, Any]]:
        """获取所有未读邮件。"""
        mails_data = []
        mail = self._connect_imap()
        try:
            mail.select("INBOX")
            # 搜索所有未读邮件
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return []
            email_ids = messages[0].split()
            for e_id in email_ids:
                status, msg_data = mail.fetch(e_id, '(RFC822)')
                if status != 'OK':
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_mime_words(msg.get("Subject", ""))
                sender = self._decode_mime_words(msg.get("From", ""))
                date = msg.get("Date", "")
                body = self._get_email_body(msg)
                mails_data.append({
                    "id": e_id.decode() if isinstance(e_id, bytes) else str(e_id),
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "body": body[:2000],
                })
            return mails_data
        finally:
            mail.close()
            mail.logout()

    # 2. 发送回复邮件
    def send_reply(self, to_email: str, original_subject: str, reply_content: str) -> bool:
        """回复邮件。"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_account
            msg['To'] = to_email
            # 处理回复的邮件主题
            subject = original_subject
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"
            msg['Subject'] = subject
            msg.attach(MIMEText(reply_content, 'plain', 'utf-8'))

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_account, self.email_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

# 将邮件操作包装成 LangChain 工具
@tool
def get_unread_emails() -> List[Dict[str, Any]]:
    """获取邮箱中所有未读的邮件。"""
    client = EmailClient()
    return client.get_unread_emails()

@tool
def send_reply(to_email: str, original_subject: str, reply_content: str) -> bool:
    """发送邮件回复，需要提供收件人、原邮件主题和回复内容。"""
    client = EmailClient()
    return client.send_reply(to_email, original_subject, reply_content)