from typing import Dict, Any, TypedDict, Literal, List
from pipecat_flows import FlowArgs, FlowManager
from agent.general_nodes.wrap_up import create_wrap_up_node


class Medication(TypedDict):
    name: str
    dosage: str
    frequency: str


class MedicalHistoryResult(TypedDict):
    status: Literal["success", "error"]
    conditions: List[str]
    medications: List[Medication]
    allergies: List[str]
    surgeries: List[str]


def create_medical_history_node() -> Dict[str, Any]:
    """Create a node for collecting medical history."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Now I'd like to ask about your general medical history. Ask about:\n"
                    "1. Any existing medical conditions\n"
                    "2. Current medications\n"
                    "3. Any allergies\n"
                    "4. Past surgeries\n"
                    "Ask these questions one at a time, naturally."
                ),
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_medical_history",
                    "handler": collect_medical_history,
                    "description": "Collect patient's medical history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conditions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of medical conditions",
                            },
                            "medications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "dosage": {"type": "string"},
                                        "frequency": {"type": "string"},
                                    },
                                },
                                "description": "List of current medications",
                            },
                            "allergies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of allergies",
                            },
                            "surgeries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of past surgeries",
                            },
                        },
                        "required": ["conditions", "medications", "allergies"],
                    },
                    "transition_callback": handle_medical_history_transition,
                },
            }
        ],
    }


async def collect_medical_history(args: FlowArgs) -> MedicalHistoryResult:
    """Process medical history information."""
    return {
        "status": "success",
        "conditions": args.get("conditions", []),
        "medications": args.get("medications", []),
        "allergies": args.get("allergies", []),
        "surgeries": args.get("surgeries", []),
    }


async def handle_medical_history_transition(
    args: Dict, result: MedicalHistoryResult, flow_manager: FlowManager
):
    """Handle transition after collecting medical history."""
    # Store medical history in state
    flow_manager.state["medical_history"] = {
        "conditions": result["conditions"],
        "medications": result["medications"],
        "allergies": result["allergies"],
        "surgeries": result["surgeries"],
    }

    # Move to wrap-up node
    await flow_manager.set_node("wrap_up", create_wrap_up_node())
