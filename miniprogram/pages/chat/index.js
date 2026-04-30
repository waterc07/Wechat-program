const api = require('../../utils/api')
const env = require('../../config/env')
const { getEndpointDisplay } = require('../../utils/request')
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
    baseURLDisplay: '',
    messages: [],
    scrollIntoView: '',
    inputMessage: '',
    consultationId: null,
    userId: null,
    historyVisible: false,
    historyLoading: false,
    historyItems: [],
    loading: false,
    reportLoading: false
  },

  onLoad(options) {
    const locale = getApp().globalData.locale || getStoredLocale()
    this.applyLocale(locale)
    this.setData({
      baseURLDisplay: this.getBaseURLDisplay(getEndpointDisplay())
    })

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

  onUnload() {
    this.abortActiveStream()
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
      baseURLDisplay: this.getBaseURLDisplay(getEndpointDisplay()),
      messages: this.relabelMessages(this.data.messages, t),
      historyItems: this.normalizeConsultations(this.data.historyItems)
    })
  },

  getBaseURLDisplay(url) {
    if (!url) {
      return ''
    }

    try {
      const normalized = url.replace(/^https?:\/\//, '')
      return normalized.replace(/\/$/, '')
    } catch (error) {
      return url
    }
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
    if (app.globalData.userId) {
      this.setData({ userId: app.globalData.userId })
      return this.fetchHistory({ silent: true })
    }

    if (app.globalData.loginReady) {
      return app.globalData.loginReady
        .then((user) => {
          this.setData({ userId: user.id })
          return this.fetchHistory({ silent: true })
        })
        .catch((error) => {
          wx.showToast({
            title: error.message || this.data.t.loginFailed,
            icon: 'none'
          })
        })
    }

    return Promise.resolve()
  },

  onInputChange(event) {
    this.setData({
      inputMessage: event.detail.value
    })
  },

  startChatStream({ userId, consultationId, message, t, previousMessages, previousScrollIntoView }) {
    this.resetStreamRuntimeState()

    this.activeStreamTask = api.chatStream(
      {
        user_id: userId,
        consultation_id: consultationId,
        message,
        locale: this.data.locale
      },
      {
        onChunkReceived: (chunk) => {
          this.handleStreamChunk(chunk)
        },
        success: () => {
          this.flushStreamDecoder()
          const donePayload = this.streamFinalPayload
          const streamError = this.streamErrorMessage

          if (streamError) {
            this.rollbackStreamState(message, previousMessages, previousScrollIntoView, streamError)
            return
          }

          if (!donePayload || !donePayload.consultation_id) {
            this.rollbackStreamState(
              message,
              previousMessages,
              previousScrollIntoView,
              t.sendFailed
            )
            return
          }

          this.setData({
            consultationId: donePayload.consultation_id
          })
          this.refreshMessages(donePayload.consultation_id).finally(() => {
            this.fetchHistory({ silent: true })
          })
        },
        fail: (error) => {
          this.rollbackStreamState(
            message,
            previousMessages,
            previousScrollIntoView,
            error.message || t.sendFailed
          )
        },
        complete: () => {
          this.activeStreamTask = null
          this.setData({ loading: false })
        }
      }
    )
  },

  resetStreamRuntimeState() {
    this.streamBuffer = ''
    this.streamFinalPayload = null
    this.streamErrorMessage = ''
    this.streamTextDecoder = typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8') : null
  },

  abortActiveStream() {
    if (this.activeStreamTask && typeof this.activeStreamTask.abort === 'function') {
      this.activeStreamTask.abort()
    }
    this.activeStreamTask = null
  },

  flushStreamDecoder() {
    if (!this.streamTextDecoder) {
      return
    }

    const tail = this.streamTextDecoder.decode()
    if (tail) {
      this.consumeStreamText(tail)
    }
  },

  handleStreamChunk(chunk) {
    const text = this.decodeChunkBuffer(chunk && chunk.data)
    if (!text) {
      return
    }
    this.consumeStreamText(text)
  },

  decodeChunkBuffer(buffer) {
    if (!buffer) {
      return ''
    }

    if (this.streamTextDecoder) {
      return this.streamTextDecoder.decode(buffer, { stream: true })
    }

    try {
      const bytes = new Uint8Array(buffer)
      let encoded = ''
      bytes.forEach((byte) => {
        encoded += `%${byte.toString(16).padStart(2, '0')}`
      })
      return decodeURIComponent(encoded)
    } catch (error) {
      const bytes = new Uint8Array(buffer)
      return String.fromCharCode.apply(null, bytes)
    }
  },

  consumeStreamText(text) {
    this.streamBuffer = `${this.streamBuffer || ''}${text.replace(/\r\n/g, '\n')}`
    const blocks = this.streamBuffer.split('\n\n')
    this.streamBuffer = blocks.pop() || ''

    blocks.forEach((block) => {
      this.processStreamBlock(block)
    })
  },

  processStreamBlock(block) {
    if (!block) {
      return
    }

    let eventName = 'message'
    const dataLines = []
    block.split('\n').forEach((line) => {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
        return
      }
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    })

    if (!dataLines.length) {
      return
    }

    let payload = null
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch (error) {
      return
    }

    if (eventName === 'meta') {
      if (payload.consultation_id) {
        this.setData({ consultationId: payload.consultation_id })
      }
      return
    }

    if (eventName === 'delta') {
      this.appendAssistantDelta(payload.delta || '')
      return
    }

    if (eventName === 'done') {
      this.streamFinalPayload = payload
      if (payload.assistant_message && payload.assistant_message.content) {
        this.replacePendingAssistantContent(payload.assistant_message.content)
      }
      return
    }

    if (eventName === 'error') {
      this.streamErrorMessage = payload.message || this.data.t.sendFailed
    }
  },

  appendAssistantDelta(delta) {
    if (!delta) {
      return
    }

    const messages = this.data.messages.slice()
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index]
      if (item.role === 'assistant' && item.pending) {
        messages[index] = {
          ...item,
          content: `${item.content || ''}${delta}`
        }
        this.setData({
          messages,
          scrollIntoView: item.viewId
        })
        return
      }
    }
  },

  replacePendingAssistantContent(content) {
    const messages = this.data.messages.slice()
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index]
      if (item.role === 'assistant' && item.pending) {
        messages[index] = {
          ...item,
          content
        }
        this.setData({
          messages,
          scrollIntoView: item.viewId
        })
        return
      }
    }
  },

  rollbackStreamState(message, previousMessages, previousScrollIntoView, errorMessage) {
    this.abortActiveStream()
    this.setData({
      inputMessage: message,
      messages: previousMessages,
      scrollIntoView: previousScrollIntoView
    })
    wx.showToast({
      title: errorMessage || this.data.t.sendFailed,
      icon: 'none'
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
        content: '',
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

    this.startChatStream({
      userId,
      consultationId,
      message,
      t,
      previousMessages,
      previousScrollIntoView
    })
  },

  refreshMessages(consultationId) {
    return api
      .getMessages(consultationId)
      .then((data) => {
        const normalizedMessages = this.normalizeMessages(data.messages)
        this.setData({
          consultationId,
          historyItems: this.normalizeConsultations(this.data.historyItems),
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

  fetchHistory({ silent = false } = {}) {
    const { userId, t } = this.data
    if (!userId) {
      return Promise.resolve([])
    }

    this.setData({ historyLoading: true })
    return api
      .getConsultations(userId)
      .then((data) => {
        const historyItems = this.normalizeConsultations(data.consultations)
        this.setData({ historyItems })
        return historyItems
      })
      .catch((error) => {
        if (!silent) {
          wx.showToast({
            title: error.message || t.historyLoadFailed,
            icon: 'none'
          })
        }
        return []
      })
      .finally(() => {
        this.setData({ historyLoading: false })
      })
  },

  openHistory() {
    const { loading, reportLoading } = this.data
    if (loading || reportLoading) {
      return
    }

    this.setData({ historyVisible: true })
    this.fetchHistory()
  },

  closeHistory() {
    this.setData({ historyVisible: false })
  },

  resumeConsultation(event) {
    const targetId = Number(event.currentTarget.dataset.id)
    if (!targetId) {
      return
    }

    const { consultationId, loading, reportLoading } = this.data
    if (loading || reportLoading) {
      return
    }

    this.closeHistory()
    if (consultationId === targetId && this.data.messages.length) {
      return
    }

    this.abortActiveStream()
    this.setData({
      consultationId: targetId,
      loading: false,
      reportLoading: false
    })
    this.refreshMessages(targetId)
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

  normalizeConsultations(consultations) {
    const { t, consultationId } = this.data
    return (consultations || []).map((item) => ({
      ...item,
      titleText: item.chief_complaint || item.last_message_preview || `#${item.id}`,
      previewText: item.last_message_preview || item.chief_complaint || '',
      displayTime: this.formatHistoryTime(item.last_message_at || item.updated_at),
      riskText: item.risk_level === 'high' ? t.historyRiskHigh : t.historyRiskNormal,
      isActive: item.id === consultationId
    }))
  },

  relabelMessages(messages, t) {
    return (messages || []).map((item) => ({
      ...item,
      displayTime: formatTime(item.timestampSource || item.created_at),
      statusText: this.getStatusText(item.statusKey, t)
    }))
  },

  formatHistoryTime(value) {
    if (!value) {
      return ''
    }

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return ''
    }

    const now = new Date()
    const isSameDay =
      now.getFullYear() === date.getFullYear() &&
      now.getMonth() === date.getMonth() &&
      now.getDate() === date.getDate()

    const hours = `${date.getHours()}`.padStart(2, '0')
    const minutes = `${date.getMinutes()}`.padStart(2, '0')
    if (isSameDay) {
      return `${hours}:${minutes}`
    }

    const month = `${date.getMonth() + 1}`.padStart(2, '0')
    const day = `${date.getDate()}`.padStart(2, '0')
    return `${month}/${day} ${hours}:${minutes}`
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
      historyVisible: false,
      loading: false,
      reportLoading: false
    })

    this.fetchHistory({ silent: true })

    if (showToast) {
      wx.showToast({
        title: this.data.t.startNewConsultationDone,
        icon: 'none'
      })
    }
  }
})
