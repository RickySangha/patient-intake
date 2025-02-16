from typing import Dict, Any, TypedDict, Literal
from pipecat_flows import FlowArgs, FlowManager


class ConsentResult(TypedDict):
    status: Literal["success", "error"]
    consent_given: bool


def create_entry_node() -> Dict[str, Any]:
    """Create the initial greeting and consent node."""
    return {
        "role_messages": [
            {
                "role": "system",
                "content": (
                    "You are Alice, an agent for the Surrey Medical Clinic. Your job is to collect important information from the user before their doctor visit. You're talking to Ricky Sangha. You should address the user by their first name and be polite and professional. You're not a medical professional, so you shouldn't provide any advice. Keep your responses short. Your job is to collect information to give to a doctor. Don't make assumptions about what values to plug into functions. Ask for clarification if a user response is ambiguous."
                    "Maintain a professional, friendly, and empathetic tone. "
                    "Speak naturally and clearly as this is a voice conversation."
                ),
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Start by introducing yourself as an automated assistant from the medical office. "
                    "Explain that you're calling to gather some information before their upcoming appointment. "
                    "Ask for their consent to collect health information."
                ),
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "process_consent",
                    "handler": verify_consent,
                    "description": "Process patient consent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "consent": {
                                "type": "boolean",
                                "description": "Did the patient give consent?",
                            }
                        },
                        "required": ["consent"],
                    },
                    "transition_callback": handle_consent_transition,
                },
            }
        ],
    }


async def verify_consent(args: FlowArgs) -> ConsentResult:
    """Process patient consent."""
    if type(args.get("consent", "")) == bool:
        consent_given = args.get("consent", "")
    elif type(args.get("consent", "")) == str:
        consent_response = args.get("consent", "").lower()
        consent_given = consent_response == "true"
    else:
        consent_given = False

    return {"status": "success", "consent_given": consent_given}


async def handle_consent_transition(
    args: Dict, result: ConsentResult, flow_manager: FlowManager
):
    """Handle transition after consent response."""
    from agent.general_nodes.chief_complaint import create_chief_complaint_node
    from agent.general_nodes.end import create_end_call_node

    if result["consent_given"]:
        flow_manager.state["consent_given"] = True
        await flow_manager.set_node("chief_complaint", create_chief_complaint_node())
    else:
        await flow_manager.set_node(
            "end_call",
            create_end_call_node(
                "I understand. I'll have a staff member contact you directly. Thank you for your time."
            ),
        )
