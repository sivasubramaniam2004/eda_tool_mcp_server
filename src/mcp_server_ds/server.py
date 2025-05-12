from enum import Enum
import logging
from typing import Optional, List, Any, Tuple, Union

## import mcp server
from mcp.server.models import InitializationOptions
from mcp.types import (
    TextContent,
    Tool,
    Resource,
    INTERNAL_ERROR,
    Prompt,
    PromptArgument,
    EmbeddedResource,
    GetPromptResult,
    PromptMessage,
)
from mcp.server import Server, NotificationOptions
from mcp.shared.exceptions import McpError
from pydantic import BaseModel, AnyUrl

## import common data analysis libraries
import pandas as pd
import numpy as np
import scipy
import sklearn
from io import StringIO
import sys

## Our imports
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

from starlette.applications import Starlette
from starlette.routing import Mount, Route
import statsmodels.api as sm
from starlette.requests import Request

import uvicorn

# Configure logging
target = "data-exploration"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(target)
logger.info("Initializing Data Exploration Server")

# Prompt templates and arguments
class DataExplorationPrompts(str, Enum):
    EXPLORE_DATA = "explore-data"

class PromptArgs(str, Enum):
    CSV_PATH = "csv_path"
    TOPIC = "topic"

PROMPT_TEMPLATE = """
You are a professional Data Scientist tasked with performing exploratory data analysis on a dataset. Your goal is to provide insightful analysis while ensuring stability and manageable result sizes.

First, load the CSV file from the following path:

<csv_path>
{csv_path}
</csv_path>

Your analysis should focus on the following topic:

<analysis_topic>
{topic}
</analysis_topic>

You have access to the following tools for your analysis:
1. load_csv: Use this to load the CSV file.
2. run-script: Use this to execute Python scripts on the MCP server.

Please follow these steps carefully:

1. Load the CSV file using the load_csv tool.

2. Explore the dataset. Provide a brief summary of its structure, including the number of rows, columns, and data types. Wrap your exploration process in <dataset_exploration> tags, including:
   - List of key statistics about the dataset
   - Potential challenges you foresee in analyzing this data

3. Wrap your thought process in <analysis_planning> tags:
   Analyze the dataset size and complexity:
   - How many rows and columns does it have?
   - Are there any potential computational challenges based on the data types or volume?
   - What kind of questions would be appropriate given the dataset's characteristics and the analysis topic?
   - How can we ensure that our questions won't result in excessively large outputs?

   Based on this analysis:
   - List 10 potential questions related to the analysis topic
   - Evaluate each question against the following criteria:
     * Directly related to the analysis topic
     * Can be answered with reasonable computational effort
     * Will produce manageable result sizes
     * Provides meaningful insights into the data
   - Select the top 5 questions that best meet all criteria

4. List the 5 questions you've selected, ensuring they meet the criteria outlined above.

5. For each question, follow these steps:
   a. Wrap your thought process in <analysis_planning> tags:
      - How can I structure the Python script to efficiently answer this question?
      - What data preprocessing steps are necessary?
      - How can I limit the output size to ensure stability?
      - What type of visualization would best represent the results?
      - Outline the main steps the script will follow
   
   b. Write a Python script to answer the question. Include comments explaining your approach and any measures taken to limit output size.
   
   c. Use the run_script tool to execute your Python script on the MCP server.
   
   d. Render the results returned by the run-script tool as a chart using plotly.js (prefer loading from cdnjs.cloudflare.com). Do not use react or recharts, and do not read the original CSV file directly. Provide the plotly.js code to generate the chart.

6. After completing the analysis for all 5 questions, provide a brief summary of your findings and any overarching insights gained from the data.

Remember to prioritize stability and manageability in your analysis. If at any point you encounter potential issues with large result sets, adjust your approach accordingly.

Please begin your analysis by loading the CSV file and providing an initial exploration of the dataset.
"""

# Tool identifiers
class DataExplorationTools(str, Enum):
    LOAD_CSV = "load_csv"
    RUN_SCRIPT = "run_script"

LOAD_CSV_TOOL_DESCRIPTION = """
Load CSV File Tool

Purpose:
Load a local CSV file into a DataFrame.

Usage Notes:
	•	If a df_name is not provided, the tool will automatically assign names sequentially as df_1, df_2, and so on.
"""

# Input schemas\ class LoadCsv(BaseModel):
class LoadCsv(BaseModel):
    csv_path: str
    df_name: Optional[str] = None

RUN_SCRIPT_TOOL_DESCRIPTION = """
Python Script Execution Tool

Purpose:
Execute Python scripts for specific data analytics tasks.

Allowed Actions
	1.	Print Results: Output will be displayed as the script’s stdout.
	2.	[Optional] Save DataFrames: Store DataFrames in memory for future use by specifying a save_to_memory name.

Prohibited Actions
	1.	Overwriting Original DataFrames: Do not modify existing DataFrames to preserve their integrity for future tasks.
	2.	Creating Charts: Chart generation is not permitted.
"""

class RunScript(BaseModel):
    script: str
    save_to_memory: Optional[List[str]] = None

