import os

from pathlib import Path
from dotenv import load_dotenv

from session.manager import SessionManager
from session.consolidator import Consolidator

from tools.loader import load_tools
from providers.factory import make_provider
from utils.prompt_templates import render_template
from memory.store import MemoryStore
from memory.dream import Dream
from agent.runner import AgentRunner, AgentRunSpec

load_dotenv()

registry = load_tools()
provider = make_provider()

SYSTEM = render_template("identity.md", workspace=os.getcwd())

        
# 主函数
if __name__ == "__main__":
    print("Welcome to bearclaw!")
    sessions = SessionManager(Path.cwd())
    session = sessions.get_or_create("default")
    store = MemoryStore(Path.cwd())
    consolidator = Consolidator(store, sessions)
    dream = Dream(store, provider)
    runner = AgentRunner()

    while True: 
        try: 
            query = input(">> ")
        except Exception:
            break

        session.messages.append({"role": "user", "content": query})
        consolidator.maybe_consolidate(session, provider, context_window=2000, max_tokens=200)

        system = SYSTEM
        if session.metadata.get("_last_summary"):
            system += f"\n\n[Archived Context Summary]\n{session.metadata['_last_summary']}"
        spec = AgentRunSpec(system=system, tools=registry, provider=provider)
        runner.run(spec, session)
        sessions.save(session)
        dream.run()
        for msg in reversed(session.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break
        print()