const api = require('../../utils/api')
const { PATIENT_DISCLAIMER } = require('../../utils/disclaimer')

Page({
  data: {
    disclaimer: PATIENT_DISCLAIMER,
    messages: [],
    inputMessage: '',
    consultationId: null,
    userId: null,
    loading: false,
    reportLoading: false
  },

  onLoad() {
    this.ensureUserReady()
  },

  ensureUserReady() {
    const app = getApp()
    const cachedUserId = wx.getStorageSync('userId')
    if (cachedUserId) {
      this.setData({ userId: cachedUserId })
      return
    }

    if (app.globalData.loginReady) {
      app.globalData.loginReady
        .then((user) => {
          this.setData({ userId: user.id })
        })
        .catch(() => {
          wx.showToast({
            title: '登录失败，请稍后重试',
            icon: 'none'
          })
        })
    }
  },

  onInputChange(event) {
    this.setData({
      inputMessage: event.detail.value
    })
  },

  sendMessage() {
    const { inputMessage, consultationId, userId, loading } = this.data
    const message = inputMessage.trim()

    if (loading) {
      return
    }
    if (!userId) {
      wx.showToast({
        title: '用户尚未初始化完成',
        icon: 'none'
      })
      return
    }
    if (!message) {
      wx.showToast({
        title: '请输入症状描述',
        icon: 'none'
      })
      return
    }

    this.setData({ loading: true })

    api
      .chat({
        user_id: userId,
        consultation_id: consultationId,
        message
      })
      .then((data) => {
        this.setData({
          consultationId: data.consultation_id,
          inputMessage: ''
        })
        return this.refreshMessages(data.consultation_id)
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || '发送失败',
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  refreshMessages(consultationId) {
    return api
      .getMessages(consultationId)
      .then((data) => {
        this.setData({
          consultationId,
          messages: data.messages
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || '获取消息失败',
          icon: 'none'
        })
      })
  },

  generateReport() {
    const { consultationId, reportLoading } = this.data
    if (!consultationId) {
      wx.showToast({
        title: '请先完成至少一轮对话',
        icon: 'none'
      })
      return
    }
    if (reportLoading) {
      return
    }

    this.setData({ reportLoading: true })
    api
      .generateReport({ consultation_id: consultationId })
      .then(() => {
        wx.navigateTo({
          url: `/pages/report/index?consultationId=${consultationId}`
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || '生成报告失败',
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ reportLoading: false })
      })
  }
})

