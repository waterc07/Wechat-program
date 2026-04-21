const api = require('../../utils/api')
const { PATIENT_DISCLAIMER } = require('../../utils/disclaimer')

Page({
  data: {
    consultationId: null,
    report: null,
    loading: true,
    disclaimer: PATIENT_DISCLAIMER
  },

  onLoad(options) {
    const consultationId = Number(options.consultationId || 0)
    if (!consultationId) {
      wx.showToast({
        title: '缺少问诊记录',
        icon: 'none'
      })
      this.setData({ loading: false })
      return
    }

    this.setData({ consultationId })
    this.fetchReport(consultationId)
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
          title: error.message || '获取报告失败',
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  }
})

