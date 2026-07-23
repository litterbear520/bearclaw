import asyncio

from pathlib import Path
from dotenv import load_dotenv

from bus.events import InboundMessage
from bus.queue import MessageBus
from agent.loop import AgentLoop
from tools.loader import load_tools
from providers.factory import make_provider

load_dotenv()

async def main():
    bus = MessageBus()
    provider = make_provider()
    workspace = Path.cwd()
    tools = load_tools(workspace)

    loop = AgentLoop(bus, provider, tools, workspace)
    loop_task = asyncio.create_task(loop.run())

    turn_done = asyncio.Event()
    turn_done.set()

    async def consume_outbound():
        while True:
            try:
                msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            print(msg.content)
            print()
            turn_done.set()

    outbound_task = asyncio.create_task(consume_outbound())
    print("Welcome to bearclaw!")
    io_loop = asyncio.get_event_loop()
    
    # 获取用户输入
    try:
        while True:
            try:
                query = await io_loop.run_in_executor(None, input, ">> ")
            except (EOFError, KeyboardInterrupt):
                break
            query = query.strip()
            if not query:
                continue

            turn_done.clear()
            await bus.publish_inbound(InboundMessage(
                channel="cli",
                sender_id="user",
                chat_id="cli",
                content=query
            ))
            await turn_done.wait()
    finally:
        loop._running = False
        loop_task.cancel()
        outbound_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())