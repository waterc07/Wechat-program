import json

from ..constants import DISCLAIMER_TEXT


def build_chat_messages(history, latest_user_message):
    system_prompt = (
        "你是医疗预问诊助手。你的目标是帮助患者整理就诊前信息，并生成对医生有帮助的结构化背景。"
        "你不能给出最终诊断，不能声称替代医生。请先简洁回应患者，再提出一个最重要的补充问题。"
        "如果信息不足，请明确说明仍需线下医生判断。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": latest_user_message})
    return messages


def build_report_messages(conversation_messages):
    transcript = [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in conversation_messages
    ]
    system_prompt = (
        "你是医疗预问诊助手。请基于对话内容输出 JSON 对象。"
        "字段必须包括：symptoms_summary, possible_conditions, recommended_department, "
        "urgency_level, next_step_advice, disclaimer。"
        "possible_conditions 必须是字符串数组。"
        "所有内容必须保持为预问诊辅助语气，不能给出最终诊断，也不能声称替代医生。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(transcript, ensure_ascii=False)},
        {
            "role": "user",
            "content": (
                "请严格返回 JSON，不要输出 Markdown 代码块，不要添加 JSON 以外的解释。"
                f"免责声明必须为：{DISCLAIMER_TEXT}"
            ),
        },
    ]
