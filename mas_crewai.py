# ── mas_crewai.py ────────────────────────────────────────────────

"""
Реалізація того самого кейсу Customer Support MAS у CrewAI.
Патерн: hierarchical crew з manager_agent.
"""

from crewai import Agent, Crew, Process, Task

# ── Менеджер / triage ────────────────────────────────────────────
# Цей агент не виконує доменну роботу сам,
# а приймає рішення, кому делегувати задачу.

triage_manager = Agent(
    role="Customer Support Triage Manager",
    goal="Визначити тип запиту користувача і делегувати його правильному спеціалісту",
    backstory=(
        "Ти координатор служби підтримки. "
        "Твоя задача — правильно спрямувати звернення до orders, billing або tech."
    ),
    llm="gemini/gemini-2.5-flash",
    allow_delegation=True,
    verbose=True,
)

# ── Billing specialist ───────────────────────────────────────────

orders_agent = Agent(
    role="Orders Specialist",
    goal="Перевірити статус замовлення, доставку та дані відстеження",
    backstory=(
        "Ти спеціаліст із замовлень. Спочатку з'ясовуєш фактичний стан "
        "замовлення, а запити на повернення передаєш billing-спеціалісту."
    ),
    llm="gemini/gemini-2.5-flash",
    allow_delegation=False,
    verbose=True,
)

# ── Billing specialist ───────────────────────────────────────────

billing_agent = Agent(
    role="Billing Specialist",
    goal="Обробити питання, пов'язані з оплатами, рахунками і поверненнями коштів",
    backstory=(
        "Ти спеціаліст із фінансових запитів клієнтів. "
        "Даєш точні, короткі й практичні відповіді."
    ),
    llm="gemini/gemini-2.5-flash",
    allow_delegation=False,
    verbose=True,
)

# ── Technical specialist ─────────────────────────────────────────

tech_agent = Agent(
    role="Technical Support Specialist",
    goal="Допомогти користувачу вирішити технічну проблему",
    backstory=(
        "Ти технічний спеціаліст. "
        "Пояснюєш рішення коротко, покроково і без зайвої теорії."
    ),
    llm="gemini/gemini-2.5-flash",
    allow_delegation=False,
    verbose=True,
)

# ── Єдина high-level задача ──────────────────────────────────────
# Її бере на себе менеджер, а далі він делегує підзадачу відповідному агенту.

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

# ── Crew ─────────────────────────────────────────────────────────
# Для hierarchical process обов'язково задаємо manager_agent.

crew = Crew(
    agents=[orders_agent, billing_agent, tech_agent],
    tasks=[support_task],
    process=Process.hierarchical,
    manager_agent=triage_manager,
    verbose=True,
)

# ── Приклад запуску ──────────────────────────────────────────────

if __name__ == "__main__":
    result = crew.kickoff(
        inputs={
            "query": "У мене подвійне списання з картки за березень"
        }
    )
    print(result)
