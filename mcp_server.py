# ── mcp_server.py ────────────────────────────────────────────────

"""
MCP Server для Customer Support MAS.

Призначення:
    Сервер надає інструменти для роботи із замовленнями, оплатами,
    поверненнями коштів і FAQ системи підтримки клієнтів.

Запуск:
    python mcp_server.py

Тестування через Inspector:
    npx @modelcontextprotocol/inspector python mcp_server.py
"""

import json
from datetime import datetime, timezone
from typing import Any

from mcp.server.mcpserver import MCPServer

# ── Ініціалізація MCP-сервера ────────────────────────────────────

mcp = MCPServer(
    name="customer_support",
    instructions=(
        "Сервер для системи підтримки клієнтів. "
        "Надає доступ до замовлень, оплат, повернень та FAQ."
    ),
)

# ── Демонстраційні дані ──────────────────────────────────────────
# У реальній системі тут були б запити до БД або зовнішніх сервісів.

ORDERS: dict[str, dict[str, Any]] = {
    "ORD-001": {
        "status": "delivered",
        "total": 1250.00,
        "currency": "UAH",
        "date": "2026-03-15",
        "items": ["Laptop Stand", "USB-C Hub"],
        "customer_email": "alice@example.com",
    },
    "ORD-002": {
        "status": "shipped",
        "total": 890.50,
        "currency": "UAH",
        "date": "2026-03-20",
        "items": ["Wireless Mouse"],
        "tracking": "UA1234567890",
    },
    "ORD-003": {
        "status": "processing",
        "total": 2100.00,
        "currency": "UAH",
        "date": "2026-03-22",
        "items": ["Monitor 27\"", "HDMI Cable"],
    },
}

PAYMENTS: dict[str, dict[str, Any]] = {
    "PAY-001": {
        "status": "completed",
        "amount": 1250.00,
        "method": "Visa *4242",
    },
    "PAY-002": {
        "status": "pending",
        "amount": 890.50,
        "method": "Mastercard *5555",
    },
}

FAQ_DB: dict[str, str] = {
    "delivery": "Доставка займає 3-5 робочих днів по Україні.",
    "refund": "Повернення можливе протягом 14 днів після доставки.",
    "payment": "Доступні Visa, Mastercard, Apple Pay та банківський переказ.",
    "tracking": "Для відстеження використовуйте номер накладної.",
    "warranty": "Гарантія на електроніку — 12 місяців.",
    "contact": "Підтримка працює Пн-Пт 9:00-18:00. Email: support@shop.ua",
}

# ── Допоміжні функції бізнес-логіки ──────────────────────────────
# Їх спеціально винесено окремо, щоб зручно тестувати unit tests без
# залежності від transport-рівня MCP.

def get_order_status_payload(order_id: str) -> dict[str, Any]:
    """
    Повертає безпечний словник зі статусом замовлення.

    Важливо:
        customer_email навмисно не повертається,
        щоб не видавати PII навіть якщо агент або клієнт помилиться.
    """
    order = ORDERS.get(order_id)
    if not order:
        return {
            "error": f"Замовлення {order_id} не знайдено. Перевірте правильність ID."
        }

    safe_order = {k: v for k, v in order.items() if k != "customer_email"}
    return {"order_id": order_id, **safe_order}

def get_payment_payload(payment_id: str) -> dict[str, Any]:
    """Повертає інформацію про платіж або повідомлення про помилку."""
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return {"error": f"Оплата {payment_id} не знайдена."}
    return {"payment_id": payment_id, **payment}

def process_refund_payload(order_id: str, reason: str) -> dict[str, Any]:
    """
    Формує результат повернення коштів.

    Правила:
        - повернення дозволене лише для замовлень зі статусом delivered;
        - причина має бути не коротшою за 5 символів.
    """
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Замовлення {order_id} не знайдено."}

    if order["status"] != "delivered":
        return {
            "error": (
                f'Повернення неможливе: статус замовлення "{order["status"]}". '
                "Повернення дозволене лише для delivered-замовлень."
            )
        }

    if not reason or len(reason.strip()) < 5:
        return {
            "error": "Причина повернення обов'язкова і має містити щонайменше 5 символів."
        }

    return {
        "refund_id": f"REF-{order_id}",
        "order_id": order_id,
        "amount": order["total"],
        "currency": order["currency"],
        "reason": reason.strip(),
        "status": "processed",
        "estimated_days": 3,
    }

def search_faq_payload(query: str) -> list[dict[str, str]]:
    """
    Повертає список релевантних FAQ-записів.

    Логіка:
        - шукаємо збіг у ключі FAQ;
        - шукаємо збіг окремих значущих слів у тексті відповіді.
    """
    query_lower = query.lower().strip()
    results: list[dict[str, str]] = []

    for key, value in FAQ_DB.items():
        if (
            query_lower in key
            or any(word in value.lower() for word in query_lower.split() if len(word) > 3)
        ):
            results.append({"topic": key, "answer": value})

    if not results:
        return [{
            "topic": "no_results",
            "answer": f'Не знайдено FAQ для запиту: "{query}".',
        }]

    return results

# ── MCP tools ────────────────────────────────────────────────────

@mcp.tool()
def check_order_status(order_id: str) -> str:
    """
    Перевірити статус замовлення за його ID.

    Args:
        order_id: Ідентифікатор замовлення у форматі ORD-XXX.

    Returns:
        JSON-рядок із даними замовлення або повідомленням про помилку.
    """
    return json.dumps(get_order_status_payload(order_id), ensure_ascii=False, indent=2)

@mcp.tool()
def check_payment(payment_id: str) -> str:
    """
    Перевірити статус оплати.

    Args:
        payment_id: Ідентифікатор платежу у форматі PAY-XXX.

    Returns:
        JSON-рядок із даними про платіж або повідомленням про помилку.
    """
    return json.dumps(get_payment_payload(payment_id), ensure_ascii=False, indent=2)

@mcp.tool()
def process_refund(order_id: str, reason: str) -> str:
    """
    Обробити повернення коштів.

    Увага:
        Це ризикова операція. У реальній системі вона має поєднуватися
        з human-in-the-loop і журналюванням.

    Args:
        order_id: ID замовлення.
        reason: Причина повернення.

    Returns:
        JSON-рядок із результатом повернення або помилкою.
    """
    return json.dumps(process_refund_payload(order_id, reason), ensure_ascii=False, indent=2)

@mcp.tool()
def search_faq(query: str) -> str:
    """
    Пошук відповіді у FAQ.

    Args:
        query: Короткий текстовий запит користувача.

    Returns:
        JSON-рядок зі списком знайдених FAQ-записів.
    """
    return json.dumps(search_faq_payload(query), ensure_ascii=False, indent=2)

# ── MCP resource ─────────────────────────────────────────────────

@mcp.resource("support://info")
def support_info() -> str:
    """
    Повертає загальну інформацію про сервіс підтримки.

    Це приклад MCP resource, який не виконує дію, а надає контекст.
    """
    return (
        f"Customer Support System\n"
        f"Orders in DB: {len(ORDERS)}\n"
        f"FAQ topics: {len(FAQ_DB)}\n"
        f"Last updated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )

# ── Точка входу ──────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
