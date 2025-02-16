from typing import Dict, Any, TypedDict, Literal
from dataclasses import dataclass
from pipecat_flows import FlowArgs, FlowResult, FlowManager


class ChiefComplaintResult(TypedDict):
    status: Literal["success", "error"]
    complaint: str
    duration: str


def create_chief_complaint_node() -> Dict[str, Any]:
    """Create the chief complaint collection node."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Ask: 'Could you please tell me the main reason for your appointment?' "
                    "After their response, ask about duration: 'How long have you been experiencing these symptoms?'"
                ),
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_chief_complaint",
                    "handler": collect_chief_complaint,
                    "description": "Collect chief complaint information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "complaint": {
                                "type": "string",
                                "description": "Main complaint or symptoms",
                            },
                            "duration": {
                                "type": "string",
                                "description": "How long they've had the symptoms",
                            },
                        },
                        "required": ["complaint", "duration"],
                    },
                    "transition_callback": handle_complaint_transition,
                },
            }
        ],
    }


async def collect_chief_complaint(args: FlowArgs) -> ChiefComplaintResult:
    """Process chief complaint information."""
    return {
        "status": "success",
        "complaint": args.get("complaint", ""),
        "duration": args.get("duration", ""),
    }


async def handle_complaint_transition(
    args: Dict, result: ChiefComplaintResult, flow_manager: FlowManager
):
    """Handle transition after collecting chief complaint."""
    from agent.specialty_nodes.registry import NodeRegistry
    from agent.general_nodes.medical_history import create_medical_history_node

    # Store complaint info in state
    flow_manager.state["chief_complaint"] = {
        "complaint": result["complaint"],
        "duration": result["duration"],
    }

    # TODO: Save complaint info to emr
    # FUTURE: We can run a task in the background that checks previous medical history and see if this is an emergency or if the request needs any special attention etc. Once the background task is complete it should update the flow manager state so the agent is aware.

    # Get appropriate specialty flow
    specialty_flow = NodeRegistry.get_node_for_complaint(
        result["complaint"], flow_manager
    )

    if specialty_flow:
        transition_message = (
            f"I understand you've been experiencing {result['complaint']} for {result['duration']}. "
            "I'd like to ask a few more specific questions about this to help the doctor "
            "better prepare for your appointment."
        )
        await specialty_flow.setup(flow_manager, transition_message)
    else:
        await flow_manager.set_node("medical_history", create_medical_history_node())
