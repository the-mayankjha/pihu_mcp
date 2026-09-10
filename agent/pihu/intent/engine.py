"""
PIHU Fast Intent Engine — Deterministic classifier routing prompts to Fast Path or Agent Path.
Extremely fast natural language matching for common queries (< 5ms execution).
"""

import re
from enum import Enum
from typing import Optional, Tuple, Dict, Any


class IntentPath(str, Enum):
    FAST_PATH = "fast_path"
    AGENT_PATH = "agent_path"


class IntentResolver:
    """Fast, deterministic intent classifier that bypasses LLM inference for common queries."""

    @staticmethod
    def classify(prompt: str) -> Tuple[IntentPath, Optional[str], Optional[Dict[str, Any]]]:
        """
        Classify prompt intent.
        Returns (path, tool_name, tool_arguments) if FAST_PATH, else (AGENT_PATH, None, None).
        """
        text = prompt.lower().strip()
        # Remove trailing punctuation like ??? or !!! or ...
        clean_text = re.sub(r'[\?!\.\,]+$', '', text).strip()

        # Greetings & Courtesy
        greetings = {"hi", "hello", "hey", "hii", "hiii", "yo", "sup", "good morning", "good afternoon", "good evening"}
        if clean_text in greetings:
            return IntentPath.FAST_PATH, "greeting", {"text": "Hey! 👋 How can I help you today?"}

        if clean_text in {"thanks", "thank you", "thx", "ty", "cheers"}:
            return IntentPath.FAST_PATH, "greeting", {"text": "You're welcome! 😊 Let me know if you need anything else."}

        if clean_text in {"bye", "goodbye", "cya"}:
            return IntentPath.FAST_PATH, "greeting", {"text": "Goodbye! 👋 Have a great day!"}

        # System Time & Date queries
        time_patterns = [
            r"time", r"date", r"clock", r"today",
            r"what(?:'s|\s+is)\s+the\s+time",
            r"what\s+time\s+is\s+it",
            r"current\s+time",
            r"time\s+now",
            r"what(?:'s|\s+is)\s+the\s+date",
            r"what\s+date\s+is\s+it",
            r"current\s+date",
            r"today(?:'s|\s+is)\s+date",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in time_patterns if len(p) > 3) or clean_text in {"time", "date", "clock"}:
            return IntentPath.FAST_PATH, "get_current_time", {"timezone": "Asia/Kolkata"}

        # Memory / RAM queries
        memory_patterns = [
            r"memory", r"ram",
            r"how\s+much\s+(?:memory|ram)",
            r"free\s+(?:memory|ram)",
            r"available\s+(?:memory|ram)",
            r"used\s+(?:memory|ram)",
            r"ram\s+usage",
            r"memory\s+usage",
            r"memory\s+status",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in memory_patterns if len(p) > 3) or clean_text in {"memory", "ram"}:
            return IntentPath.FAST_PATH, "get_system_status", {"focus": "memory"}

        # CPU / Processor queries
        cpu_patterns = [
            r"cpu", r"processor",
            r"cpu\s+usage", r"cpu\s+utilization", r"cpu\s+load", r"cpu\s+status",
            r"what(?:'s|\s+is)\s+cpu", r"processor\s+usage",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in cpu_patterns if len(p) > 3) or clean_text in {"cpu", "processor"}:
            return IntentPath.FAST_PATH, "get_system_status", {"focus": "cpu"}

        # Storage / Disk queries
        disk_patterns = [
            r"disk", r"storage", r"space", r"hard\s+drive", r"ssd",
            r"how\s+much\s+(?:disk|storage|space)",
            r"disk\s+space", r"storage\s+space", r"free\s+space",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in disk_patterns if len(p) > 3) or clean_text in {"disk", "storage"}:
            return IntentPath.FAST_PATH, "get_system_status", {"focus": "disk"}

        # Battery / Power queries
        battery_patterns = [
            r"battery", r"power", r"battery\s+status", r"battery\s+level", r"charge",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in battery_patterns if len(p) > 3) or clean_text in {"battery"}:
            return IntentPath.FAST_PATH, "get_system_status", {"focus": "battery"}

        # Overall System Status & Snapshot
        system_patterns = [
            r"system\s+status", r"system\s+snapshot", r"system\s+overview", r"machine\s+status",
            r"system\s+info", r"machine\s+info", r"os\s+info", r"what\s+os", r"uptime",
        ]
        if any(re.search(r'\b' + p + r'\b', clean_text) for p in system_patterns if len(p) > 3):
            return IntentPath.FAST_PATH, "get_system_snapshot", {}

        # Directory listing (fast path for root / current dir)
        list_patterns = [
            r"^list\s+(?:my\s+)?files$",
            r"^show\s+files$",
            r"^list\s+directory$",
            r"^ls$",
            r"^dir$",
            r"what(?:'s|\s+is)\s+in\s+(?:my\s+)?(?:current\s+)?(?:folder|directory)",
            r"show\s+(?:my\s+)?(?:current\s+)?(?:folder|directory)\s+contents?",
            r"files?\s+in\s+(?:my\s+)?(?:current\s+)?(?:folder|directory)",
        ]
        if any(re.search(p, clean_text) for p in list_patterns):
            return IntentPath.FAST_PATH, "list_directory", {"path": "."}

        # Tree view
        tree_patterns = [
            r"^tree$",
            r"^directory\s+tree$",
            r"^file\s+tree$",
        ]
        if any(re.search(p, clean_text) for p in tree_patterns):
            return IntentPath.FAST_PATH, "tree", {"path": ".", "depth": 3}

        # Everything else goes through the AGENT_PATH
        return IntentPath.AGENT_PATH, None, None
