const { request, streamRequest } = require('./request')

function createClientRequestId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function wxLogin(data) {
  return request({
    url: '/api/auth/wx-login',
    method: 'POST',
    data
  })
}

function chat(data) {
  return request({
    url: '/api/chat',
    method: 'POST',
    data: {
      client_request_id: createClientRequestId('chat'),
      ...data
    }
  })
}

function chatStream(data, handlers = {}) {
  return streamRequest({
    url: '/api/chat/stream',
    method: 'POST',
    data: {
      client_request_id: createClientRequestId('chat-stream'),
      ...data
    },
    ...handlers
  })
}

function getMessages(consultationId) {
  return request({
    url: `/api/consultations/${consultationId}/messages`
  })
}

function getConsultations(userId) {
  return request({
    url: `/api/consultations?user_id=${userId}`
  })
}

function generateReport(data) {
  return request({
    url: '/api/report/generate',
    method: 'POST',
    data
  })
}

function getReport(consultationId, locale) {
  const localeQuery = locale ? `?locale=${encodeURIComponent(locale)}` : ''
  return request({
    url: `/api/report/${consultationId}${localeQuery}`
  })
}

module.exports = {
  wxLogin,
  chat,
  chatStream,
  getConsultations,
  getMessages,
  generateReport,
  getReport
}
