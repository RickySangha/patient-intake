from typing import Dict, Any, List
from dataclasses import dataclass
from pipecat_flows import FlowArgs, FlowResult, FlowManager
from datetime import datetime

from agent.general_nodes.end import create_end_call_node
from agent.shared_handlers.handlers import handle_emergency


def create_emergency_node(emergency_reason: str) -> Dict[str, Any]:
    """Create a node for handling emergency situations."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Based on what you've told me, I need to transfer you to our medical staff immediately. "
                    "Please stay on the line while I connect you. If you're experiencing severe symptoms, "
                    "please consider calling emergency services or going to the nearest emergency room."
                ),
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "handle_emergency",
                    "handler": handle_emergency,
                    "description": "Handle emergency routing",
                    "parameters": {
                        "type": "object",
                        "properties": {"emergency_reason": {"type": "string"}},
                    },
                    "transition_callback": handle_emergency_transition,
                },
            }
        ],
        "pre_actions": [{"type": "alert_staff", "reason": emergency_reason}],
    }


async def handle_emergency(args: FlowArgs) -> FlowResult:
    """Handle emergency situation."""
    return {
        "status": "success",
        "emergency_reason": args.get("emergency_reason", "Unspecified emergency"),
    }


async def handle_emergency_transition(
    args: Dict, result: Any, flow_manager: FlowManager
):
    """Handle transition after emergency routing."""
    # Store emergency info
    flow_manager.state["emergency"] = {
        "reason": result.get("emergency_reason"),
        "timestamp": datetime.now().isoformat(),
    }

    # End conversation after emergency handling
    await flow_manager.set_node(
        "end_call",
        create_end_call_node(
            "Please stay on the line while I transfer you to our medical staff."
        ),
    )
