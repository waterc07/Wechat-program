const api = require('./utils/api')

App({
  globalData: {
    userId: null,
    userInfo: null,
    loginReady: null
  },

  onLaunch() {
    this.globalData.loginReady = this.initAuth()
  },

  initAuth() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          api
            .wxLogin({
              code: loginRes.code || 'mock-code',
              nickname: '微信用户'
            })
            .then((data) => {
              this.globalData.userId = data.user.id
              this.globalData.userInfo = data.user
              wx.setStorageSync('userId', data.user.id)
              resolve(data.user)
            })
            .catch((error) => {
              wx.showToast({
                title: '登录初始化失败',
                icon: 'none'
              })
              reject(error)
            })
        },
        fail: reject
      })
    })
  }
})

