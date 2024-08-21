import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import psutil  # For monitoring CPU and memory usage
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from logging.handlers import RotatingFileHandler

# Constants for default values with environment variable support
DEFAULT_WEBSOCKET_SERVER_IP_ADDRESS = os.getenv("WEBSOCKET_SERVER_IP_ADDRESS", "localhost")
DEFAULT_WEBSOCKET_SERVER_PORT = int(os.getenv("WEBSOCKET_SERVER_PORT", 8765))
DEFAULT_OBS_STUDIO_WORKING_DIRECTORY = os.getenv(
    "OBS_STUDIO_WORKING_DIRECTORY", r"C:\Program Files\obs-studio\bin\64bit\\"
)
DEFAULT_OBS_STUDIO_EXECUTABLE_FILE = os.getenv("OBS_STUDIO_EXECUTABLE_FILE", "obs64.exe")
DEFAULT_OBS_STUDIO_EXECUTABLE_PATH = os.path.join(
    DEFAULT_OBS_STUDIO_WORKING_DIRECTORY, DEFAULT_OBS_STUDIO_EXECUTABLE_FILE
)

# Setup logging with rotation
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = Path('obslauncherservice.log')
handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
handler.setFormatter(log_formatter)
logger = logging.getLogger('OBSLauncherService')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Global dictionary to manage WebSocket connections and associated pids
connections: Dict[str, Dict[str, Any]] = {}

# Logging helper functions
def log_debug(message: str):
    logger.debug(message)

def log_info(message: str):
    logger.info(message)

def log_warning(message: str):
    logger.warning(message)

def log_error(message: str):
    logger.error(message)

