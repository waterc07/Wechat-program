const api = require('./utils/api')
const { getStoredLocale, getTranslations } = require('./utils/i18n')

App({
  globalData: {
    userId: null,
    userInfo: null,
    loginReady: null,
    locale: getStoredLocale()
  },

  onLaunch() {
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
              wx.setStorageSync('userId', data.user.id)
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
