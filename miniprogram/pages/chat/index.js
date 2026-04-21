const api = require('../../utils/api')
const env = require('../../config/env')
const {
  LOCALE_OPTIONS,
  formatTime,
  getStoredLocale,
  getTranslations,
  setStoredLocale
} = require('../../utils/i18n')

Page({
  data: {
    locale: getStoredLocale(),
    localeOptions: LOCALE_OPTIONS,
    t: getTranslations(getStoredLocale()),
    disclaimer: getTranslations(getStoredLocale()).patientDisclaimer,
    baseURL: env.baseURL,
    messages: [],
    scrollIntoView: '',
    inputMessage: '',
    consultationId: null,
    userId: null,
    loading: false,
    reportLoading: false
  },

  onLoad(options) {
    const locale = getApp().globalData.locale || getStoredLocale()
    this.applyLocale(locale)

    if (options && options.reset === '1') {
      this.resetConversation(false)
    }

    this.ensureUserReady()
  },

  onShow() {
    const locale = getApp().globalData.locale || getStoredLocale()
    if (locale !== this.data.locale) {
      this.applyLocale(locale)
    }
  },

  applyLocale(locale) {
    const t = getTranslations(locale)
    wx.setNavigationBarTitle({
      title: t.chatNavTitle
    })

    this.setData({
      locale,
      t,
      disclaimer: t.patientDisclaimer,
      messages: this.relabelMessages(this.data.messages, t)
    })
  },

  switchLocale(event) {
    const locale = event.currentTarget.dataset.locale
    if (!locale || locale === this.data.locale) {
      return
    }
    setStoredLocale(locale)
    getApp().globalData.locale = locale
    this.applyLocale(locale)
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
        .catch((error) => {
          wx.showToast({
            title: error.message || this.data.t.loginFailed,
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
    const { inputMessage, consultationId, userId, loading, t } = this.data
    const message = inputMessage.trim()

    if (loading) {
      return
    }
    if (!userId) {
      wx.showToast({
        title: t.userNotReady,
        icon: 'none'
      })
      return
    }
    if (!message) {
      wx.showToast({
        title: t.inputRequired,
        icon: 'none'
      })
      return
    }

    const previousMessages = this.data.messages.slice()
    const previousScrollIntoView = this.data.scrollIntoView
    const timestamp = Date.now()
    const optimisticMessages = this.data.messages.concat([
      this.buildOptimisticMessage({
        id: `temp-user-${timestamp}`,
        role: 'user',
        content: message,
        timestamp,
        pending: false,
        statusKey: 'sending',
        statusText: t.statusSending
      }),
      this.buildOptimisticMessage({
        id: `temp-assistant-${timestamp}`,
        role: 'assistant',
        content: t.thinking,
        timestamp,
        pending: true,
        statusKey: 'thinking',
        statusText: t.statusThinking
      })
    ])

    this.setData({
      loading: true,
      inputMessage: '',
      messages: optimisticMessages,
      scrollIntoView: `msg-temp-assistant-${timestamp}`
    })

    api
      .chat({
        user_id: userId,
        consultation_id: consultationId,
        message,
        locale: this.data.locale
      })
      .then((data) => {
        this.setData({
          consultationId: data.consultation_id
        })
        return this.refreshMessages(data.consultation_id)
      })
      .catch((error) => {
        this.setData({
          inputMessage: message,
          messages: previousMessages,
          scrollIntoView: previousScrollIntoView
        })
        wx.showToast({
          title: error.message || t.sendFailed,
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
        const normalizedMessages = this.normalizeMessages(data.messages)
        this.setData({
          consultationId,
          messages: normalizedMessages,
          scrollIntoView:
            normalizedMessages.length > 0
              ? normalizedMessages[normalizedMessages.length - 1].viewId
              : ''
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || this.data.t.fetchMessagesFailed,
          icon: 'none'
        })
      })
  },

  normalizeMessages(messages) {
    const { t } = this.data
    return (messages || []).map((item) => ({
      ...item,
      pending: false,
      viewId: `msg-${item.id}`,
      timestampSource: item.created_at,
      displayTime: formatTime(item.created_at),
      statusKey: item.role === 'user' ? 'sent' : '',
      statusText: item.role === 'user' ? t.statusSent : ''
    }))
  },

  relabelMessages(messages, t) {
    return (messages || []).map((item) => ({
      ...item,
      displayTime: formatTime(item.timestampSource || item.created_at),
      statusText: this.getStatusText(item.statusKey, t)
    }))
  },

  getStatusText(statusKey, t) {
    if (statusKey === 'sending') {
      return t.statusSending
    }
    if (statusKey === 'thinking') {
      return t.statusThinking
    }
    if (statusKey === 'sent') {
      return t.statusSent
    }
    return ''
  },

  buildOptimisticMessage({ id, role, content, timestamp, pending, statusKey, statusText }) {
    return {
      id,
      role,
      content,
      pending,
      statusKey,
      viewId: `msg-${id}`,
      timestampSource: timestamp,
      displayTime: formatTime(timestamp),
      statusText
    }
  },

  generateReport() {
    const { consultationId, reportLoading, t } = this.data
    if (!consultationId) {
      wx.showToast({
        title: t.needConversation,
        icon: 'none'
      })
      return
    }
    if (reportLoading) {
      return
    }

    this.setData({ reportLoading: true })
    api
      .generateReport({ consultation_id: consultationId, locale: this.data.locale })
      .then(() => {
        wx.navigateTo({
          url: `/pages/report/index?consultationId=${consultationId}`
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || t.reportFailed,
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ reportLoading: false })
      })
  },

  promptResetConversation() {
    const { t, loading, reportLoading } = this.data
    if (loading || reportLoading) {
      return
    }

    wx.showModal({
      title: t.startNewConsultationTitle,
      content: t.startNewConsultationContent,
      confirmText: t.confirm,
      cancelText: t.cancel,
      success: (res) => {
        if (res.confirm) {
          this.resetConversation(true)
        }
      }
    })
  },

  resetConversation(showToast) {
    this.setData({
      messages: [],
      scrollIntoView: '',
      inputMessage: '',
      consultationId: null,
      loading: false,
      reportLoading: false
    })

    if (showToast) {
      wx.showToast({
        title: this.data.t.startNewConsultationDone,
        icon: 'none'
      })
    }
  }
})
