SUPPORTED_LOCALES = {"zh-CN", "en-US"}
DEFAULT_LOCALE = "zh-CN"

DISCLAIMERS = {
    "zh-CN": (
        "本工具仅用于就诊前信息整理与分诊辅助，不能替代医生面诊，也不能作为最终诊断依据。"
        "如症状加重或出现紧急情况，请立即前往线下医疗机构或急诊。"
    ),
    "en-US": (
        "This tool is only for pre-visit information collection and triage support. "
        "It does not replace a doctor and must not be used as a final diagnosis. "
        "Seek in-person care or emergency help if symptoms worsen or become urgent."
    ),
}

EMERGENCY_ESCALATION_MESSAGES = {
    "zh-CN": (
        "检测到您描述的症状可能存在紧急风险。请立即拨打急救电话或尽快前往最近的急诊科，"
        "不要仅依赖线上建议。"
    ),
    "en-US": (
        "The symptoms you described may indicate an urgent risk. Please call emergency services or go to the "
        "nearest emergency department immediately instead of relying only on online advice."
    ),
}

DEFAULT_ASSISTANT_QUESTIONS = {
    "zh-CN": (
        "为了让医生更快了解情况，想再确认一下：这些症状持续多久了，严重程度怎么样，"
        "另外还有没有发热、咳嗽、疼痛加重或其他不适？"
    ),
    "en-US": (
        "To help the doctor understand your situation more quickly, I still need the symptom duration, severity, "
        "and whether you also have fever, cough, worsening pain, or any other discomfort."
    ),
}

EMERGENCY_KEYWORDS = {
    "high": [
        "chest pain",
        "severe breathing difficulty",
        "shortness of breath",
        "loss of consciousness",
        "unconscious",
        "severe bleeding",
        "coughing blood",
        "胸痛",
        "胸口痛",
        "呼吸困难",
        "严重呼吸困难",
        "喘不上气",
        "失去意识",
        "昏迷",
        "严重出血",
        "大出血",
        "咯血",
    ]
}


def normalize_locale(locale):
    if locale in SUPPORTED_LOCALES:
        return locale
    return DEFAULT_LOCALE


def get_disclaimer(locale):
    return DISCLAIMERS[normalize_locale(locale)]


def get_emergency_escalation_message(locale):
    return EMERGENCY_ESCALATION_MESSAGES[normalize_locale(locale)]


def get_default_assistant_question(locale):
    return DEFAULT_ASSISTANT_QUESTIONS[normalize_locale(locale)]
