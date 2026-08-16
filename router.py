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
        Analyzes user text using the 14MB Needle model.
        Returns:
            (is_tool_call, tool_output_text)
            - If is_tool_call is False: Query is conversational, pass directly to Qwen with 0 tools.
            - If is_tool_call is True: Tool was executed by Needle, pass output context to Qwen.
        """
        if not self.available or not self.agent:
            return False, None

        # Filter out casual greetings or short chat utterances instantly in 0ms
        clean = user_text.strip().lower()
        if any(clean.startswith(g) for g in ["hi", "hello", "hey", "how are you", "what's up", "good morning", "good evening", "what is your name", "who are you"]):
            return False, None

        try:
            res = self.agent.run(user_text, max_steps=2)
            if res and res.get("results") and len(res["results"]) > 0:
                results = res["results"]
                # If tool executed and returned substantive data
                combined_output = "\n".join(str(r) for r in results if r)
                if combined_output:
                    print(f"[Needle Router] Tool executed successfully for query: '{user_text}'")
                    return True, combined_output
        except Exception as e:
            print(f"[Needle Warning] Error during routing: {e}")

        return False, None
