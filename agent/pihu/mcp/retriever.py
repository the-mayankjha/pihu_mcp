"""
PIHU Tool Capability Retriever — Filters registered MCP tools down to top-K relevant tools per prompt.
Prevents prompt token bloat, ensuring local Ollama models (qwen2.5, gemma3, qwen3) and Gemini run fast without 400/429 errors.
"""

import re
from typing import List, Dict, Set
from pihu.llm.base import ToolDefinition


class ToolRetriever:
    """Capability Index & Search Engine for registered MCP tools."""

    SERVER_DOMAINS: Dict[str, str] = {
        "pihu-file-mcp": "file",
        "pihu-system-mcp": "system",
        "pihu-web-search-mcp": "web",
        "google-workspace-mcp": "workspace",
        "pihu-project-mcp": "project",
    }

    # Strict domain keyword mapping to tool categories
    CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
        "file": {
            "file", "files", "directory", "folder", "read", "readme", "write", "create",
            "delete", "search", "find", "grep", "lines", "head", "tail", "hash", "copy",
            "move", "rename", "trash", "stat", "tree", "replace", "append", "path",
            "txt", "pdf", "md", "json", "py", "java", "js", "ts", "tsx", "go", "rs", "cpp",
            "code", "edit", "explore", "inspect", "check", "open", "show", "view"
        },
        "system": {
            "system", "status", "cpu", "ram", "memory", "disk", "hardware", "process",
            "processes", "pid", "uptime", "os", "command", "shell", "run", "exec",
            "notification", "battery", "hostname", "snapshot", "terminal", "kill", "ps"
        },
        "web": {
            "web", "search", "internet", "online", "browse", "url", "http", "https",
            "news", "latest", "current", "fetch", "scrape", "website", "page", "weather",
            "stock", "price", "download", "duckduckgo", "brave"
        },
        "workspace": {
            "gmail", "email", "mail", "inbox", "send", "calendar", "event", "meeting",
            "schedule", "tasks", "tasklist", "drive", "gdrive", "docs", "document"
        },
        "project": {
            "project", "scaffold", "init", "diagnose", "fix", "health", "server", "manage",
            "deploy", "start", "stop", "npm", "pip", "cargo", "vite"
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

        query_lower = query.lower()
        query_tokens = set(re.findall(r'\w+', query_lower))

        # Determine target categories
        target_categories = set()
        for cat, keywords in cls.CATEGORY_KEYWORDS.items():
            if query_tokens.intersection(keywords):
                target_categories.add(cat)

        if not target_categories:
            # Default to file and system
            target_categories = {"file", "system"}

        scored_tools = []
        for tool in all_tools:
            score = 0
            t_name_lower = tool.name.lower()
            t_desc_lower = (tool.description or "").lower()

            server_name = ""
            if tool.name in tool_map:
                server_name = tool_map[tool.name][0].lower()

            server_domain = cls.SERVER_DOMAINS.get(server_name, "")

            # If tool belongs to a targeted category, give strong boost
            if server_domain in target_categories:
                score += 15

            # If tool belongs to workspace but user didn't mention email/calendar/docs, penalize heavily
            if server_domain == "workspace" and "workspace" not in target_categories:
                score -= 50

            # Keyword matches in tool name
            for token in query_tokens:
                if len(token) < 3:
                    continue
                if token in t_name_lower:
                    score += 10
                if token in t_desc_lower:
                    score += 3

            # Exact matching for common file actions
            if "readme" in query_tokens or "read" in query_tokens:
                if tool.name in ["read_file", "read_lines", "read_head", "search_files", "stat_file"]:
                    score += 20

            if "search" in query_tokens or "find" in query_tokens:
                if "web" in target_categories and "web_search" in tool.name:
                    score += 20
                elif "file" in target_categories and ("search_files" in tool.name or "grep_search" in tool.name):
                    score += 20

            # Baseline priority for core exploration tools
            if server_domain == "file" and tool.name in ["list_directory", "read_file", "search_files", "tree"]:
                score += 5
            elif server_domain == "system" and tool.name in ["get_system_status", "run_shell"]:
                score += 3

            scored_tools.append((score, tool))

        # Sort by score descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        selected = [tool for score, tool in scored_tools if score > 0][:top_k]
        if not selected:
            # Fallback to top scored tools
            selected = [tool for score, tool in scored_tools[:top_k]]

        return selected
