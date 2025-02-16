import argparse
import asyncio
import os
from dotenv import load_dotenv
import aiohttp
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.openai import OpenAILLMService, OpenAILLMContext
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat_flows import FlowManager
from pipecat.processors.logger import FrameLogger
from agent.general_nodes.entry import create_entry_node
from runner import configure  # Import the configure helper

load_dotenv(override=True)


async def initialize_medical_intake(task, llm, context_aggregator):
    """Initialize the medical intake system."""
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
    )

    # Initialize flow manager
    await flow_manager.initialize()

    return flow_manager


async def main():
    async with aiohttp.ClientSession() as session:
        # Use configure helper to get room URL and token
        (url, token) = await configure(session)

        # Initialize transport with Daily
        transport = DailyTransport(
            url,
            token,
            "Medical Assistant",
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
                vad_audio_passthrough=True,  # Added this parameter
            ),
        )

        # Initialize services
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id=os.getenv(
                "CARTESIA_VOICE_ID", "79a125e8-cd45-4c13-8a67-188112f4dd22"
            ),
        )

        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

        # Create context and pipeline
        context = OpenAILLMContext(messages=[])
        context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline(
            [
                transport.input(),
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        # Initialize flow manager
        flow_manager = FlowManager(
            task=task,
            llm=llm,
            context_aggregator=context_aggregator,
            tts=tts,  # Added TTS service
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            logger.debug("Initializing flow")
            await flow_manager.initialize()
            # Start the entry flow
            entry_node = create_entry_node()
            await flow_manager.set_node("initial", entry_node)

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
