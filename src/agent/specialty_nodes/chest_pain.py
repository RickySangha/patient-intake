from typing import Dict, Any, TypedDict, Literal, List
from dataclasses import dataclass
from pipecat_flows import FlowArgs, FlowManager

from .registry import FlowRegistry
from .base import SpecialtyNode
from agent.general_nodes.medical_history import create_medical_history_node
from agent.general_nodes.emergency import create_emergency_node


class ChestPainAssessmentResult(TypedDict):
    status: Literal["success", "error"]
    pain_location: str
    pain_quality: str
    radiation: str
    associated_symptoms: List[str]
    severity: str
    aggravating_factors: List[str]
    relieving_factors: List[str]
    requires_emergency_routing: bool
    emergency_reason: str | None


@FlowRegistry.register
class ChestPainNode(SpecialtyNode):
    """Specialty node for chest pain assessment."""

    @classmethod
    def get_trigger_phrases(cls) -> List[str]:
        return [
            "chest pain",
            "chest pressure",
            "chest tightness",
            "heart pain",
            "angina",
        ]

    def create_assessment_node(self) -> Dict[str, Any]:
        return {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are assessing chest pain symptoms. Be alert for signs of emergency.",
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Carefully assess chest pain characteristics. Ask about:\n"
                        "1. Location and radiation of pain\n"
                        "2. Quality of pain (sharp, dull, pressure, etc.)\n"
                        "3. Severity (1-10 scale)\n"
                        "4. Associated symptoms\n"
                        "5. What makes it better or worse"
                    ),
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "assess_chest_pain",
                        "handler": assess_chest_pain,
                        "description": "Assess chest pain symptoms",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "pain_location": {
                                    "type": "string",
                                    "description": "Location of chest pain",
                                },
                                "pain_quality": {
                                    "type": "string",
                                    "description": "Quality of the pain (sharp, dull, etc.)",
                                },
                                "radiation": {
                                    "type": "string",
                                    "description": "Where the pain radiates to",
                                },
                                "associated_symptoms": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Other symptoms occurring with chest pain",
                                },
                                "severity": {
                                    "type": "string",
                                    "description": "Pain severity (1-10)",
                                },
                                "aggravating_factors": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "What makes the pain worse",
                                },
                                "relieving_factors": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "What makes the pain better",
                                },
                            },
                            "required": ["pain_location", "pain_quality", "severity"],
                        },
                        "transition_callback": handle_chest_pain_assessment,
                    },
                }
            ],
        }


async def assess_chest_pain(args: FlowArgs) -> ChestPainAssessmentResult:
    """Process chest pain assessment with emergency detection."""
    severity = args.get("severity", "").lower()
    associated_symptoms = args.get("associated_symptoms", [])

    # Check for emergency indicators
    emergency_indicators = [
        "severe",
        "crushing",
        "extremely painful",
        "unbearable",
        "difficulty breathing",
        "shortness of breath",
        "sweating",
        "nausea",
        "radiating to arm",
    ]

    is_emergency = any(
        indicator in severity for indicator in emergency_indicators
    ) or any(
        indicator in symptom.lower()
        for symptom in associated_symptoms
        for indicator in emergency_indicators
    )

    return ChestPainAssessmentResult(
        status="success",
        pain_location=args.get("pain_location", ""),
        pain_quality=args.get("pain_quality", ""),
        radiation=args.get("radiation", ""),
        associated_symptoms=associated_symptoms,
        severity=severity,
        aggravating_factors=args.get("aggravating_factors", []),
        relieving_factors=args.get("relieving_factors", []),
        requires_emergency_routing=is_emergency,
        emergency_reason=(
            "Potential cardiac emergency detected" if is_emergency else None
        ),
    )


async def handle_chest_pain_assessment(
    args: Dict, result: ChestPainAssessmentResult, flow_manager: FlowManager
):
    """Handle the chest pain assessment result."""
    # Store the assessment
    flow_manager.state["chest_pain_assessment"] = {
        "location": result.pain_location,
        "quality": result.pain_quality,
        "radiation": result.radiation,
        "associated_symptoms": result.associated_symptoms,
        "severity": result.severity,
        "aggravating_factors": result.aggravating_factors,
        "relieving_factors": result.relieving_factors,
    }

    if result.requires_emergency_routing:
        await flow_manager.set_node(
            "emergency", create_emergency_node(result.emergency_reason)
        )
    else:
        await flow_manager.set_node("medical_history", create_medical_history_node())
