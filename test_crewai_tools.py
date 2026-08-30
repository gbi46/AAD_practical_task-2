"""
Unit tests для захищених CrewAI tool-wrapper-ів.

Тести не запускають LLM/Crew kickoff. Вони перевіряють той самий security-шар,
який CrewAI agents використовують навколо бізнес-логіки MCP.
"""

import os

os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("XDG_DATA_HOME", "/tmp")

from mas_crewai import (
    guarded_check_order_status,
    guarded_process_refund,
    guarded_search_faq,
)


def test_crewai_order_tool_hides_pii():
    result = guarded_check_order_status("orders", "ORD-001")

    assert "delivered" in result
    assert "alice@example.com" not in result
    assert "customer_email" not in result


def test_crewai_triage_cannot_process_refund():
    result = guarded_process_refund("triage", "ORD-001", "Дефект товару")

    assert "не має доступу до process_refund" in result


def test_crewai_billing_refund_requires_hitl():
    result = guarded_process_refund("billing", "ORD-001", "Дефект товару")

    assert "pending_human_approval" in result
    assert '"hitl_required": true' in result


def test_crewai_refund_rejects_bad_order_id():
    result = guarded_process_refund("billing", "DROP TABLE orders", "Дефект товару")

    assert "order_id" in result


def test_crewai_faq_uses_existing_safe_logic():
    result = guarded_search_faq("tech", "delivery")

    assert "delivery" in result
    assert "Доставка" in result
