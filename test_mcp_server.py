"""
Unit tests для бізнес-логіки MCP-сервера.

Запуск:
    pytest test_mcp_server.py -v
"""

from mcp_server import (
    get_order_status_payload,
    get_payment_payload,
    process_refund_payload,
    search_faq_payload,
)

def test_check_order_existing():
    """Для існуючого замовлення повертається коректний словник."""
    data = get_order_status_payload("ORD-001")
    assert data["status"] == "delivered"
    assert data["total"] == 1250.00

def test_check_order_hides_pii():
    """PII-поле customer_email не повинно потрапляти у відповідь."""
    data = get_order_status_payload("ORD-001")
    assert "customer_email" not in data

def test_check_order_not_found():
    """Для неіснуючого замовлення має повертатися помилка."""
    data = get_order_status_payload("INVALID")
    assert "error" in data

def test_check_payment_existing():
    """Існуючий платіж має коректно повертатися."""
    data = get_payment_payload("PAY-001")
    assert data["status"] == "completed"
    assert data["amount"] == 1250.00

def test_check_payment_not_found():
    """Для неіснуючого платежу має повертатися помилка."""
    data = get_payment_payload("PAY-999")
    assert "error" in data

def test_refund_success():
    """Повернення виконується лише після підтвердження оператора."""
    data = process_refund_payload("ORD-001", "Дефект товару", human_approved=True)
    assert data["status"] == "processed"
    assert data["amount"] == 1250.00

def test_refund_requires_human_approval():
    """Без HITL-підтвердження повернення лишається pending."""
    data = process_refund_payload("ORD-001", "Дефект товару")
    assert data["status"] == "pending_human_approval"
    assert data["hitl_required"] is True

def test_refund_wrong_status():
    """Повернення заборонене для замовлення не у статусі delivered."""
    data = process_refund_payload("ORD-003", "Передумав")
    assert "error" in data
    assert "processing" in data["error"]

def test_refund_short_reason():
    """Причина повернення не повинна бути занадто короткою."""
    data = process_refund_payload("ORD-001", "bad")
    assert "error" in data

def test_search_faq_found():
    """Пошук повинен знаходити релевантний FAQ."""
    data = search_faq_payload("delivery")
    assert len(data) >= 1
    assert any("доставка" in item["answer"].lower() for item in data)

def test_search_faq_not_found():
    """Якщо FAQ не знайдено, має повертатися no_results."""
    data = search_faq_payload("xyznonexistent")
    assert data[0]["topic"] == "no_results"
