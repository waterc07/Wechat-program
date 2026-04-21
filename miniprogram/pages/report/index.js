const api = require('../../utils/api')
const {
  LOCALE_OPTIONS,
  getStoredLocale,
  getTranslations,
  setStoredLocale
} = require('../../utils/i18n')

Page({
  data: {
    consultationId: null,
    report: null,
    loading: true,
    regenerating: false,
    locale: getStoredLocale(),
    localeOptions: LOCALE_OPTIONS,
    t: getTranslations(getStoredLocale()),
    disclaimer: getTranslations(getStoredLocale()).patientDisclaimer
  },

  onLoad(options) {
    const locale = getApp().globalData.locale || getStoredLocale()
    this.applyLocale(locale)

    const consultationId = Number(options.consultationId || 0)
    if (!consultationId) {
      wx.showToast({
        title: this.data.t.missingConsultation,
        icon: 'none'
      })
      this.setData({ loading: false })
      return
    }

    this.setData({ consultationId })
    this.fetchReport(consultationId)
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
      title: t.reportNavTitle
    })
    this.setData({
      locale,
      t,
      disclaimer: t.patientDisclaimer
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

  fetchReport(consultationId) {
    this.setData({ loading: true })
    api
      .getReport(consultationId)
      .then((data) => {
        this.setData({
          report: data.report
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || this.data.t.fetchReportFailed,
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  regenerateReport() {
    const { consultationId, regenerating, loading, t } = this.data
    if (!consultationId || regenerating || loading) {
      return
    }

    this.setData({ regenerating: true })
    api
      .generateReport({ consultation_id: consultationId, locale: this.data.locale })
      .then((data) => {
        this.setData({
          report: data.report
        })
        wx.showToast({
          title: t.reportGenerated,
          icon: 'none'
        })
      })
      .catch((error) => {
        wx.showToast({
          title: error.message || t.reportFailed,
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ regenerating: false })
      })
  },

  backToChat() {
    const pages = getCurrentPages()
    if (pages.length > 1) {
      wx.navigateBack()
      return
    }

    wx.reLaunch({
      url: '/pages/chat/index'
    })
  },

  startNewConsultation() {
    wx.reLaunch({
      url: '/pages/chat/index?reset=1'
    })
  }
})
