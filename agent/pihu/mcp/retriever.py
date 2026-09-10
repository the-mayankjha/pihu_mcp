"""
PIHU Tool Capability Retriever — Filters registered MCP tools down to top-K relevant tools per prompt.
Prevents prompt token bloat, ensuring local Ollama models (qwen2.5, gemma3, qwen3) and Gemini run fast without 400/429 errors.
"""

import re
from typing import List, Dict, Set
from pihu.llm.base import ToolDefinition


class ToolRetriever:
    """Capability Index & Search Engine for registered MCP tools."""

    # Domain keyword mapping to tool categories
    CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
        "file": {
            "file", "files", "directory", "folder", "read", "write", "create", "delete",
            "search", "find", "grep", "lines", "head", "tail", "hash", "copy", "move",
            "rename", "trash", "stat", "tree", "replace", "append", "path", "txt", "pdf",
            "md", "json", "py", "java", "js", "cpp"
        },
        "system": {
            "system", "status", "cpu", "ram", "memory", "disk", "hardware", "process",
            "processes", "pid", "uptime", "os", "command", "shell", "run", "exec",
            "notification", "battery", "hostname", "snapshot"
        },
        "time": {
            "time", "date", "clock", "timezone", "hour", "day", "week", "month", "year",
            "today", "now"
        },
        "memory": {
            "memory", "remember", "fact", "recall", "store", "know", "name", "preference",
            "history", "entity", "entities", "observation", "graph"
        },
        "fetch": {
            "fetch", "url", "http", "https", "web", "website", "page", "download", "api",
            "get", "request", "scrape"
        }
    }

    @classmethod
    def retrieve_relevant_tools(
        cls,
        query: str,
        all_tools: List[ToolDefinition],
        tool_map: Dict[str, tuple],
        top_k: int = 8
    ) -> List[ToolDefinition]:
        """
        Filter all_tools down to top_k most relevant tools based on query intent matching.
        If all_tools count is already small (<= top_k), return all_tools.
        """
        if not all_tools or len(all_tools) <= top_k:
            return all_tools

        query_tokens = set(re.findall(r'\w+', query.lower()))

        # Determine target categories
        target_categories = set()
        for cat, keywords in cls.CATEGORY_KEYWORDS.items():
            if query_tokens.intersection(keywords):
                target_categories.add(cat)

        if not target_categories:
            # Default to file and system if no specific category matched
            target_categories = {"file", "system"}

        scored_tools = []
        for tool in all_tools:
            score = 0
            t_name_lower = tool.name.lower()
            t_desc_lower = (tool.description or "").lower()

            server_name = ""
            if tool.name in tool_map:
                server_name = tool_map[tool.name][0].lower()

            # Server category match boost
            for cat in target_categories:
                if cat in server_name or cat in t_name_lower:
                    score += 5

            # Keyword matches in name and description
            for token in query_tokens:
                if len(token) < 3:
                    continue
                if token in t_name_lower:
                    score += 3
                if token in t_desc_lower:
                    score += 1

            # High priority tools boost
            high_priority = {"list_directory", "read_file", "stat_file", "write_file", "get_system_status", "get_system_snapshot", "get_current_time"}
            if tool.name in high_priority:
                score += 2

            scored_tools.append((score, tool))

        # Sort by score descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        selected = [tool for score, tool in scored_tools[:top_k]]
        return selected
