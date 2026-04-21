const env = require('../config/env')

function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${env.baseURL}${options.url}`,
      method: options.method || 'GET',
      timeout: env.timeout,
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...(options.header || {})
      },
      success: (res) => {
        const payload = res.data || {}
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
        reject({
          message: error.errMsg || '网络请求失败',
          code: 'NETWORK_ERROR'
        })
      }
    })
  })
}

module.exports = {
  request
}

