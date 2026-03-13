"""Quick test for MCP server — validates tools are exposed and respond."""

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run", "context-bridge", "serve",
            "-d", "sample_project/architecture.mmd",
            "-c", "sample_project/mapping.json",
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:60]}...")

            # Test get_file_context
            result = await session.call_tool(
                "get_file_context",
                {"file_path": "services/order-service/src/api/routes.py"},
            )
            print(f"\nget_file_context result:")
            data = json.loads(result.content[0].text)
            print(json.dumps(data, indent=2))

            # Test list_services
            result = await session.call_tool("list_services", {})
            services = json.loads(result.content[0].text)
            print(f"\nlist_services: {len(services)} services")

            # Test get_service_context
            result = await session.call_tool(
                "get_service_context",
                {"service_id": "order_service"},
            )
            print(f"\nget_service_context(order_service):")
            data = json.loads(result.content[0].text)
            print(json.dumps(data, indent=2, ensure_ascii=False))

            print("\n✅ All MCP tools working correctly!")


if __name__ == "__main__":
    asyncio.run(main())
