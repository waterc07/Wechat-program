import json

from ..constants import get_disclaimer, normalize_locale


CHAT_SYSTEM_PROMPTS = {
    "zh-CN": (
        "你是医疗预问诊助手。你的目标是帮助患者整理就诊前信息，并生成对医生有帮助的结构化背景。"
        "你不能给出最终诊断，不能声称替代医生。请用简洁、自然、专业但克制的语气回复。"
        "先简短回应患者，再提出一个最重要的补充问题。"
        "不要重复追问患者已经明确给出的信息，应优先追问尚未提供的持续时间、严重程度、最高体温、诱因或伴随症状。"
        "如果信息不足，请明确说明仍需线下医生判断。"
        "除非用户明确要求，不要使用 Markdown 标记。请使用中文回复。"
    ),
    "en-US": (
        "You are a medical pre-visit assistant. Your goal is to help patients organize information before seeing a doctor "
        "and provide structured background that is useful for clinicians. You must not give a definitive diagnosis or claim "
        "to replace a doctor. Reply in a concise, natural, professional but restrained tone. Acknowledge the patient briefly, "
        "then ask the single most important follow-up question. Do not repeat information the patient has already clearly provided; "
        "prioritize missing details such as duration, severity, highest temperature, triggers, or associated symptoms. "
        "If the information is insufficient, clearly say that in-person clinical evaluation is still needed. "
        "Do not use Markdown unless the user explicitly asks for it. Reply in English."
    ),
}

REPORT_SYSTEM_PROMPTS = {
    "zh-CN": (
        "你是医疗预问诊助手。请基于对话内容输出 JSON 对象。"
        "字段必须包括：symptoms_summary, possible_conditions, recommended_department, "
        "urgency_level, next_step_advice, disclaimer。"
        "possible_conditions 必须是字符串数组。"
        "所有内容必须保持为预问诊辅助语气，不能给出最终诊断，也不能声称替代医生。"
        "如果后续消息对前面的症状做了否定、澄清或更正，应优先采用最新澄清。"
        "请使用中文输出。"
    ),
    "en-US": (
        "You are a medical pre-visit assistant. Output a JSON object based on the conversation. "
        "The required fields are: symptoms_summary, possible_conditions, recommended_department, "
        "urgency_level, next_step_advice, disclaimer. possible_conditions must be an array of strings. "
        "All content must stay in a pre-visit assistance tone and must not provide a final diagnosis or claim to replace a doctor. "
        "If later messages negate, clarify, or correct earlier symptom descriptions, prefer the latest clarification. "
        "Please output in English."
    ),
}


def build_chat_messages(history, latest_user_message, locale="zh-CN"):
    locale = normalize_locale(locale)
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPTS[locale]}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": latest_user_message})
    return messages


def build_report_messages(conversation_messages, locale="zh-CN"):
    locale = normalize_locale(locale)
    transcript = [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in conversation_messages
    ]
    disclaimer = get_disclaimer(locale)
    user_instruction = (
        "请严格返回 JSON，不要输出 Markdown 代码块，不要添加 JSON 以外的解释。"
        if locale == "zh-CN"
        else "Return strict JSON only. Do not use Markdown code fences or add commentary outside JSON."
    )
    disclaimer_instruction = (
        f"免责声明必须为：{disclaimer}"
        if locale == "zh-CN"
        else f'The disclaimer field must be exactly: "{disclaimer}"'
    )

    return [
        {"role": "system", "content": REPORT_SYSTEM_PROMPTS[locale]},
        {"role": "user", "content": json.dumps(transcript, ensure_ascii=False)},
        {
            "role": "user",
            "content": f"{user_instruction} {disclaimer_instruction}",
        },
    ]
