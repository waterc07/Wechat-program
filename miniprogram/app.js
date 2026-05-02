const api = require('./utils/api')
const env = require('./config/env')
const { getStoredLocale, getTranslations } = require('./utils/i18n')

function getAuthCacheKey() {
  if (env.transport === 'cloud-container') {
    return `authState:cloud:${env.cloudEnv}:${env.cloudService}`
  }
  return `authState:${env.baseURL}`
}

function initCloudContainer() {
  if (env.transport !== 'cloud-container') {
    return
  }

  if (!wx.cloud || typeof wx.cloud.init !== 'function') {
    console.warn('[cloud:init] wx.cloud is unavailable in current runtime')
    return
  }

  const config = {
    env: env.cloudEnv,
    traceUser: true
  }

  wx.cloud.init(config)
}

App({
  globalData: {
    userId: null,
    userInfo: null,
    loginReady: null,
    locale: getStoredLocale()
  },

  onLaunch() {
    initCloudContainer()

    const cachedAuth = wx.getStorageSync(getAuthCacheKey())
    if (cachedAuth && cachedAuth.userId) {
      this.globalData.userId = cachedAuth.userId
      this.globalData.userInfo = cachedAuth.userInfo || null
    }

    this.globalData.loginReady = this.initAuth()
  },

  initAuth() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          const locale = this.globalData.locale || getStoredLocale()
          const t = getTranslations(locale)
          if (!loginRes.code) {
            wx.showToast({
              title: t.wxLoginFailed,
              icon: 'none'
            })
            reject(new Error('wx.login did not return a code'))
            return
          }

          api
            .wxLogin({
              code: loginRes.code,
              nickname: t.mockNickname
            })
            .then((data) => {
              this.globalData.userId = data.user.id
              this.globalData.userInfo = data.user
              wx.setStorageSync(getAuthCacheKey(), {
                userId: data.user.id,
                userInfo: data.user,
                baseURL: env.baseURL,
                transport: env.transport,
                cloudEnv: env.cloudEnv,
                cloudService: env.cloudService
              })
              wx.removeStorageSync('userId')
              resolve(data.user)
            })
            .catch((error) => {
              wx.showToast({
                title: error.message || t.loginInitFailed,
                icon: 'none'
              })
              reject(error)
            })
        },
        fail: (error) => {
          const locale = this.globalData.locale || getStoredLocale()
          const t = getTranslations(locale)
          wx.showToast({
            title: t.wxLoginFailed,
            icon: 'none'
          })
          reject(error)
        }
      })
    })
  }
})
