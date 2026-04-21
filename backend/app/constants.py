DISCLAIMER_TEXT = (
    "本工具仅用于就诊前信息整理与分诊辅助，不能替代医生面诊，也不能作为最终诊断依据。"
    "如症状加重或出现紧急情况，请立即前往线下医疗机构或急救。"
)

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

EMERGENCY_ESCALATION_MESSAGE = (
    "检测到您描述的症状可能存在紧急风险。请立即拨打急救电话或尽快前往最近的急诊科，"
    "不要仅依赖线上咨询。"
)

DEFAULT_ASSISTANT_QUESTION = (
    "为了帮助医生更快了解情况，请补充症状持续时间、严重程度，以及是否伴随发热、咳嗽、"
    "疼痛加重或其他不适。"
)
