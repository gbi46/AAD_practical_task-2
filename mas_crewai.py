"""
Реалізація того самого кейсу Customer Support MAS у CrewAI.
Патерн: hierarchical crew з manager_agent.
"""

import json
import os
from pathlib import Path
from tempfile import gettempdir


def _prepare_crewai_storage() -> None:
    """Keep CrewAI import usable in read-only-home sandboxes."""
    credentials_dir = Path.home() / ".local" / "share" / "crewai" / "credentials"
    try:
        credentials_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        os.environ["HOME"] = gettempdir()

    os.environ.setdefault("CREWAI_STORAGE_DIR", "AAD_practical_task-2")


from guardrails import output_guardrail, tool_guardrail, validate_tool_args
from mcp_server import get_order_status_payload, process_refund_payload, search_faq_payload


def _guarded_tool_call(agent: str, tool_name: str, args: dict) -> tuple[bool, str]:
    if not tool_guardrail(agent, tool_name):
        return False, f"{agent} не має доступу до {tool_name}."

    is_valid, message = validate_tool_args(tool_name, args)
    if not is_valid:
        return False, message

    return True, "ok"


def guarded_check_order_status(agent: str, order_id: str) -> str:
    """Shared CrewAI wrapper for the same order-status logic exposed by MCP."""
    args = {"order_id": order_id}
    allowed, message = _guarded_tool_call(agent, "check_order_status", args)
    if not allowed:
        return output_guardrail(message)

    return output_guardrail(
        json.dumps(get_order_status_payload(order_id), ensure_ascii=False)
    )


def guarded_search_faq(agent: str, query: str) -> str:
    """Shared CrewAI wrapper for FAQ lookup with per-agent tool policy."""
    args = {"query": query}
    allowed, message = _guarded_tool_call(agent, "search_faq", args)
    if not allowed:
        return output_guardrail(message)

    return output_guardrail(json.dumps(search_faq_payload(query), ensure_ascii=False))


def guarded_process_refund(
    agent: str,
    order_id: str,
    reason: str,
    human_approved: bool = False,
) -> str:
    """Shared CrewAI wrapper for refund processing with allowlist and HITL."""
    args = {"order_id": order_id, "reason": reason}
    allowed, message = _guarded_tool_call(agent, "process_refund", args)
    if not allowed:
        return output_guardrail(message)

    refund = process_refund_payload(order_id, reason, human_approved)
    return output_guardrail(json.dumps(refund, ensure_ascii=False))


def build_crew():
    """
    Створює CrewAI hierarchical crew.

    Agent creation is lazy because CrewAI initializes the configured LLM during
    Agent construction, which requires a Gemini API key.
    """
    _prepare_crewai_storage()

    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool

    @tool("check_order_status")
    def crewai_check_order_status(order_id: str) -> str:
        """Перевірити статус замовлення. Використовується orders-agent."""
        return guarded_check_order_status("orders", order_id)

    @tool("search_faq")
    def crewai_search_faq(query: str) -> str:
        """Знайти відповідь у FAQ. Використовується tech-agent."""
        return guarded_search_faq("tech", query)

    @tool("process_refund")
    def crewai_process_refund(
        order_id: str,
        reason: str,
        human_approved: bool = False,
    ) -> str:
        """Підготувати або виконати refund. Використовується лише billing-agent."""
        return guarded_process_refund("billing", order_id, reason, human_approved)

    # ── Менеджер / triage ────────────────────────────────────────
    triage_manager = Agent(
        role="Customer Support Triage Manager",
        goal="Визначити тип запиту користувача і делегувати його правильному спеціалісту",
        backstory=(
            "Ти координатор служби підтримки. "
            "Твоя задача — правильно спрямувати звернення до orders, billing або tech. "
            "Не виконуй фінансові операції самостійно."
        ),
        llm="gemini/gemini-2.5-flash",
        allow_delegation=True,
        verbose=True,
    )

    # ── Orders specialist ────────────────────────────────────────
    orders_agent = Agent(
        role="Orders Specialist",
        goal="Перевірити статус замовлення, доставку та дані відстеження",
        backstory=(
            "Ти спеціаліст із замовлень. Спочатку з'ясовуєш фактичний стан "
            "замовлення, а запити на повернення передаєш billing-спеціалісту."
        ),
        llm="gemini/gemini-2.5-flash",
        tools=[crewai_check_order_status],
        allow_delegation=False,
        verbose=True,
    )

    # ── Billing specialist ───────────────────────────────────────
    billing_agent = Agent(
        role="Billing Specialist",
        goal="Обробити питання, пов'язані з оплатами, рахунками і поверненнями коштів",
        backstory=(
            "Ти спеціаліст із фінансових запитів клієнтів. "
            "Даєш точні, короткі й практичні відповіді. "
            "Повернення коштів виконуєш тільки через process_refund і тільки "
            "після явного підтвердження оператора."
        ),
        llm="gemini/gemini-2.5-flash",
        tools=[crewai_process_refund],
        allow_delegation=False,
        verbose=True,
    )

    # ── Technical specialist ─────────────────────────────────────
    tech_agent = Agent(
        role="Technical Support Specialist",
        goal="Допомогти користувачу вирішити технічну проблему",
        backstory=(
            "Ти технічний спеціаліст. "
            "Пояснюєш рішення коротко, покроково і без зайвої теорії."
        ),
        llm="gemini/gemini-2.5-flash",
        tools=[crewai_search_faq],
        allow_delegation=False,
        verbose=True,
    )

    # ── Єдина high-level задача ──────────────────────────────────
    support_task = Task(
        description=(
            "Оброби звернення користувача: {query}\n"
            "1. Визнач, чи це orders, billing або technical.\n"
            "2. Делегуй роботу правильному спеціалісту.\n"
            "3. Якщо потрібне повернення коштів, зазнач, що process_refund потребує "
            "підтвердження оператора.\n"
            "4. Поверни користувачу фінальну відповідь українською мовою."
        ),
        expected_output=(
            "Коротка, зрозуміла відповідь українською мовою, "
            "що містить або рішення, або наступний практичний крок."
        ),
        agent=triage_manager,
    )

    # ── Crew ─────────────────────────────────────────────────────
    return Crew(
        agents=[orders_agent, billing_agent, tech_agent],
        tasks=[support_task],
        process=Process.hierarchical,
        manager_agent=triage_manager,
        verbose=True,
    )

# ── Приклад запуску ──────────────────────────────────────────────

if __name__ == "__main__":
    result = build_crew().kickoff(
        inputs={
            "query": "У мене подвійне списання з картки за березень"
        }
    )
    print(result)
