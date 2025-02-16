#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import os
import subprocess
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)

MAX_BOTS_PER_ROOM = 1

# Bot sub-process dict for status reporting and concurrency control
bot_procs = {}

daily_helpers = {}


def cleanup():
    # Clean up function, just to be extra safe
    for entry in bot_procs.values():
        proc = entry[0]
        proc.terminate()
        proc.wait()


@asynccontextmanager
async def lifespan(app: FastAPI):
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )
    yield
    await aiohttp_session.close()
    cleanup()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def start_agent(request: Request, room_url: str = None):
    if room_url:
        # Use existing room
        print(f"!!! Using existing room: {room_url}")
    else:
        # Create new room
        print(f"!!! Creating new room")
        room = await daily_helpers["rest"].create_room(DailyRoomParams())
        room_url = room.url
        print(f"!!! Room URL: {room_url}")

    # Check if there is already an existing process running in this room
    num_bots_in_room = sum(
        1
        for proc in bot_procs.values()
        if proc[1] == room_url and proc[0].poll() is None
    )
    if num_bots_in_room >= MAX_BOTS_PER_ROOM:
        raise HTTPException(
            status_code=500, detail=f"Max bot limited reach for room: {room_url}"
        )

    # Get the token for the room
    token = await daily_helpers["rest"].get_token(room_url)

    if not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room_url}"
        )

    # Spawn a new agent
    try:
        proc = subprocess.Popen(
            [f"python3 -m bot -u {room_url} -t {token}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    return RedirectResponse(room_url)


@app.get("/status/{pid}")
def get_status(pid: int):
    # Look up the subprocess
    proc = bot_procs.get(pid)

    # If the subprocess doesn't exist, return an error
    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Bot with process id: {pid} not found"
        )

    # Check the status of the subprocess
    if proc[0].poll() is None:
        status = "running"
    else:
        status = "finished"

    return JSONResponse({"bot_id": pid, "status": status})


if __name__ == "__main__":
    import uvicorn

    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(description="Daily patient-intake FastAPI server")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    parser.add_argument("--port", type=int, default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Reload code on change")

    config = parser.parse_args()
    print(f"to join a test room, visit http://localhost:{config.port}/")
    print(
        f"to join a test room, visit http://localhost:{config.port}?room_url=https://cryptokiingg.daily.co/LgO4yU4YYZ9lwAt04akX"
    )
    uvicorn.run(
        "server:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
    )
