from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pipecat_flows import FlowManager


class SpecialtyNode(ABC):
    """Base class for specialty nodes."""

    def __init__(self, flow_manager: FlowManager):
        self.flow_manager = flow_manager

    @classmethod
    @abstractmethod
    def get_trigger_phrases(cls) -> List[str]:
        """Return list of phrases that should trigger this flow."""
        pass

    @abstractmethod
    def create_assessment_node(self) -> Dict[str, Any]:
        """Create the main assessment node for this specialty."""
        pass

    def create_transition_node(self, transition_message: str) -> Dict[str, Any]:
        """Create a transition node to this specialty assessment."""
        return {
            "task_messages": [
                {"role": "system", "content": f"Say: '{transition_message}'"}
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": f"continue_to_{self.__class__.__name__.lower()}",
                        "description": f"Continue to {self.__class__.__name__} assessment",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": f"{self.__class__.__name__.lower()}_assessment",
                    },
                }
            ],
        }

    async def setup(self, flow_manager: FlowManager, transition_message: str):
        """Set up the specialty flow with transition."""
        # Set transition node
        transition_node = self.create_transition_node(transition_message)
        await flow_manager.set_node(
            f"{self.__class__.__name__.lower()}_intro", transition_node
        )

        # Set assessment node
        assessment_node = self.create_assessment_node()
        await flow_manager.set_node(
            f"{self.__class__.__name__.lower()}_assessment", assessment_node
        )
