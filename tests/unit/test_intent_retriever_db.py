"""
Unit tests for IntentResolver, ToolRetriever, and PihuDatabase.
"""

import pytest
import pytest_asyncio
from pihu.intent.engine import IntentResolver, IntentPath
from pihu.mcp.retriever import ToolRetriever
from pihu.memory.db import PihuDatabase
from pihu.llm.base import ToolDefinition


def test_intent_resolver_fast_paths():
    path, tool, args = IntentResolver.classify("what time is it")
    assert path == IntentPath.FAST_PATH
    assert tool == "get_current_time"

    path, tool, args = IntentResolver.classify("how much memory do i have")
    assert path == IntentPath.FAST_PATH
    assert tool == "get_system_status"
    assert args.get("focus") == "memory"

    path, tool, args = IntentResolver.classify("what's cpu utilization ???")
    assert path == IntentPath.FAST_PATH
    assert tool == "get_system_status"
    assert args.get("focus") == "cpu"

    path, tool, args = IntentResolver.classify("hello")
    assert path == IntentPath.FAST_PATH
    assert tool == "greeting"

    path, tool, args = IntentResolver.classify("system snapshot")
    assert path == IntentPath.FAST_PATH
    assert tool == "get_system_snapshot"

    path, tool, args = IntentResolver.classify("list files")
    assert path == IntentPath.FAST_PATH
    assert tool == "list_directory"

    path, tool, args = IntentResolver.classify("what's in my current folder/directory")
    assert path == IntentPath.FAST_PATH
    assert tool == "list_directory"

    path, tool, args = IntentResolver.classify("write a python script to calculate fibonacci")
    assert path == IntentPath.AGENT_PATH
    assert tool is None


def test_human_formatter():
    from pihu.formatter import format_human_response
    import json

    status_data = json.dumps({
        "cpu_percent": 29.0,
        "memory": {"total_gb": 8.0, "used_gb": 5.23, "available_gb": 2.77, "percent_used": 65.4},
        "disk": {"total_gb": 465.0, "used_gb": 210.0, "free_gb": 255.0, "percent_used": 45.1}
    })

    res = format_human_response("get_system_status", status_data, {"focus": "memory"})
    assert "8.0 GB" in res
    assert "5.23 GB" in res

    res_cpu = format_human_response("get_system_status", status_data, {"focus": "cpu"})
    assert "29.0%" in res_cpu

    dir_data = json.dumps([
        {"name": "agent", "is_dir": True},
        {"name": "main.py", "is_dir": False}
    ])
    res_dir = format_human_response("list_directory", dir_data, {})
    assert "agent/" in res_dir
    assert "main.py" in res_dir


def test_tool_retriever():
    tools = [
        ToolDefinition(name="list_directory", description="List directory contents", parameters={}),
        ToolDefinition(name="read_file", description="Read text file", parameters={}),
        ToolDefinition(name="get_system_status", description="Get CPU and RAM status", parameters={}),
        ToolDefinition(name="get_current_time", description="Get current date time", parameters={}),
        ToolDefinition(name="search_nodes", description="Search memory graph nodes", parameters={}),
    ]
    tool_map = {
        "list_directory": ("pihu-file-mcp", None),
        "read_file": ("pihu-file-mcp", None),
        "get_system_status": ("pihu-system-mcp", None),
        "get_current_time": ("pihu-system-mcp", None),
        "search_nodes": ("memory", None),
    }

    selected = ToolRetriever.retrieve_relevant_tools(
        query="show system status and cpu usage",
        all_tools=tools,
        tool_map=tool_map,
        top_k=2
    )

    assert len(selected) <= 2
    selected_names = [t.name for t in selected]
    assert "get_system_status" in selected_names


@pytest.mark.asyncio
async def test_pihu_database(tmp_path):
    db_file = tmp_path / "test_pihu.db"
    db = PihuDatabase(db_path=db_file)
    await db.initialize()

    # Test memory
    await db.set_memory("user_name", "Mayank")
    val = await db.get_memory("user_name")
    assert val == "Mayank"

    # Test activity log
    await db.record_activity("TEST_EVENT", "test_target", {"key": "val"})
    logs = await db.get_recent_activities(limit=5)
    assert len(logs) == 1
    assert logs[0]["event_type"] == "TEST_EVENT"
    assert logs[0]["target"] == "test_target"
