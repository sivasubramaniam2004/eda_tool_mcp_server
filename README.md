# EDA Tool MCP Server (with SSE Endpoint)

This repository provides a server setup for the EDA (Exploratory Data Analysis) tool that supports **Server-Sent Events (SSE)** via the `/sse` endpoint. It allows clients to connect and receive real-time data streams over HTTP.

---

## 🔧 Prerequisites

- Python 3.8 or later
- Git
- pip (Python package installer)

---

## Setup Instructions 

### 1. Clone the Repository

Open Command Prompt or PowerShell and run:

```bash
git clone https://github.com/sivasubramaniam2004/eda_tool_mcp_server.git
```

``` bash
cd eda_tool_mcp_server
```

### Install Dependencies
Run the setup script to install required packages:

### 1. On Windows
``` bash
python setup.py
```

### 2. On macOS

 Change the 98th line of setup.py with 

``` python
match = re.findall(r'dist/[^\s]+\.whl', output.strip())
```
and 
``` bash
cd mcp_server_ds
```

### Start the Server
``` bash
python server.py --transport sse --host 127.0.0.1 --port 8000
```
