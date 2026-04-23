const STORAGE_KEY = 'locale'
const DEFAULT_LOCALE = 'zh-CN'

const LOCALE_OPTIONS = [
  { code: 'zh-CN', shortLabel: '中' },
  { code: 'en-US', shortLabel: 'EN' }
]

const TRANSLATIONS = {
  'zh-CN': {
    chatNavTitle: '患者预问诊',
    reportNavTitle: '医生摘要',
    heroTitle: '就诊前症状整理',
    heroSubtitle: '按聊天方式补充症状、持续时间和伴随情况，系统会生成给医生参考的结构化摘要。',
    disclaimerTitle: '安全提示',
    patientDisclaimer:
      '本工具仅用于就诊前信息整理与分诊辅助，不能替代医生面诊，也不能作为最终诊断依据。如症状加重或出现紧急情况，请立即前往线下医疗机构或急救。',
    currentEndpoint: '当前联调地址',
    emptyTitle: '先描述您的主要不适',
    emptyHint: '例如：发烧两天、咳嗽、喉咙痛，或肚子疼伴随恶心。',
    inputPlaceholder: '请输入症状、持续时间、严重程度和伴随症状',
    send: '发送',
    sending: '发送中...',
    generateReport: '生成医生摘要',
    generatingReport: '生成报告中...',
    regenerateReport: '重新生成报告',
    regeneratingReport: '重新生成中...',
    continueConsultation: '返回继续问诊',
    startNewConsultation: '开始新问诊',
    historyButton: '历史记录',
    historyTitle: '问诊历史',
    historySubtitle: '可以随时恢复之前的问诊会话',
    historyLoading: '正在加载历史记录...',
    historyEmptyTitle: '还没有问诊记录',
    historyEmptyHint: '发送第一条症状描述后，这里会显示历史会话。',
    historyResume: '继续这次问诊',
    historyCurrent: '当前',
    historyRiskHigh: '高风险',
    historyRiskNormal: '常规',
    historyReports: '报告',
    historyMessages: '消息',
    historyLoadFailed: '获取历史记录失败',
    startNewConsultationTitle: '开始新问诊',
    startNewConsultationContent: '将清空当前页面会话内容，并开始新的预问诊流程。',
    startNewConsultationDone: '已开始新的问诊会话',
    assistantRole: '助手',
    patientRole: '患者',
    thinking: 'AI 正在思考，请稍候...',
    statusSent: '已发送',
    statusSending: '发送中',
    statusThinking: '思考中',
    loginFailed: '登录失败，请稍后重试',
    loginInitFailed: '登录初始化失败',
    wxLoginFailed: '微信登录失败',
    userNotReady: '用户尚未初始化完成',
    inputRequired: '请输入症状描述',
    sendFailed: '发送失败',
    fetchMessagesFailed: '获取消息失败',
    needConversation: '请先完成至少一轮对话',
    reportFailed: '生成报告失败',
    missingConsultation: '缺少问诊记录',
    fetchReportFailed: '获取报告失败',
    reportGenerated: '报告已重新生成',
    reportHeaderTitle: '预问诊结构化摘要',
    reportHeaderSubtitle: '供医生快速了解患者主诉与基础情况，不能替代医生正式诊断。',
    reportLoading: '报告生成中，请稍候...',
    fieldSymptoms: '症状概述',
    fieldConditions: '可能方向',
    fieldDepartment: '建议科室',
    fieldUrgency: '紧急程度',
    fieldAdvice: '下一步建议',
    fieldDisclaimer: '免责声明',
    confirm: '确认',
    cancel: '取消',
    mockNickname: '微信用户'
  },
  'en-US': {
    chatNavTitle: 'Pre-visit Chat',
    reportNavTitle: 'Doctor Summary',
    heroTitle: 'Pre-visit Symptom Intake',
    heroSubtitle:
      'Describe symptoms in a chat flow. The app will prepare a structured summary for doctors.',
    disclaimerTitle: 'Safety Notice',
    patientDisclaimer:
      'This tool is only for pre-visit information collection and triage support. It does not replace a doctor and must not be used as a final diagnosis. Seek in-person care or emergency help if symptoms worsen or become urgent.',
    currentEndpoint: 'Current API endpoint',
    emptyTitle: 'Describe your main discomfort first',
    emptyHint: 'For example: fever for two days, cough, sore throat, or stomach pain with nausea.',
    inputPlaceholder: 'Describe symptoms, duration, severity, and related symptoms',
    send: 'Send',
    sending: 'Sending...',
    generateReport: 'Generate doctor summary',
    generatingReport: 'Generating report...',
    regenerateReport: 'Regenerate report',
    regeneratingReport: 'Regenerating...',
    continueConsultation: 'Back to chat',
    startNewConsultation: 'New consultation',
    historyButton: 'History',
    historyTitle: 'Consultation history',
    historySubtitle: 'Resume any earlier consultation without losing context.',
    historyLoading: 'Loading consultation history...',
    historyEmptyTitle: 'No consultation history yet',
    historyEmptyHint: 'After you send the first symptom message, past consultations will appear here.',
    historyResume: 'Resume consultation',
    historyCurrent: 'Current',
    historyRiskHigh: 'High risk',
    historyRiskNormal: 'Routine',
    historyReports: 'Reports',
    historyMessages: 'Messages',
    historyLoadFailed: 'Failed to load consultation history.',
    startNewConsultationTitle: 'Start a new consultation',
    startNewConsultationContent:
      'This will clear the current page conversation and start a new pre-visit intake flow.',
    startNewConsultationDone: 'New consultation started',
    assistantRole: 'Assistant',
    patientRole: 'Patient',
    thinking: 'AI is thinking. Please wait...',
    statusSent: 'Sent',
    statusSending: 'Sending',
    statusThinking: 'Thinking',
    loginFailed: 'Login failed. Please try again later.',
    loginInitFailed: 'Login initialization failed.',
    wxLoginFailed: 'WeChat login failed.',
    userNotReady: 'User session is not ready yet.',
    inputRequired: 'Please enter symptom details.',
    sendFailed: 'Failed to send.',
    fetchMessagesFailed: 'Failed to load messages.',
    needConversation: 'Please complete at least one round of conversation first.',
    reportFailed: 'Failed to generate the report.',
    missingConsultation: 'Missing consultation record.',
    fetchReportFailed: 'Failed to load the report.',
    reportGenerated: 'Report regenerated.',
    reportHeaderTitle: 'Structured Pre-visit Summary',
    reportHeaderSubtitle:
      'Helps doctors quickly understand the main complaint and key context. It is not a final diagnosis.',
    reportLoading: 'Generating the report. Please wait...',
    fieldSymptoms: 'Symptom summary',
    fieldConditions: 'Possible directions',
    fieldDepartment: 'Suggested department',
    fieldUrgency: 'Urgency level',
    fieldAdvice: 'Next-step advice',
    fieldDisclaimer: 'Disclaimer',
    confirm: 'Confirm',
    cancel: 'Cancel',
    mockNickname: 'WeChat User'
  }
}

function getStoredLocale() {
  try {
    const locale = wx.getStorageSync(STORAGE_KEY)
    return TRANSLATIONS[locale] ? locale : DEFAULT_LOCALE
  } catch (error) {
    return DEFAULT_LOCALE
  }
}

function setStoredLocale(locale) {
  if (!TRANSLATIONS[locale]) {
    return DEFAULT_LOCALE
  }
  wx.setStorageSync(STORAGE_KEY, locale)
  return locale
}

function getTranslations(locale) {
  return TRANSLATIONS[locale] || TRANSLATIONS[DEFAULT_LOCALE]
}

function formatTime(value) {
  if (!value) {
    return ''
  }
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const hours = `${date.getHours()}`.padStart(2, '0')
  const minutes = `${date.getMinutes()}`.padStart(2, '0')
  return `${hours}:${minutes}`
}

module.exports = {
  DEFAULT_LOCALE,
  LOCALE_OPTIONS,
  getStoredLocale,
  setStoredLocale,
  getTranslations,
  formatTime
}
