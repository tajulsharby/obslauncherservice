# OBS Studio Launcher Service

The **OBS Studio Launcher Service** is a WebSocket-based service designed to remotely manage the OBS Studio application. This service allows clients to connect, launch OBS Studio, retrieve its status, and more through simple WebSocket commands.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [WebSocket Commands](#websocket-commands)
    - [CONNECT_SERVER](#connect_server)
    - [DISCONNECT_SERVER](#disconnect_server)
    - [OPEN_OBS_STUDIO](#open_obs_studio)
    - [GET_OBS_STUDIO_STATUS](#get_obs_studio_status)
- [Client Demo](#client-demo)
- [Contributing](#contributing)
- [License](#license)

## Features

- **WebSocket-Based Communication**: Allows remote control of OBS Studio through WebSocket connections.
- **Cross-Platform Compatibility**: Works on both Windows and Unix-based systems (with some platform-specific considerations).
- **Logging and Monitoring**: Includes detailed logging and status monitoring for easy debugging and management.
- **Graceful Shutdown**: Ensures proper cleanup of resources when the service is terminated.

## Installation

### Prerequisites

- **Python 3.7+**: Make sure you have Python installed. You can download it from the [official Python website](https://www.python.org/downloads/).
- **OBS Studio**: The service is designed to work with OBS Studio, which should be installed on the same machine.

### Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/tajulsharby/obslauncherservice.git
   cd obslauncherservice
   ```

2. **Install Dependencies**:
   Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Service**:
   Start the WebSocket service:
   ```bash
   python obslauncherservice.py
   ```

## Configuration

The service can be configured using environment variables:

- `WEBSOCKET_SERVER_IP_ADDRESS`: The IP address the WebSocket server will bind to (default: `localhost`).
- `WEBSOCKET_SERVER_PORT`: The port the WebSocket server will listen on (default: `8765`).
- `OBS_STUDIO_WORKING_DIRECTORY`: The working directory for OBS Studio (default: `C:\Program Files\obs-studio\bin\64bit\\`).
- `OBS_STUDIO_EXECUTABLE_FILE`: The name of the OBS Studio executable file (default: `obs64.exe`).

You can set these variables in your environment or create a `.env` file in the project root.

## Usage

### WebSocket Commands

The service accepts the following WebSocket commands. Each command is sent as a JSON object, and the service responds with a JSON object.

#### CONNECT_SERVER

Establishes a connection with the WebSocket server.

**Command Format**:
```json
{
  "command": "CONNECT_SERVER",
  "command_uid": "<client_generated_uid>",
  "parameter": {
    "ip_address": "<optional_websocket_server_ip_address>",
    "port": "<optional_websocket_server_port>"
  }
}
```

**Response Format**:
```json
{
  "status": "success",
  "command_uid": "<ping_back_the_client_generated_uid>",
  "message": "WebSocket connected successfully",
  "data": {
    "ip_address": "<websocket_server_ip_address>",
    "port": "<websocket_server_port>",
    "pid": "<assigned_connection_pid>"
  }
}
```

#### DISCONNECT_SERVER

Disconnects from the existing WebSocket server.

**Command Format**:
```json
{
  "command": "DISCONNECT_SERVER",
  "command_uid": "<client_generated_uid>",
  "parameter": {
    "pid": "<connection_pid>"
  }
}
```

**Response Format**:
```json
{
  "status": "success",
  "command_uid": "<ping_back_the_client_generated_uid>",
  "message": "WebSocket disconnected successfully"
}
```

#### OPEN_OBS_STUDIO

Launches the OBS Studio application.

**Command Format**:
```json
{
  "command": "OPEN_OBS_STUDIO",
  "command_uid": "<client_generated_uid>",
  "parameter": {
    "path": "<optional_obs_studio_executable_path>"
  }
}
```

**Response Format**:
```json
{
  "status": "success",
  "command_uid": "<ping_back_the_client_generated_uid>",
  "message": "OBS Studio launched successfully",
  "data": {
    "uid": "<assigned_connection_pid>",
    "path": "<obs_studio_executable_path>",
    "app_pid": "<obs_studio_process_pid>"
  }
}
```

#### GET_OBS_STUDIO_STATUS

Retrieves the status of the running OBS Studio process.

**Command Format**:
```json
{
  "command": "GET_OBS_STUDIO_STATUS",
  "command_uid": "<client_generated_uid>",
  "parameter": {
    "app_pid": "<obs_studio_process_pid>"
  }
}
```

**Response Format**:
```json
{
  "status": "success",
  "command_uid": "<ping_back_the_client_generated_uid>",
  "message": "OBS Studio is running",
  "data": {
    "app_pid": "<obs_studio_process_pid>",
    "status": "<process_status>",
    "cpu_usage": "<cpu_usage_percentage>",
    "memory_usage": "<memory_usage_in_bytes>"
  }
}
```

## Client Demo

To help you get started with the service, a client demo is provided in the `client_demo` folder. This demo demonstrates how to connect to the WebSocket server, send commands, and receive responses.

### Running the Client Demo

1. Navigate to the `client_demo` directory.
2. Open `index.html` in your browser.
3. Use the provided interface to test various commands.

## Contributing

Contributions are welcome! If you find any issues or want to add new features, feel free to fork the repository, make changes, and submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
```