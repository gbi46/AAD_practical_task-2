# ── mas_langgraph.py ─────────────────────────────────────────────

"""
Мультиагентна система у LangGraph.
Патерн: supervisor / router
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

# ── Опис state ───────────────────────────────────────────────────
# messages зберігає історію повідомлень;
# current_agent показує, куди має перейти виконання;
# resolved сигналізує, чи вже сформовано фінальну відповідь.

class SupportState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: str
    resolved: bool

# ── LLM ──────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
)

def _last_user_message(state: SupportState) -> str:
    """
    Повертає останнє повідомлення користувача зі state.

    Це окрема допоміжна функція, щоб не дублювати однаковий код
    у triage, billing і tech вузлах.
    """
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message.content
    return ""

# ── Supervisor / triage ──────────────────────────────────────────

def triage_node(state: SupportState) -> dict:
    """
    Аналізує запит користувача і вирішує, якому агенту передати роботу.

    Повертає:
        - current_agent: billing / technical / general
        - messages: службове повідомлення від triage
        - resolved: False або True для general-відповідей
    """
    user_text = _last_user_message(state)

    prompt = (
        "Ти triage-агент служби підтримки.\n"
        "Класифікуй звернення користувача.\n"
        "Поверни лише одне слово:\n"
        "BILLING - якщо це оплата, рахунок, повернення, подвійне списання;\n"
        "TECHNICAL - якщо це технічна проблема;\n"
        "GENERAL - якщо це загальне питання.\n\n"
        f"Запит: {user_text}"
    )

    response = llm.invoke(prompt)
    category = response.content.strip().upper()

    if "BILLING" in category:
        return {
            "current_agent": "billing",
            "resolved": False,
            "messages": [AIMessage(content="[triage] Запит передано billing_agent.")],
        }

    if "TECHNICAL" in category:
        return {
            "current_agent": "technical",
            "resolved": False,
            "messages": [AIMessage(content="[triage] Запит передано tech_agent.")],
        }

    return {
        "current_agent": "general",
        "resolved": True,
        "messages": [
            AIMessage(
                content="[triage] Це загальне звернення. Координатор відповідає без делегування."
            )
        ],
    }

# ── Billing agent ────────────────────────────────────────────────

def billing_node(state: SupportState) -> dict:
    """
    Формує відповідь для billing-запиту.

    У реальній системі тут може бути виклик tool-а або підграфа,
    але для базової демонстрації достатньо окремого вузла.
    """
    user_text = _last_user_message(state)

    prompt = (
        "Ти billing_agent служби підтримки.\n"
        "Відповідай українською, коротко, професійно та конкретно.\n"
        "Поясни користувачу наступний крок.\n\n"
        f"Запит: {user_text}"
    )

    response = llm.invoke(prompt)

    return {
        "resolved": True,
        "messages": [AIMessage(content=f"[billing] {response.content}")],
    }

# ── Technical agent ──────────────────────────────────────────────

def tech_node(state: SupportState) -> dict:
    """
    Формує відповідь для технічного звернення.

    Відповідь має містити короткий покроковий план дій.
    """
    user_text = _last_user_message(state)

    prompt = (
        "Ти tech_agent служби підтримки.\n"
        "Відповідай українською.\n"
        "Сформуй короткі й зрозумілі кроки для вирішення проблеми.\n\n"
        f"Запит: {user_text}"
    )

    response = llm.invoke(prompt)

    return {
        "resolved": True,
        "messages": [AIMessage(content=f"[tech] {response.content}")],
    }

# ── Router після triage ──────────────────────────────────────────

def route_after_triage(state: SupportState) -> Literal["billing", "tech", "__end__"]:
    """
    Визначає, куди перейти після triage-вузла.

    Якщо triage визначив billing — переходимо до billing.
    Якщо technical — до tech.
    Якщо general — завершуємо виконання.
    """
    agent = state.get("current_agent", "")
    if agent == "billing":
        return "billing"
    if agent == "technical":
        return "tech"
    return "__end__"

# ── Побудова графа ───────────────────────────────────────────────

graph = StateGraph(SupportState)

graph.add_node("triage", triage_node)
graph.add_node("billing", billing_node)
graph.add_node("tech", tech_node)

graph.add_edge(START, "triage")
graph.add_conditional_edges("triage", route_after_triage)
graph.add_edge("billing", END)
graph.add_edge("tech", END)

app = graph.compile()

# ── Приклад запуску ──────────────────────────────────────────────

if __name__ == "__main__":
    result = app.invoke(
        {
            "messages": [HumanMessage(content="У мене подвійне списання з картки за квітень")],
            "current_agent": "",
            "resolved": False,
        }
    )

    for message in result["messages"]:
        print(message.content)
