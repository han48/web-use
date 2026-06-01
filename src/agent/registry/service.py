from src.agent.registry.views import ToolResult
from src.tools import Tool
import inspect
import json
import logging

logger = logging.getLogger(__name__)

class Registry:
    NON_TOOL_PARAMS = {"thought"}

    def __init__(self, tools: list[Tool] = [], browser=None):
        self._static_tools: list[Tool] = list(tools)
        self._dynamic_tools: list[Tool] = []
        self.tools_registry: dict[str, Tool] = {tool.name: tool for tool in tools}
        self.extensions: dict = {}
        self.browser = browser

    @property
    def tools(self) -> list[Tool]:
        return self._static_tools + self._dynamic_tools
    
    def register_static(self, tools: list[Tool]) -> None:
        self._static_tools.extend(tools)
        self._sync()

    def register_dynamic(self, tools: list[Tool]) -> None:
        """Replace the dynamic tool pool (called once per agent step)."""
        self._dynamic_tools = list(tools)
        self._sync()

    def _sync(self) -> None:
        """Synchronize the tools_registry dictionary with the current tool lists."""
        registry = {t.name: t for t in self._dynamic_tools}
        registry.update({t.name: t for t in self._static_tools})
        self.tools_registry = registry

    async def refresh_dynamic_tools(self) -> bool:
        """Fetch and update dynamic tools (WebMCP) from the browser."""
        if not self.browser:
            return False

        from src.tools import WebMCPTool
        try:
            cdp = await self.browser.get_cdp_client()
            session_id = self.browser._get_current_session_id()
            if not session_id:
                return False

            script = """
                (async () => {
                    try {
                        if (typeof navigator.modelContextTesting !== 'undefined') {
                            const tools = await navigator.modelContextTesting.listTools();
                            return { tools: tools };
                        }
                        return { tools: [] };
                    } catch (e) {
                        return { error: e.message };
                    }
                })()
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
                logger.error(f"WebMCP fetch error: {val['error']}")
                return False

            tools = val.get("tools", [])
            dynamic_tools = []

            for tool in tools:
                name = tool.get('name')
                if not name:
                    continue
                logger.info(f"Discovered WebMCP tool: {name}")
                desc = tool.get('description', '')
                schema = tool.get('inputSchema', {})
                if isinstance(schema, str):
                    try:
                        schema = json.loads(schema)
                    except Exception:
                        schema = {}

                dynamic_tools.append(WebMCPTool(self.browser, name, desc, schema))

            self.register_dynamic(dynamic_tools)
            return True

        except Exception as e:
            logger.debug(f"Failed to fetch WebMCP tools: {e}")
            return False

    def add_extension(self, name: str, obj) -> None:
        self.extensions[name] = obj

    def _build_kwargs(self, tool: Tool, tool_params: dict) -> dict:
        """Merge extensions into tool_params, filtered to only params the tool accepts.

        Tools that override invoke/ainvoke directly (e.g. WebMCPTool) set
        ``function = None``. For those we skip extension injection and pass
        only the parameters defined in their schema through.
        """
        from src.tools import WebMCPTool
        if isinstance(tool, WebMCPTool):
            # WebMCPTools are sensitive to extra arguments; strictly filter to their schema
            properties = tool.schema.get('properties', {})
            if properties:
                allowed = set(properties.keys())
                return {k: v for k, v in tool_params.items() if k in allowed}
            return {k: v for k, v in tool_params.items() if k not in self.NON_TOOL_PARAMS}

        if tool.function is None:
            # Fallback for other non-function tools
            return {k: v for k, v in tool_params.items() if k not in self.NON_TOOL_PARAMS}

        sig = inspect.signature(tool.function)
        accepted = set(sig.parameters)
        extensions = {k: v for k, v in self.extensions.items() if k in accepted}
        filtered_params = {k: v for k, v in tool_params.items() if k in accepted}
        return extensions | filtered_params

    def get_tools(self, exclude: list[str] = []) -> list[Tool]:
        if not exclude:
            return self.tools
        return [t for t in self.tools if t.name not in exclude]

    def get_tool(self, name: str) -> Tool | None:
        return self.tools_registry.get(name)

    def execute(self, tool_name: str, tool_params: dict) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' not found.")
        errors = tool.validate_params(tool_params)
        if errors:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' validation failed:\n" + "\n".join(errors))
        try:
            content = tool.invoke(**self._build_kwargs(tool, tool_params))
            return ToolResult(is_success=True, content=content)
        except Exception as e:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' failed: {e}")

    async def aexecute(self, tool_name: str, tool_params: dict) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' not found.")
        errors = tool.validate_params(tool_params)
        if errors:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' validation failed:\n" + "\n".join(errors))
        try:
            content = await tool.ainvoke(**self._build_kwargs(tool, tool_params))
            return ToolResult(is_success=True, content=content)
        except Exception as e:
            return ToolResult(is_success=False, error=f"Tool '{tool_name}' async failed: {e}")
