"""
Базове налаштування tracing для LangSmith та приклади ручного трасування.
"""

import re

from langsmith import traceable

# ── LangSmith: базове ввімкнення трасування ──────────────────────
# Ці змінні встановлюються у shell ДО запуску агентів:
# export LANGSMITH_TRACING=true
# export LANGSMITH_API_KEY=<your_langsmith_key>
# export LANGSMITH_PROJECT=practice-2-customer-support

# ── Приклади кастомного трасування ───────────────────────────────

@traceable(name="input_guardrail")
def traced_input_guardrail(text: str) -> tuple[bool, str]:
    """
    Приклад input guardrail з трасуванням у LangSmith.
    """
    patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"system\s+prompt",
        r"reveal\s+your\s+prompt",
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Запит заблоковано з міркувань безпеки."
    return True, text

@traceable(name="output_guardrail")
def traced_output_guardrail(text: str) -> str:
    """
    Приклад output guardrail з трасуванням у LangSmith.
    """
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL_REDACTED]", text)
    return text

# ── Варіант для Langfuse (закоментований) ────────────────────────
# Якщо використовується Langfuse, можна підключити observe-декоратор:

# import os
# from langfuse import observe
#
# os.environ["LANGFUSE_PUBLIC_KEY"] = "pk_your_public_key"
# os.environ["LANGFUSE_SECRET_KEY"] = "sk_your_secret_key"
# os.environ["LANGFUSE_HOST"] = "<https://cloud.langfuse.com>"
#
# @observe(name="input_guardrail")
# def traced_input_guardrail_langfuse(text: str) -> tuple[bool, str]:
#     import re
#     patterns = [r"ignore\s+(all\s+)?previous", r"system\s+prompt"]
#     for pattern in patterns:
#         if re.search(pattern, text, re.IGNORECASE):
#             return False, "Запит заблоковано з міркувань безпеки."
#     return True, text
#
# @observe(name="output_guardrail")
# def traced_output_guardrail_langfuse(text: str) -> str:
#     import re
#     return re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL_REDACTED]", text)
