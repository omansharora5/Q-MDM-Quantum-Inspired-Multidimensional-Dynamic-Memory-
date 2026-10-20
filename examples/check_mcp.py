"""Exercise the real stdio transport against the running REST service."""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    keys = json.loads(Path(".local/keys.json").read_text())
    params = StdioServerParameters(command=sys.executable, args=["-m","mnemograph.mcp_server"],
                                  env={**os.environ,"MNEMO_TOKEN":keys["developer"],"MNEMO_PLATFORM":"mcp-smoke-test"})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read,write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert {"memory_recall","memory_remember","memory_expand","memory_handoff","memory_record_message",
                    "memory_propose","memory_checkpoint","memory_claim_task","memory_ack_action","memory_forget"} <= {tool.name for tool in tools.tools}
            connected = await client.call_tool("memory_connect",{"context":"MCP transport verification"})
            assert not connected.isError, connected
            result = await client.call_tool("memory_recall",{"query":"camera"})
            assert not result.isError, result
            data = json.loads(result.content[0].text)
            assert data["handles"], data
            expanded = await client.call_tool("memory_expand",{"memory_id":data["handles"][0]["id"]})
            assert not expanded.isError
            source_text = "Synthetic MCP check: the reading session lasts twenty minutes."
            message = await client.call_tool("memory_record_message",{"message":{
                "text":source_text,"role":"user","at":"2026-10-18T12:00:00+00:00", "platform":"mcp-smoke-test",
                "dataset":"transport-check","synthetic":True,"session_id":"mcp-v2-check","idempotency_key":"mcp-v2:message"}})
            assert not message.isError, message
            source_id = json.loads(message.content[0].text)["id"]
            candidate = await client.call_tool("memory_propose",{"memory":{
                "title":"Synthetic reading session", "kind":"fact","content":"The reading session lasts twenty minutes.",
                "dataset":"transport-check","synthetic":True,"source_message_id":source_id,
                "source":{"title":"MCP source event","text":source_text}},"idempotency_key":"mcp-v2:candidate"})
            assert not candidate.isError, candidate
            memory_id = json.loads(candidate.content[0].text)["id"]
            checked = await client.call_tool("memory_expand",{"memory_id":memory_id})
            assert not checked.isError and json.loads(checked.content[0].text)["payload"]["status"] == "asserted"
            checkpoint = await client.call_tool("memory_checkpoint",{"checkpoint":{
                "objective":"Verify the v2 MCP bridge","completed":["Recorded exact source and staged candidate"],
                "memory_ids":[memory_id],"idempotency_key":"mcp-v2:checkpoint"}})
            assert not checkpoint.isError, checkpoint
            print(f"MCP stdio: {len(tools.tools)} tools discovered; connect, recall, exact evidence, message, candidate and checkpoint passed.")


if __name__ == "__main__":
    asyncio.run(main())
