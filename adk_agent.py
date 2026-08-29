# ── adk_agent.py ─────────────────────────────────────────────────

"""
ADK-агент, який використовує tools з локального MCP-сервера.
Найзручніше запускати через adk web або власний Runner.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# root_agent — стандартна точка входу для ADK-проєкту
root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="support_agent",
    instruction=(
        "Ти агент підтримки клієнтів. "
        "Використовуй MCP-tools для перевірки статусу замовлення, "
        "статусу оплати, пошуку FAQ і повернення коштів. "
        "Відповідай українською мовою, коротко і професійно."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=["mcp_server.py"],
                )
            ),
            tool_filter=[
                "check_order_status",
                "check_payment",
                "search_faq",
                "process_refund",
            ],
        )
    ],
)
