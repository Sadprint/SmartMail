import request from './request'

export const fetchProcessedEmails = () => {
  return request.get('/api/emails/process')
}