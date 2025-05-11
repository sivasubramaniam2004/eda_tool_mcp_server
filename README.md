<<<<<<< HEAD
# EDA Tool MCP Server (with SSE Endpoint)

This repository provides a server setup for the EDA (Exploratory Data Analysis) tool that supports **Server-Sent Events (SSE)** via the `/sse` endpoint. It allows clients to connect and receive real-time data streams over HTTP.

---

## 🔧 Prerequisites

- Python 3.8 or later
- Git
- pip (Python package installer)

---

## Setup Instructions (Windows)

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

``` bash
python setup.py
```

``` bash
cd mcp_server_ds
```

### Start the Server
``` bash
python server.py --transport sse --host 127.0.0.1 --port 8000
```

=======
# eda_tool_mcp_server
>>>>>>> 4f3a5b1df70aaa03d5c9731751e836c2c6cf5b39
