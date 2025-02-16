from typing import Dict, Any

FLOW_SETTINGS: Dict[str, Any] = {
    "context_strategy": "RESET_WITH_SUMMARY",
    "summary_prompt": "Summarize the key medical information collected so far, "
    "focusing on symptoms, history, and any red flags.",
}
