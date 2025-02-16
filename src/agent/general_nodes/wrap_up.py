from typing import Dict, Any
from pipecat_flows import FlowManager
from agent.general_nodes.end import create_end_call_node


def create_wrap_up_node() -> Dict[str, Any]:
    """Create a node for wrapping up the conversation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Thank the patient for their time and summarize the key information collected. "
                    "Let them know that this information will be reviewed by their healthcare provider "
                    "before their appointment. Ask if they have any questions before ending the call."
                ),
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "finish_conversation",
                    "description": "End the conversation",
                    "parameters": {"type": "object", "properties": {}},
                    "transition_callback": handle_wrap_up_transition,
                },
            }
        ],
    }


async def handle_wrap_up_transition(
    args: Dict, result: Dict[str, Any], flow_manager: FlowManager
):
    """Handle the wrap-up transition."""
    await flow_manager.set_node(
        "end_call", create_end_call_node("Thank you for your time. Goodbye!")
    )
