"""
MAS у LangGraph для Customer Support.

Граф навмисно зроблено детермінованим для демонстрації архітектури без
API-ключа: supervisor маршрутизує запит, а спеціалісти викликають ту саму
бізнес-логіку, яку MCP-сервер експонує як tools.
"""

import re
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from guardrails import input_guardrail, output_guardrail, tool_guardrail, validate_tool_args
from mcp_server import get_order_status_payload, process_refund_payload, search_faq_payload


class SupportState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: str
    order_id: str
    wants_refund: bool
    human_approved: bool
    resolved: bool


def _last_user_message(state: SupportState) -> str:
    """Повертає останній запит користувача зі state."""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _extract_order_id(text: str) -> str:
    """Витягує ID замовлення з тексту звернення."""
    match = re.search(r"\bORD-\d{3,5}\b", text.upper())
    return match.group(0) if match else ""


def _safe_tool_call(agent: str, tool: str, args: dict) -> tuple[bool, str]:
    """Єдина точка перевірки allowlist та аргументів перед tool-викликом."""
    if not tool_guardrail(agent, tool):
        return False, f"{agent} не має доступу до {tool}."
    is_valid, message = validate_tool_args(tool, args)
    if not is_valid:
        return False, message
    return True, "ok"


def triage_node(state: SupportState) -> dict:
    """Supervisor визначає маршрут і не виконує ризикових дій напряму."""
    user_text = _last_user_message(state)
    is_safe, processed = input_guardrail(user_text)
    if not is_safe:
        return {
            "current_agent": "blocked",
            "resolved": True,
            "messages": [AIMessage(content=processed)],
        }

    order_id = _extract_order_id(processed)
    lowered = processed.lower()
    wants_refund = any(word in lowered for word in ["повернення", "refund", "повернути"])

    if order_id:
        next_agent = "orders"
    elif any(word in lowered for word in ["оплата", "платіж", "карт", "billing"]):
        next_agent = "billing"
    elif any(word in lowered for word in ["сайт", "логін", "помилка", "bug", "error"]):
        next_agent = "tech"
    else:
        next_agent = "tech"

    return {
        "current_agent": next_agent,
        "order_id": order_id,
        "wants_refund": wants_refund,
        "resolved": False,
        "messages": [AIMessage(content=f"[triage] Маршрут: {next_agent}.")],
    }


def orders_node(state: SupportState) -> dict:
    """Orders-agent перевіряє статус замовлення і передає refund-запити billing."""
    order_id = state.get("order_id", "")
    allowed, message = _safe_tool_call("orders", "check_order_status", {"order_id": order_id})
    if not allowed:
        return {"resolved": True, "messages": [AIMessage(content=output_guardrail(message))]}

    order = get_order_status_payload(order_id)
    if state.get("wants_refund"):
        return {
            "current_agent": "billing",
            "messages": [
                AIMessage(
                    content=(
                        f"[orders] Замовлення {order_id}: статус {order.get('status')}. "
                        "Запит на повернення передано billing_agent."
                    )
                )
            ],
        }

    return {
        "resolved": True,
        "messages": [AIMessage(content=output_guardrail(f"[orders] Дані замовлення: {order}"))],
    }


def billing_node(state: SupportState) -> dict:
    """Billing-agent оформлює refund лише після HITL-підтвердження."""
    order_id = state.get("order_id", "")
    args = {"order_id": order_id, "reason": "Клієнт просить повернення через затримку доставки"}
    allowed, message = _safe_tool_call("billing", "process_refund", args)
    if not allowed:
        return {"resolved": True, "messages": [AIMessage(content=output_guardrail(message))]}

    refund = process_refund_payload(
        order_id=order_id,
        reason=args["reason"],
        human_approved=state.get("human_approved", False),
    )
    if "error" in refund:
        answer = f"[billing] Повернення не виконано: {refund['error']}"
    elif refund.get("status") == "pending_human_approval":
        answer = (
            f"[billing] Повернення для {order_id} підготовлено, "
            "але очікує підтвердження оператора."
        )
    else:
        answer = f"[billing] Повернення підтверджено: {refund}"
    return {"resolved": True, "messages": [AIMessage(content=output_guardrail(answer))]}


def tech_node(state: SupportState) -> dict:
    """Tech-agent працює лише з безпечним FAQ/tool-контекстом."""
    user_text = _last_user_message(state)
    allowed, message = _safe_tool_call("tech", "search_faq", {"query": user_text[:300]})
    if not allowed:
        return {"resolved": True, "messages": [AIMessage(content=output_guardrail(message))]}
    faq = search_faq_payload(user_text)
    return {"resolved": True, "messages": [AIMessage(content=output_guardrail(f"[tech] FAQ: {faq}"))]}


def route_after_triage(state: SupportState) -> Literal["orders", "billing", "tech", "__end__"]:
    """Conditional edges реалізують handoff після supervisor."""
    agent = state.get("current_agent", "")
    if agent in {"orders", "billing", "tech"}:
        return agent
    return "__end__"


def route_after_orders(state: SupportState) -> Literal["billing", "__end__"]:
    """Refund-запити після перевірки статусу переходять до billing-agent."""
    return "billing" if state.get("current_agent") == "billing" else "__end__"


graph = StateGraph(SupportState)
graph.add_node("triage", triage_node)
graph.add_node("orders", orders_node)
graph.add_node("billing", billing_node)
graph.add_node("tech", tech_node)

graph.add_edge(START, "triage")
graph.add_conditional_edges("triage", route_after_triage)
graph.add_conditional_edges("orders", route_after_orders)
graph.add_edge("billing", END)
graph.add_edge("tech", END)

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Замовлення ORD-12345 не прийшло вчасно, хочу повернення."
                )
            ],
            "current_agent": "",
            "order_id": "",
            "wants_refund": False,
            "human_approved": False,
            "resolved": False,
        }
    )
    for message in result["messages"]:
        print(message.content)
