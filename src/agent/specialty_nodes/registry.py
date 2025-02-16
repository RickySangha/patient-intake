from typing import Dict, Type, Optional
from pipecat_flows import FlowManager
from agent.specialty_nodes.base import SpecialtyNode


class NodeRegistry:
    """Registry for managing specialty flows."""

    _flows: Dict[str, Type[SpecialtyNode]] = {}

    @classmethod
    def register(cls, flow_class: Type[SpecialtyNode]):
        """Register a new specialty node."""
        cls._flows[flow_class.__name__] = flow_class
        return flow_class

    @classmethod
    def get_node_for_complaint(
        cls, complaint: str, flow_manager: FlowManager
    ) -> Optional["SpecialtyNode"]:
        """Get appropriate specialty node for a given complaint."""
        complaint_lower = complaint.lower()

        # TODO: Better way to handle complaint matching. Perhaps use similarity search using vector embeddings.

        for flow_class in cls._flows.values():
            if any(
                trigger in complaint_lower
                for trigger in flow_class.get_trigger_phrases()
            ):
                return flow_class(flow_manager)

        return None
