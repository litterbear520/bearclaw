# AGENTS.md

This file provides guidance to AI coding agents working with this repository.

## What Is bearclaw

bearclaw 是通过**逆向学习** [nanobot](../AGENTS.md) 来理解 AI Agent 框架设计的项目。

**学习方法**：
1. 先让 AI 构建 nanobot 的架构全景和系统设计，理解项目到底在干什么、怎么构建的
2. 再让 AI 以 agent 应用开发工程师的视角，模拟作者从零到一百构建项目的过程，输出 roadmap
3. 跟着 roadmap 一步步用代码复现，在这个过程中理解每个模块为什么要这样设计（第一性原理）

**核心原则**：只做减法——保留 nanobot 的变量名、类名、模块结构和数据流，去掉尚未学到的模块和复杂的鲁棒性处理。**不改名、不重新设计**。

学习路线记录在 `html/nanobot-roadmap.html`，当前进度：上下文构建（ContextBuilder）已完成，正在完善 Consolidator 的 token 估算精度（对齐 nanobot 的完整 prompt 链估算）。

## Architecture

数据流与 nanobot 一致：

```
用户输入 → MessageBus(inbound) → AgentLoop → ContextBuilder → AgentRunner → Provider → LLM
                                                                    ↕
                                                               ToolRegistry
LLM响应 → session.messages → MessageBus(outbound) → 打印输出
```

### 模块对应关系（bearclaw → nanobot）

| bearclaw | nanobot | 职责 |
|----------|---------|------|
| `main.py` | `cli/commands.py` | 入口，创建总线/provider/工具/loop |
| `agent/loop.py` | `agent/loop.py` | 核心调度：消费消息→压缩→构建上下文→运行→Dream |
| `agent/runner.py` | `agent/runner.py` | 多轮 LLM 对话 + 工具执行循环 |
| `agent/context.py` | `agent/context.py` | 组装 system prompt + 历史 + 当前消息 |
| `memory/store.py` | `agent/memory.py` | MemoryStore + Consolidator（同文件，与 nanobot 一致） |
| `agent/loop.py:_run_dream` | (commands.py cron 调度) | Dream 记忆整合（nanobot 通过 process_direct ephemeral 执行） |
| `bus/` | `bus/` | MessageBus + InboundMessage/OutboundMessage |
| `providers/` | `providers/` | LLMProvider ABC → Anthropic / OpenAI 兼容实现 |
| `tools/context.py` | `agent/tools/context.py` | ToolContext dataclass（工厂方法上下文） |
| `tools/` | `agent/tools/` | Tool ABC（含 create 工厂方法）+ Registry + 自动发现 + bash/filesystem 实现 |
| `session/manager.py` | `session/manager.py` | Session dataclass + JSONL 持久化 |
| `utils/helpers.py` | `utils/helpers.py` | token 估算、模板同步 |
| `utils/prompt_templates.py` | `utils/prompt_templates.py` | Jinja2 模板渲染 |

### 关键简化点（与 nanobot 的差异）

- **同步 runner**：`AgentRunner.run()` 是同步的（nanobot 是 async），在 loop 中通过 `run_in_executor` 调用。
- **无 AutoCompact**：只有 Consolidator，无运行时自动压缩。
- **无 Hook/Governance**：无 AgentHook、ContextGovernor、注入回调。
- **无 Skills/MCP/Config**：无技能系统、MCP 连接、Pydantic 配置。
- **工具自动发现**：`tools/loader.py` 用 pkgutil 扫描，通过 `ToolContext` + `Tool.create(ctx)` 工厂方法统一注入上下文。
- **Provider 工厂**：`LLM_BACKEND` 环境变量选择 anthropic / openai_compat。

### 当前进行中

Dream 已从独立类改为 `AgentLoop._run_dream` 方法，对齐 nanobot（通过 loop 复用 runner 执行）。用户正在进行**期中复习**——通过 `html/bearclaw-architecture.html` 架构全景图回顾已完成的所有模块，确认理解后继续 roadmap。

## Constraints

- **只做减法**：保持 nanobot 的命名和结构，不重命名、不重新设计。
- **变量/函数命名对齐 nanobot**：给出代码前先查 nanobot 里对应的变量名、函数名、字段名，严格一致，不自己发明。
- **函数/方法对齐 nanobot**：nanobot 里有独立方法的逻辑（如 `_save_turn`），bearclaw 也必须写成独立方法，不能内联到调用处。先查 nanobot 的结构再给代码。
- **模块位置对齐 nanobot**：新增/移动模块时先查 nanobot 里放在哪。
- **中文交流**：解释和注释用中文。
- **同步进度**：每次代码变更后，必须更新本文件的"当前进行中"和"模块对应关系"等相关段落，同时同步 `html/bearclaw-architecture.html` 架构图。
