import os
import sys
import logging
from typing import Tuple, Optional, Callable

# Suppress HuggingFace and Needle log noise
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

logger = logging.getLogger("NeedleRouter")
logger.setLevel(logging.INFO)

class NeedleRouter:
    def __init__(self, tool_executor: Optional[Callable[[str, dict], str]] = None):
        self.tool_executor = tool_executor
        self.agent = None
        self.available = False
        self._init_needle()

    def _init_needle(self):
        try:
            import needle

            # Define tools for Needle to route
            @needle.tool
            def full_web_search(query: str) -> str:
                """Search the web or Google for live facts, recent news, current weather, scores, or external information."""
                if self.tool_executor:
                    try:
                        return self.tool_executor("full_web_search", {"query": query})
                    except Exception as e:
                        return f"Search error: {e}"
                return "Web search completed."

            @needle.tool
            def get_single_web_page_content(url: str) -> str:
                """Fetch and extract full text content from a specific webpage URL."""
                if self.tool_executor:
                    try:
                        return self.tool_executor("get_single_web_page_content", {"url": url})
                    except Exception as e:
                        return f"Page fetch error: {e}"
                return "Page extracted."

            self.agent = needle.Needle(
                tools=[full_web_search, get_single_web_page_content]
            )
            self.available = True
            print("[Needle] 14MB Agentic Intent Router initialized and ready (28MB RAM).")
        except Exception as e:
            print(f"[Needle Warning] Could not initialize Needle router: {e}. Falling back to direct LLM mode.")
            self.available = False

    def route_query(self, user_text: str) -> Tuple[bool, Optional[str]]:
        """
        Analyzes user text to determine if a real-time web tool is genuinely required.
        Returns:
            (is_tool_call, tool_output_text)
            - If False: Conversational turn, streamed directly to Qwen in ~300ms.
            - If True: Tool executed by Needle/MCP, fresh data passed to Qwen.
        """
        if not user_text or not user_text.strip():
            return False, None

        clean = user_text.strip().lower()

        # 1. Zero-latency intent filter: only invoke search tools for genuine web/factual lookups
        search_triggers = [
            "search", "google", "look up", "lookup", "find out", "browse", "http://", "https://", "www.",
            "latest news", "breaking news", "weather in", "forecast in", "who won", "score of",
            "stock price", "current price of", "recent news about"
        ]
        
        has_search_intent = any(trigger in clean for trigger in search_triggers)
        if not has_search_intent:
            # 99% of voice agent conversation: pure zero-latency chat
            return False, None

        # 2. If genuine search intent detected, route through tool executor
        if self.tool_executor:
            try:
                # Clean up query string
                query = clean
                for prefix in ["search for", "search the web for", "google", "look up", "search"]:
                    if query.startswith(prefix):
                        query = query[len(prefix):].strip()
                if not query:
                    query = clean

                print(f"[Router] Executing live web search for: '{query}'...")
                output = self.tool_executor("full_web_search", {"query": query})
                if output and len(output.strip()) > 0:
                    print(f"[Router] Web search completed ({len(output)} chars).")
                    return True, output
            except Exception as e:
                print(f"[Router Warning] Web search error: {e}")

        return False, None