# Script runner
class ScriptRunner:
    def __init__(self):
        self.data: dict[str, pd.DataFrame] = {}
        self.df_count = 0
        self.notes: List[str] = []

    def load_csv(self, csv_path: str, df_name: Optional[str] = None) -> List[TextContent]:
        self.df_count += 1
        name = df_name or f"df_{self.df_count}"
        try:
            df = pd.read_csv(csv_path)
            self.data[name] = df
            msg = f"Loaded CSV into '{name}' ({df.shape[0]} rows, {df.shape[1]} cols)"
            self.notes.append(msg)
            return [TextContent(type="text", text=msg)]
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise McpError(INTERNAL_ERROR, f"Error loading CSV: {e}")

    def safe_eval(self, script: str, save_to_memory: Optional[List[str]] = None) -> List[TextContent]:
        local_vars = {**self.data}
        stdout = StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout
        self.notes.append(f"Executing script:\n{script}")
        try:
            exec(
                script,
                {
                    'pd': pd,
                    'np': np,
                    'scipy': scipy,
                    'sklearn': sklearn,
                    'sm': sm,
                },
                local_vars,
            )
        except Exception as e:
            sys.stdout = old_stdout
            logger.error(f"Script error: {e}")
            raise McpError(INTERNAL_ERROR, f"Script error: {e}")
        sys.stdout = old_stdout
        output = stdout.getvalue().strip() or "<no output>"
        if save_to_memory:
            for name in save_to_memory:
                df = local_vars.get(name)
                if isinstance(df, pd.DataFrame):
                    self.data[name] = df
                    self.notes.append(f"Saved DataFrame '{name}' to memory")
        self.notes.append(f"Script output: {output}")
        return [TextContent(type="text", text=output)]

### MCP Server Definition
def create_data_exploration_server() -> Tuple[Server, InitializationOptions]:
    runner = ScriptRunner()
    server = Server("data-exploration-server")

    @server.list_resources()
    async def list_resources() -> List[Resource]:
        return [
            Resource(
                uri="data-exploration://notes",
                name="Exploration Notes",
                description="Accumulated notes from data exploration",
                mimeType="text/plain",
            )
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        if str(uri) == "data-exploration://notes":
            return "\n".join(runner.notes)
        raise ValueError(f"Unknown resource: {uri}")

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        return [
            Prompt(
                name=DataExplorationPrompts.EXPLORE_DATA,
                description="Explore a CSV dataset",
                arguments=[
                    PromptArgument(
                        name=PromptArgs.CSV_PATH,
                        description="Path to the CSV file",
                        required=True,
                    ),
                    PromptArgument(
                        name=PromptArgs.TOPIC,
                        description="Focus topic",
                        required=False,
                    ),
                ],
            )
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: Optional[dict[str, Any]]) -> GetPromptResult:
        if name != DataExplorationPrompts.EXPLORE_DATA:
            raise ValueError(f"Unknown prompt: {name}")
        if not arguments or PromptArgs.CSV_PATH not in arguments:
            raise ValueError("Missing required argument: csv_path")
        prompt_text = PROMPT_TEMPLATE.format(
            csv_path=arguments[PromptArgs.CSV_PATH],
            topic=arguments.get(PromptArgs.TOPIC, ""),
        )
        return GetPromptResult(
            description="Data exploration template",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text.strip()),
                )
            ],
        )

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name=DataExplorationTools.LOAD_CSV.value,
                description="Load a CSV into memory",
                inputSchema=LoadCsv.model_json_schema(),
            ),
            Tool(
                name=DataExplorationTools.RUN_SCRIPT.value,
                description="Execute Python code safely",
                inputSchema=RunScript.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> List[Union[TextContent, EmbeddedResource]]:
        if name == DataExplorationTools.LOAD_CSV.value:
            return runner.load_csv(
                arguments.get("csv_path"),
                arguments.get("df_name"),
            )
        if name == DataExplorationTools.RUN_SCRIPT.value:
            return runner.safe_eval(
                arguments.get("script"),
                arguments.get("save_to_memory"),
            )
        raise McpError(INTERNAL_ERROR, f"Unknown tool: {name}")

    init_opts = InitializationOptions(
        server_name="data-exploration-server",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    return server, init_opts

# STDIO transport runner
def run_stdio_transport() -> None:
    server, init_opts = create_data_exploration_server()
    logger.info("Starting STDIO transport")
    import asyncio

    async def _stdio_runner():
        async with stdio_server() as (r, w):
            await server.run(r, w, init_opts)

    asyncio.run(_stdio_runner())

# SSE transport runner
def run_sse_transport(host: str = "127.0.0.1", port: int = 8000) -> None:
    server, init_opts = create_data_exploration_server()
    sse = SseServerTransport("/messages/")

    async def sse_endpoint(request: Request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (r, w):
            await server.run(r, w, init_opts)

    app = Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=sse_endpoint),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    logger.info(f"Starting SSE transport at http://{host}:{port}/sse")
    # Now uvicorn is guaranteed to be defined
    uvicorn.run(app, host=host, port=port)

# CLI entrypoint
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Data Exploration MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "both"],
        default="stdio",
        help="Transport protocol(s) to run",
    )
    parser.add_argument("--host", default="127.0.0.1", help="SSE host")
    parser.add_argument("--port", type=int, default=8000, help="SSE port")
    args = parser.parse_args()

    if args.transport in ("stdio", "both"):
        run_stdio_transport()
    if args.transport in ("sse", "both"):
        run_sse_transport(host=args.host, port=args.port)