"""
Підключення локального MCP-сервера до агента LangChain.
Цей приклад демонструє завантаження tools через MultiServerMCPClient.
"""

import asyncio
import os
import sys

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

async def main() -> None:
    """
    Створює MCP-клієнт, завантажує tools і запускає агента.
    """
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise RuntimeError(
            "Gemini API key is missing. Add GOOGLE_API_KEY=your_key to the .env file."
        )

    client = MultiServerMCPClient(
        {
            "support": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["mcp_server.py"],
            }
        }
    )

    tools = await client.get_tools()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.1,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            "Ти агент підтримки клієнтів. "
            "Використовуй доступні MCP-tools, якщо для відповіді потрібні "
            "фактичні дані про замовлення, оплату або FAQ."
        ),
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Будь ласка, перевір статус замовлення ORD-002.",
                }
            ]
        }
    )

    # Результат повертається як структура повідомлень.
    # Останнє повідомлення зазвичай є фінальною відповіддю агента.
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
