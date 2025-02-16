"""Shared handlers that can be used across multiple nodes."""

from typing import Dict, Any
from dataclasses import dataclass
from pipecat_flows import FlowArgs, FlowResult, FlowManager
from datetime import datetime


async def handle_emergency(args: FlowArgs) -> FlowResult:
    """Handle emergency routing."""
    return {
        "status": "success",
        "emergency_reason": args.get("emergency_reason", "Unspecified emergency"),
        "timestamp": datetime.now().isoformat(),
    }
