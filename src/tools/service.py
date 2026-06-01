from __future__ import annotations
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass,field
from typing import Any, TYPE_CHECKING
from abc import ABC
import asyncio
import logging
import json

if TYPE_CHECKING:
    from src.agent.browser import Browser

EXCLUDED_PROPERTIES = ["title"]

MAX_TOOL_OUTPUT_LENGTH = 10000

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    success: bool=False
    output:str|None=None
    error:str|None=None
    metadata:dict[str,Any]=field(default_factory=dict)

    @classmethod
    def success_result(cls,output:str,metadata:dict[str,Any]=None) -> "ToolResult":
        return cls(success=True,output=output,metadata=metadata)
    
    @classmethod
    def error_result(cls,error:str,metadata:dict[str,Any]=None) -> "ToolResult":
        return cls(success=False,error=error,metadata=metadata)

class Tool(ABC):
    def __init__(self, name: str|None=None, description: str|None=None, model: BaseModel|None=None):
        self.name = name
        self.description = description
        self.model = model
        self.function = None

    @property
    def json_schema(self) -> dict:
        schema = self.model.model_json_schema(mode="serialization")
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        def exclude_properties(obj):
            if isinstance(obj, dict):
                return {
                    k: exclude_properties(v)
                    for k, v in obj.items()
                    if k not in EXCLUDED_PROPERTIES
                }
            elif isinstance(obj, list):
                return [exclude_properties(item) for item in obj]
            return obj

        parameters = {
            "type": "object",
            "properties": exclude_properties(properties),
            "required": required,
        }

        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }

    def validate_params(self, args: dict[str,Any])->list[str]:
        try:
            self.model(**args)
            return []
        except ValidationError as e:
            errors=[]
            for error in e.errors():
                field = "".join([str(loc) for loc in error["loc"]])
                msg = error["msg"]
                errors.append(f"{field}:{msg}")
            return errors
        except Exception as e:
            return [str(e)]

    def __call__(self, function):
        if self.name is None:
            self.name = function.__name__
        if self.description is None:
            self.description = function.__doc__
        self.function = function
        return self

    def invoke(self, *args, **kwargs):
        """Synchronous invocation. Use ainvoke for async tools."""
        try:
            return self.function(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error invoking tool {self.name}: {e}")
            raise

    async def ainvoke(self, *args, **kwargs):
        """Asynchronous invocation. Awaits if the tool function is a coroutine."""
        try:
            if asyncio.iscoroutinefunction(self.function):
                return await self.function(*args, **kwargs)
            return self.function(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error invoking tool {self.name}: {e}")
            raise

class WebMCPTool(Tool):
    def __init__(self, browser: Browser, name: str, description: str, schema: dict):
        super().__init__(name=name, description=description)
        self.browser = browser
        self.schema = schema

    @property
    def json_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description or "No description",
            "parameters": self.schema,
        }

    def validate_params(self, args: dict) -> list[str]:
        # We skip Pydantic validation here and let the target website handle it
        return []

    async def ainvoke(self, **kwargs):
        # Execute tool on browser via CDP Runtime.evaluate
        cdp = await self.browser.get_cdp_client()
        session_id = self.browser._get_current_session_id()
        args_json = json.dumps(kwargs)
        # We use json.dumps twice: once to get the JSON string, and once to get a safely 
        # escaped JS string literal (including quotes) for the Runtime.evaluate call.
        safe_args_json = json.dumps(args_json)

        script = f"""
            (async () => {{
                try {{
                    const result = await navigator.modelContextTesting.executeTool(
                        '{self.name}',
                        {safe_args_json}
                    );
                    return {{ result: result }};
                }} catch (e) {{
                    return {{ error: e.message }};
                }}
            }})()
        """
        
        result = await cdp.runtime.evaluate(
            params={
                "expression": script,
                "awaitPromise": True,
                "returnByValue": True,
            },
            session_id=session_id
        )
        
        val = result.get("result", {}).get("value", {})
        if "error" in val:
            raise Exception(f"WebMCP execution error: {val['error']}")
            
        return val.get("result", "Success")

    def invoke(self, **kwargs):
        raise NotImplementedError("WebMCPTools must be run asynchronously.")



