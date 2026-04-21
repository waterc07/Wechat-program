const { request } = require('./request')

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

function getMessages(consultationId) {
  return request({
    url: `/api/consultations/${consultationId}/messages`
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
  getMessages,
  generateReport,
  getReport
}

