const api = require('./utils/api')
const env = require('./config/env')
const { getStoredLocale, getTranslations } = require('./utils/i18n')

function getAuthCacheKey() {
  return `authState:${env.baseURL}`
}

App({
  globalData: {
    userId: null,
    userInfo: null,
    loginReady: null,
    locale: getStoredLocale()
  },

  onLaunch() {
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
          api
            .wxLogin({
              code: loginRes.code || 'mock-code',
              nickname: t.mockNickname
            })
            .then((data) => {
              this.globalData.userId = data.user.id
              this.globalData.userInfo = data.user
              wx.setStorageSync(getAuthCacheKey(), {
                userId: data.user.id,
                userInfo: data.user,
                baseURL: env.baseURL
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
