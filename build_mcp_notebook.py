from pathlib import Path
from textwrap import dedent

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


OUTPUT = Path("notebooks/第3章-Agent进阶/2.3_MCP.ipynb")


def markdown(source: str):
    cell = new_markdown_cell(dedent(source).strip())
    cell.pop("id", None)
    return cell


def code(source: str):
    cell = new_code_cell(dedent(source).strip())
    cell.pop("id", None)
    return cell


def build_notebook():
    notebook = new_notebook(
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.13",
            },
        }
    )
    notebook.nbformat = 4
    notebook.nbformat_minor = 4

    notebook.cells = [
        markdown(
            """
            <div style="font: bold 40px sans-serif;">
            MCP（Model Context Protocol）
            </div>

            <br/>

            MCP 是一个开放协议，用来把外部系统提供的工具、资源和提示词，以统一方式暴露给
            LLM 应用。LangChain Agent 不再直接依赖每个服务的私有 SDK，而是通过 MCP Client
            发现并调用 MCP Server 的能力。

            本节使用项目中已经安装的 `langchain-mcp-adapters`。它负责把 MCP Server 的
            Tools 转成 LangChain `BaseTool`，然后直接传给 `create_agent`。
            """
        ),
        markdown(
            """
            ## 1. 学习目标

            学完本节后，你应该能够：

            1. 说明 MCP Host、Client、Server 三者的职责
            2. 使用 FastMCP 编写一个 stdio MCP Server
            3. 使用 `MultiServerMCPClient` 连接一个或多个 MCP Server
            4. 把 MCP Tools 加载给 LangChain Agent
            5. 读取 MCP Resources 和 Prompts
            6. 处理工具名冲突、连接生命周期和常见启动错误
            """
        ),
        markdown(
            """
            ## 2. MCP 架构

            ```mermaid
            flowchart LR
                U[用户] --> A[LangChain Agent / MCP Host]
                A --> C[MCP Client]
                C -->|stdio / HTTP / SSE| S1[本地 MCP Server]
                C -->|Streamable HTTP| S2[远程 MCP Server]
                S1 --> T1[Tools]
                S1 --> R1[Resources]
                S1 --> P1[Prompts]
                S2 --> T2[Tools]
                S2 --> R2[Resources]
            ```

            | 角色 | 职责 |
            |-----|------|
            | **Host** | 承载 LLM 和 Agent，决定何时调用外部能力 |
            | **Client** | 与一个或多个 Server 建立协议连接，发现并调用能力 |
            | **Server** | 对外暴露 Tools、Resources、Prompts |

            MCP Server 中最常见的是 Tool。Resource 更适合提供只读上下文，Prompt 更适合提供
            可复用的提示词模板。
            """
        ),
        markdown(
            """
            ## 3. 安装与版本

            本项目使用：

            - `langchain-mcp-adapters`
            - `mcp`
            - `langchain`

            在 Notebook 中直接运行下面代码可以确认解释器和依赖信息。
            """
        ),
        code(
            """
            import asyncio
            import json
            import sys
            import tempfile
            from pathlib import Path

            import mcp
            import langchain_mcp_adapters
            from dotenv import load_dotenv
            from importlib.metadata import version

            load_dotenv()

            print("Python:", sys.executable)
            print("MCP SDK:", version("mcp"))
            print("langchain-mcp-adapters:", version("langchain-mcp-adapters"))
            """
        ),
        markdown(
            """
            ## 4. 编写一个本地 MCP Server

            下面的 Server 提供：

            - `add`：加法工具
            - `get_course_info`：返回课程信息
            - `course://outline`：课程大纲 Resource
            - `study_plan`：生成学习计划的 Prompt

            为了保持 Notebook 自包含，Server 代码会写入系统临时目录。随后 Client 使用
            `sys.executable` 启动它，确保子进程和当前 Notebook 使用同一个 Python 虚拟环境。
            """
        ),
        code(
            r'''
            SERVER_PATH = Path(tempfile.gettempdir()) / "langchain_course_mcp_server.py"

            SERVER_CODE = r"""
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP(
                name="langchain-course-demo",
                instructions="提供课程演示用的计算、课程信息和学习计划能力。",
            )


            @mcp.tool()
            def add(a: float, b: float) -> float:
                return a + b


            add.__doc__ = "计算两个数字之和。"


            @mcp.tool()
            def get_course_info(topic: str) -> dict:
                catalog = {
                    "mcp": {
                        "title": "MCP 与 LangChain 集成",
                        "level": "agent-advanced",
                        "duration_minutes": 90,
                    },
                    "middleware": {
                        "title": "LangChain Middleware",
                        "level": "agent-advanced",
                        "duration_minutes": 75,
                    },
                }
                key = topic.strip().lower()
                return catalog.get(
                    key,
                    {
                        "title": f"未找到主题：{topic}",
                        "level": "unknown",
                        "duration_minutes": 0,
                    },
                )


            get_course_info.__doc__ = "返回指定主题的课程信息。"


            @mcp.resource("course://outline")
            def course_outline() -> str:
                return (
                    "1. Runtime\\n"
                    "2. Middleware\\n"
                    "3. MCP Server 与 Client\\n"
                    "4. Agent 工具集成\\n"
                    "5. 资源、提示词与故障排查"
                )


            course_outline.__doc__ = "返回第三章的学习大纲。"


            @mcp.prompt()
            def study_plan(topic: str, level: str = "beginner") -> str:
                return (
                    f"请为 {level} 学习者制定 {topic} 的七天学习计划。"
                    "每天包含目标、练习和验收标准。"
                )


            study_plan.__doc__ = "生成一个可复用的学习计划提示词。"


            if __name__ == "__main__":
                mcp.run(transport="stdio")
            """

            SERVER_PATH.write_text(SERVER_CODE.strip() + "\\n", encoding="utf-8")
            print(SERVER_PATH)
            '''
        ),
        markdown(
            """
            ### 4.1 Server 代码中的关键点

            | 写法 | 作用 |
            |-----|------|
            | `FastMCP(...)` | 创建 MCP Server |
            | `@mcp.tool()` | 把普通 Python 函数注册为工具 |
            | `@mcp.resource("course://outline")` | 注册只读资源 |
            | `@mcp.prompt()` | 注册可复用提示词模板 |
            | `mcp.run(transport="stdio")` | 通过标准输入输出与 Client 通信 |

            stdio Server 不能向标准输出打印日志，否则会破坏协议数据。服务端日志应写入
            stderr 或日志文件。
            """
        ),
        markdown(
            """
            ## 5. 创建 MCP Client

            `MultiServerMCPClient` 的 connections 字典按 Server 名称组织配置：

            ```python
            {
                "server_name": {
                    "transport": "...",
                    ...
                }
            }
            ```

            本地 Python 脚本使用 `stdio`。`cwd` 指定子进程工作目录，`args` 必须使用绝对路径。
            """
        ),
        code(
            """
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient(
                {
                    "course": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(SERVER_PATH)],
                        "cwd": str(SERVER_PATH.parent),
                    }
                }
            )

            print(client.connections["course"])
            """
        ),
        markdown(
            """
            ## 6. 发现 MCP Tools

            `await client.get_tools()` 会连接 Server、执行 `tools/list`，并把 MCP Tool
            转换成 LangChain Tool。

            默认情况下，每次工具调用都可能创建新会话，适合无状态工具。需要 Resource、
            Prompt 或共享会话状态时，后面会使用显式 `client.session(...)`。
            """
        ),
        code(
            """
            tools = await client.get_tools()

            print(f"发现 {len(tools)} 个工具")
            for tool in tools:
                print(f"- {tool.name}: {tool.description}")
            """
        ),
        markdown(
            """
            ## 7. 直接调用 MCP Tool

            转成 LangChain Tool 后，可以像普通 Tool 一样调用：

            - 同步：`tool.invoke(args)`
            - 异步：`await tool.ainvoke(args)`

            在 Jupyter 中优先使用异步调用，避免和事件循环冲突。
            """
        ),
        code(
            """
            tools_by_name = {tool.name: tool for tool in tools}

            add_result = await tools_by_name["add"].ainvoke({"a": 18, "b": 24})
            course_result = await tools_by_name["get_course_info"].ainvoke(
                {"topic": "mcp"}
            )

            print("18 + 24 =", add_result)
            print(json.dumps(course_result, ensure_ascii=False, indent=2))
            """
        ),
        markdown(
            """
            ## 8. 把 MCP Tools 交给 LangChain Agent

            这里的关键只有一行：`create_agent(..., tools=tools)`。

            Agent 看到的是 LangChain Tool，不需要知道它来自本地 stdio Server 还是远程
            Streamable HTTP Server。
            """
        ),
        code(
            """
            from langchain.agents import create_agent
            from langchain.messages import HumanMessage

            agent = create_agent(
                "deepseek-chat",
                tools=tools,
                system_prompt=(
                    "你是课程助手。计算时必须调用 add 工具，"
                    "查询课程信息时必须调用 get_course_info 工具。"
                ),
            )

            response = await agent.ainvoke(
                {
                    "messages": [
                        HumanMessage(
                            "请先计算 12 + 30，再告诉我 MCP 课程需要多少分钟。"
                        )
                    ]
                }
            )

            for message in response["messages"]:
                message.pretty_print()
            """
        ),
        markdown(
            """
            ## 9. 支持的连接方式

            `langchain-mcp-adapters` 支持多种 transport：

            | transport | 适合场景 | 关键字段 |
            |----------|---------|---------|
            | `stdio` | 本地脚本、IDE 工具、命令行服务 | `command`、`args`、`cwd` |
            | `streamable_http` | 远程、多用户、标准 HTTP 服务 | `url`、`headers` |
            | `sse` | 兼容旧版 Server-Sent Events | `url` |
            | `websocket` | 长连接双向通信 | `url` |

            远程连接通常需要认证。认证信息应通过环境变量注入，而不是直接写死在 Notebook 中。
            """
        ),
        code(
            """
            docs_client = MultiServerMCPClient(
                {
                    "langchain_docs": {
                        "transport": "streamable_http",
                        "url": "https://docs.langchain.com/mcp",
                    }
                }
            )

            # 需要联网时再执行：
            # docs_tools = await docs_client.get_tools(
            #     server_name="langchain_docs"
            # )
            print(docs_client.connections["langchain_docs"])
            """
        ),
        markdown(
            """
            ## 10. Resources 与 Prompts

            Tools 不是 MCP 的唯一能力：

            - `load_mcp_resources`：列出 Server 中的资源
            - `get_mcp_resource`：按 URI 读取资源
            - `load_mcp_prompt`：读取 Prompt 并转换成 LangChain Messages

            这些能力需要显式打开一个 `ClientSession`，可以在同一会话内连续操作。
            """
        ),
        code(
            """
            from langchain_mcp_adapters.prompts import load_mcp_prompt
            from langchain_mcp_adapters.resources import (
                get_mcp_resource,
                load_mcp_resources,
            )

            async with client.session("course") as session:
                resources = await load_mcp_resources(session)
                outline_blobs = await get_mcp_resource(session, "course://outline")
                prompt_messages = await load_mcp_prompt(
                    session,
                    "study_plan",
                    arguments={"topic": "MCP", "level": "beginner"},
                )

            print("资源数量:", len(resources))
            print("大纲:")
            print(outline_blobs[0].as_string())

            print("\\nPrompt 转换后的消息:")
            for message in prompt_messages:
                message.pretty_print()
            """
        ),
        markdown(
            """
            ## 11. 读取 Server 信息

            `get_server_info` 返回 Server 名称、版本、协议版本和 capabilities，适合在正式
            接入前做兼容性检查。
            """
        ),
        code(
            """
            server_info = await client.get_server_info(server_name="course")
            info = server_info["course"]

            print(info.model_dump_json(indent=2))
            """
        ),
        markdown(
            """
            ## 12. 多 Server 与工具名冲突

            多个 Server 可能暴露同名工具，例如两个 Server 都有 `search`。解决方式：

            ```python
            client = MultiServerMCPClient(
                connections,
                tool_name_prefix=True,
            )
            ```

            开启后，工具名会带上 Server 名称，例如 `course_add`。
            对多 Server 系统，建议始终开启前缀。
            """
        ),
        code(
            """
            prefixed_client = MultiServerMCPClient(
                {
                    "course": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(SERVER_PATH)],
                        "cwd": str(SERVER_PATH.parent),
                    }
                },
                tool_name_prefix=True,
            )

            prefixed_tools = await prefixed_client.get_tools()
            print([tool.name for tool in prefixed_tools])
            """
        ),
        markdown(
            """
            ## 13. 生命周期与性能

            有两种连接方式：

            | 方式 | 特点 | 适用场景 |
            |-----|------|---------|
            | `client.get_tools()` | 每次工具调用创建会话 | 无状态工具、简单接入 |
            | `async with client.session(...)` | 显式控制会话生命周期 | Resources、Prompts、连续调用 |

            对高频调用，可以在业务服务启动时创建长生命周期 Client，并在应用关闭时清理连接。
            """
        ),
        markdown(
            """
            ## 14. 常见问题

            | 现象 | 常见原因 | 处理方式 |
            |-----|---------|---------|
            | Server 启动失败 | `command` 不是当前虚拟环境解释器 | 使用 `sys.executable` |
            | 找不到 Server 文件 | 相对路径受 `cwd` 影响 | 使用绝对路径 |
            | 协议解析错误 | Server 向 stdout 打印日志 | 日志写入 stderr |
            | `asyncio.run()` 报错 | Jupyter 已有运行中的事件循环 | 直接使用顶层 `await` |
            | 远程连接 401/403 | 缺少 Bearer Token 或 OAuth | 通过 `headers` 注入认证 |
            | Agent 找不到工具 | 工具没有传给 `create_agent` | 检查 `tools=[...]` |

            MCP 工具可以执行真实操作，因此只连接可信 Server。写操作、付费操作和删除操作
            应额外增加权限校验或 Human-in-the-loop。
            """
        ),
        markdown(
            """
            ## 15. 与新版 `langchain.mcp.MCPAdapter` 的关系

            LangChain 1.4 开始提供 beta 版 `langchain.mcp.MCPAdapter`，它基于 FastMCP，
            使用体验更简洁。当前项目依赖的是稳定的 `langchain-mcp-adapters`，并且当前环境
            没有安装它所需的 `fastmcp` extra，因此本节使用
            `MultiServerMCPClient`。

            两种方式的核心思想相同：先发现 MCP Tools，再转成 LangChain Tools，最后交给
            `create_agent`。
            """
        ),
        markdown(
            """
            ## 16. 总结

            1. MCP 用统一协议连接 Agent 与外部工具、资源、提示词
            2. 本地工具使用 stdio Server，远程服务通常使用 Streamable HTTP
            3. `MultiServerMCPClient.get_tools()` 把 MCP Tools 转成 LangChain Tools
            4. `create_agent(..., tools=tools)` 即可让 Agent 使用这些工具
            5. Resources 和 Prompts 需要显式 ClientSession
            6. 多 Server 场景应开启 `tool_name_prefix`
            7. 高风险工具必须配合权限控制和人工审核
            """
        ),
        markdown(
            """
            ---

            **更多资源**

            - [LangChain MCP 文档](https://docs.langchain.com/oss/python/langchain/mcp)
            - [MCP 官方协议](https://modelcontextprotocol.io)
            - [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
            - [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
            """
        ),
    ]

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(f"Created {OUTPUT} with {len(notebook.cells)} cells.")


if __name__ == "__main__":
    build_notebook()
