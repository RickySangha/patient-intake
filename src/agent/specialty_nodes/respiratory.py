from typing import Dict, Any, TypedDict, Literal, List
from dataclasses import dataclass
from pipecat_flows import FlowArgs, FlowResult, FlowManager

from .registry import FlowRegistry
from .base import SpecialtyNode
from agent.general_nodes.medical_history import create_medical_history_node
from agent.general_nodes.emergency import create_emergency_node


class RespiratoryAssessmentResult(TypedDict):
    status: Literal["success", "error"]
    breathing_difficulty: str
    cough_type: str
    cough_duration: str
    sputum_presence: bool
    sputum_description: str
    associated_symptoms: List[str]
    requires_emergency: bool
    emergency_reason: str | None


@FlowRegistry.register
class RespiratoryNode(SpecialtyNode):
    """Specialty node for respiratory assessment."""

    @classmethod
    def get_trigger_phrases(cls) -> List[str]:
        return [
            "breathing problem",
            "shortness of breath",
            "difficulty breathing",
            "cough",
            "respiratory",
            "breathing difficulty",
        ]

    def create_assessment_node(self) -> Dict[str, Any]:
        return {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Continue gathering information about their breathing symptoms naturally. Ask about:\n"
                        "1. Difficulty breathing - when it occurs, severity\n"
                        "2. Cough - type (dry/wet), duration\n"
                        "3. Any mucus or phlegm\n"
                        "4. Associated symptoms\n"
                        "Ask these questions conversationally, one at a time."
                    ),
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "assess_respiratory",
                        "handler": assess_respiratory,
                        "description": "Collect detailed respiratory information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "breathing_difficulty": {
                                    "type": "string",
                                    "description": "Description of breathing difficulty",
                                },
                                "cough_type": {
                                    "type": "string",
                                    "description": "Type of cough (dry/wet)",
                                },
                                "cough_duration": {
                                    "type": "string",
                                    "description": "How long they've had the cough",
                                },
                                "sputum_presence": {
                                    "type": "boolean",
                                    "description": "Presence of mucus/phlegm",
                                },
                                "sputum_description": {
                                    "type": "string",
                                    "description": "Description of mucus/phlegm if present",
                                },
                                "associated_symptoms": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Additional symptoms",
                                },
                            },
                            "required": [
                                "breathing_difficulty",
                                "cough_type",
                                "cough_duration",
                            ],
                        },
                        "transition_callback": handle_respiratory_assessment,
                    },
                }
            ],
        }


async def assess_respiratory(args: FlowArgs) -> RespiratoryAssessmentResult:
    """Process respiratory assessment with emergency detection."""
    breathing_difficulty = args.get("breathing_difficulty", "").lower()
    associated_symptoms = args.get("associated_symptoms", [])

    # Check for emergency indicators
    emergency_indicators = [
        "severe difficulty",
        "can't breathe",
        "unable to breathe",
        "blue lips",
        "chest pain",
        "dizzy",
        "confused",
    ]

    is_emergency = any(
        indicator in breathing_difficulty for indicator in emergency_indicators
    ) or any(
        indicator in symptom.lower()
        for symptom in associated_symptoms
        for indicator in emergency_indicators
    )

    return {
        "status": "success",
        "breathing_difficulty": breathing_difficulty,
        "cough_type": args.get("cough_type", ""),
        "cough_duration": args.get("cough_duration", ""),
        "sputum_presence": args.get("sputum_presence", False),
        "sputum_description": args.get("sputum_description", ""),
        "associated_symptoms": associated_symptoms,
        "requires_emergency": is_emergency,
        "emergency_reason": (
            "Severe respiratory distress detected" if is_emergency else None
        ),
    }


async def handle_respiratory_assessment(
    args: Dict, result: RespiratoryAssessmentResult, flow_manager: FlowManager
):
    """Handle the respiratory assessment result."""
    # Store the assessment
    flow_manager.state["respiratory_assessment"] = {
        "breathing_difficulty": result["breathing_difficulty"],
        "cough_type": result["cough_type"],
        "cough_duration": result["cough_duration"],
        "sputum_presence": result["sputum_presence"],
        "sputum_description": result["sputum_description"],
        "associated_symptoms": result["associated_symptoms"],
    }

    if result["requires_emergency"]:
        await flow_manager.set_node(
            "emergency", create_emergency_node(result["emergency_reason"])
        )
    else:
        await flow_manager.set_node("medical_history", create_medical_history_node())
