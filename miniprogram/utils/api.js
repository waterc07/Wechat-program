const { request, streamRequest } = require('./request')

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
    data
  })
}

function chatStream(data, handlers = {}) {
  return streamRequest({
    url: '/api/chat/stream',
    method: 'POST',
    data,
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

function getReport(consultationId) {
  return request({
    url: `/api/report/${consultationId}`
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
