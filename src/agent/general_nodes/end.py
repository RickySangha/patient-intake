from typing import Dict, Any


def create_end_call_node(message: str) -> Dict[str, Any]:
    """Create an end call node with a custom message."""
    return {
        "task_messages": [{"role": "system", "content": f"Say: '{message}'"}],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }
