const env = require('../config/env')

function normalizeErrorMessage(error) {
  const rawMessage = error && error.errMsg ? error.errMsg : ''
  if (rawMessage.includes('request:fail')) {
    return '网络请求失败，请确认后端服务已启动且开发者工具已放开域名校验。'
  }
  return rawMessage || '网络请求失败'
}

function request(options) {
  return new Promise((resolve, reject) => {
    const method = (options.method || 'GET').toUpperCase()
    const url = `${env.baseURL}${options.url}`

    console.info('[request:start]', {
      method,
      url,
      data: options.data || {}
    })

    wx.request({
      url,
      method,
      timeout: env.timeout,
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...(options.header || {})
      },
      success: (res) => {
        const payload = res.data || {}
        console.info('[request:success]', {
          method,
          url,
          statusCode: res.statusCode,
          payload
        })
        if (res.statusCode >= 200 && res.statusCode < 300 && payload.success) {
          resolve(payload.data)
          return
        }

        reject({
          statusCode: res.statusCode,
          message: payload.message || '请求失败',
          code: payload.code || 'REQUEST_ERROR',
          data: payload.data || {}
        })
      },
      fail: (error) => {
        console.error('[request:fail]', {
          method,
          url,
          error
        })
        reject({
          message: normalizeErrorMessage(error),
          code: 'NETWORK_ERROR'
        })
      }
    })
  })
}

module.exports = {
  request
}