def create_json_response(command_uid: str, status: str, message: str, data: Optional[Dict[str, Any]] = None) -> str:
    response = {
        "status": status,
        "command_uid": command_uid,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return json.dumps(response)

async def handle_connection(websocket: websockets.WebSocketServerProtocol, path: str):
    pid = str(uuid.uuid4())
    connections[pid] = {"websocket": websocket, "obs_process": None}
    log_info(f"New connection established with pid: {pid}")

    try:
        async for message in websocket:
            log_debug(f"Received message from pid {pid}: {message}")
            response = await process_message(pid, message)
            await websocket.send(response)
            log_debug(f"Sent response to pid {pid}: {response}")
    except ConnectionClosedOK:
        log_info(f"Connection closed normally for pid: {pid}")
    except ConnectionClosedError as e:
        log_warning(f"Connection closed with error for pid: {pid}: {e}")
    except Exception as e:
        log_error(f"Unexpected error with pid {pid}: {e}")
    finally:
        await cleanup_connection(pid)

async def process_message(pid: str, message: str) -> str:
    try:
        command_data = json.loads(message)
        command = command_data.get("command")
        command_uid = command_data.get("command_uid")
        parameters = command_data.get("parameter", {})

        if not command_uid or not command:
            return create_json_response(command_uid or "unknown", "error", "Both 'command' and 'command_uid' are required.")

        command_handlers = {
            "CONNECT_SERVER": connect_server,
            "DISCONNECT_SERVER": disconnect_server,
            "OPEN_OBS_STUDIO": open_obs_studio,
            "GET_OBS_STUDIO_STATUS": get_obs_studio_status,
        }

        handler = command_handlers.get(command)
        if handler:
            return await handler(command_uid, pid, parameters)
        else:
            return create_json_response(command_uid, "error", f"Unknown command: {command}")
    except json.JSONDecodeError:
        log_warning(f"Invalid JSON received from pid {pid}")
        return create_json_response("unknown", "error", "Invalid JSON format.")
    except Exception as e:
        log_error(f"Error processing message from pid {pid}: {e}")
        return create_json_response("unknown", "error", f"An unexpected error occurred: {str(e)}")

async def connect_server(command_uid: str, pid: str, parameters: Dict[str, Any]) -> str:
    ip_address = parameters.get("ip_address", DEFAULT_WEBSOCKET_SERVER_IP_ADDRESS)
    port = parameters.get("port", DEFAULT_WEBSOCKET_SERVER_PORT)
    log_info(f"WebSocket connected for pid: {pid} at {ip_address}:{port}")
    return create_json_response(command_uid, "success", "WebSocket connected successfully.", {"ip_address": ip_address, "port": port, "pid": pid})

async def disconnect_server(command_uid: str, pid: str, parameters: Dict[str, Any]) -> str:
    websocket = connections.get(pid, {}).get("websocket")
    if websocket:
        await websocket.close()
        log_info(f"WebSocket disconnected for pid: {pid}")
        return create_json_response(command_uid, "success", "WebSocket disconnected successfully.")
    else:
        log_warning(f"Attempted to disconnect nonexistent WebSocket for pid: {pid}")
        return create_json_response(command_uid, "error", "WebSocket connection not found.")

async def open_obs_studio(command_uid: str, pid: str, parameters: Dict[str, Any]) -> str:
    """Open OBS Studio."""
    if pid not in connections:
        log_warning(f"Invalid pid {pid} for OPEN_OBS_STUDIO command.")
        return create_json_response(command_uid, "error", "Invalid connection PID.")

    obs_process = connections[pid].get("obs_process")
    if obs_process and obs_process.poll() is None:
        log_info(f"OBS Studio is already running for pid: {pid}")
        return create_json_response(command_uid, "error", "OBS Studio is already running.")

    # Get the executable path and additional parameters
    executable_path = parameters.get("path", DEFAULT_OBS_STUDIO_EXECUTABLE_PATH)
    param_path = parameters.get("param_path", "")

    # Determine the working directory based on the executable path
    working_directory = os.path.dirname(executable_path)

    if not os.path.isfile(executable_path):
        log_error(f"Executable not found at path: {executable_path}")
        return create_json_response(command_uid, "error", "OBS Studio executable not found.", {"path": executable_path})

    try:
        # Prepare the command with additional parameters if provided
        command = [executable_path]
        if param_path:
            command.extend(param_path.split())

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=working_directory,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        connections[pid]["obs_process"] = process
        log_info(f"OBS Studio launched for pid: {pid} with process id: {process.pid}")
        return create_json_response(command_uid, "success", "OBS Studio launched successfully.", {"app_pid": process.pid})
    except Exception as e:
        log_error(f"Failed to launch OBS Studio for pid: {pid}: {e}")
        return create_json_response(command_uid, "error", "Failed to launch OBS Studio.", {"error": str(e)})

async def get_obs_studio_status(command_uid: str, pid: str, parameters: Dict[str, Any]) -> str:
    app_pid = parameters.get("app_pid")

    if not isinstance(app_pid, int):
        log_warning(f"Invalid app_pid provided by pid {pid}: {app_pid}")
        return create_json_response(command_uid, "error", "Invalid 'app_pid'; must be an integer.")

    try:
        process = psutil.Process(app_pid)
        if process.is_running():
            cpu_usage = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            status = process.status()
            log_info(f"Retrieved OBS Studio status for app_pid: {app_pid}")
            return create_json_response(command_uid, "success", "OBS Studio is running.", {"app_pid": app_pid, "status": status, "cpu_usage": cpu_usage, "memory_usage": memory_info.rss})
        else:
            log_warning(f"OBS Studio process with app_pid {app_pid} is not running.")
            return create_json_response(command_uid, "error", "OBS Studio is not running.")
    except psutil.NoSuchProcess:
        log_error(f"No process found with app_pid: {app_pid}")
        return create_json_response(command_uid, "error", "No OBS Studio process found with the given 'app_pid'.")
    except Exception as e:
        log_error(f"Error retrieving OBS Studio status for app_pid {app_pid}: {e}")
        return create_json_response(command_uid, "error", "Failed to retrieve OBS Studio status.", {"error": str(e)})

async def cleanup_connection(pid: str):
    connection = connections.pop(pid, None)
    if connection:
        obs_process = connection.get("obs_process")
        if obs_process and obs_process.returncode is None:
            obs_process.terminate()
            try:
                await obs_process.wait()
                log_info(f"OBS Studio process terminated for pid: {pid}")
            except Exception as e:
                log_error(f"Error terminating OBS Studio process for pid {pid}: {e}")
        log_info(f"Cleaned up connection for pid: {pid}")
    else:
        log_warning(f"No connection found to clean up for pid: {pid}")

async def start_server():
    server = await websockets.serve(handle_connection, DEFAULT_WEBSOCKET_SERVER_IP_ADDRESS, DEFAULT_WEBSOCKET_SERVER_PORT)
    log_info(f"WebSocket server started on ws://{DEFAULT_WEBSOCKET_SERVER_IP_ADDRESS}:{DEFAULT_WEBSOCKET_SERVER_PORT}")
    await server.wait_closed()

def main():
    log_info("===== OBS STUDIO WEBSOCKET LAUNCHER STARTING =====")
    try:
        asyncio.run(start_server())
    except Exception as e:
        log_error(f"Server encountered an error: {e}")
    finally:
        log_info("WebSocket server stopped.")

if __name__ == "__main__":
    main()
