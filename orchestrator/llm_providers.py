"""LLM provider abstraction layer supporting multiple providers."""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class ProviderResponse:
    """Unified response format from any LLM provider."""

    def __init__(
        self,
        assistant_message: str,
        tools_used: list[str],
        stop_reason: str = "end_turn",
        error: Optional[str] = None,
    ):
        self.assistant_message = assistant_message
        self.tools_used = tools_used
        self.stop_reason = stop_reason
        self.error = error

    def to_dict(self) -> dict:
        return {
            "assistant_message": self.assistant_message,
            "tools_used": self.tools_used,
            "stop_reason": self.stop_reason,
            "error": self.error,
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: dict, db_config: dict):
        """Initialize provider.

        Args:
            config: Provider configuration (model, system_prompt, etc.)
            db_config: Database connection config for tool execution
        """
        self.config = config
        self.db_config = db_config
        self.model = config.get("llm_model", "")
        self.system_prompt = config.get("system_prompt", "")
        self.tools = config.get("tools", [])
        self.guardrails = config.get("guardrails", {})

    @abstractmethod
    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message to LLM and get response.

        Args:
            user_message: User's input message
            available_tools: Dict of available tools with descriptions

        Returns:
            ProviderResponse with assistant message, tools used, and stop reason
        """
        pass

    def _execute_tool(self, tool_name: str, params: dict) -> str:
        """Execute a database tool. Subclasses can override for custom tools.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters

        Returns:
            String result of tool execution
        """
        from orchestrator.chatbot_service import TOOL_EXECUTORS

        if tool_name in TOOL_EXECUTORS:
            executor = TOOL_EXECUTORS[tool_name]
            return executor(self.db_config, params, self.guardrails)

        return f"Tool {tool_name} not found"


class AnthropicProvider(LLMProvider):
    """Claude API provider using Anthropic SDK."""

    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message to Claude via Anthropic API."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="ANTHROPIC_API_KEY not configured",
            )

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)

            # Build Claude tools schema
            tools_schema = self._build_claude_tools(available_tools)

            # Call Claude with tools
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=tools_schema,
                messages=[{"role": "user", "content": user_message}],
            )

            # Process response blocks
            assistant_message = ""
            tools_used = []

            for block in response.content:
                if hasattr(block, "text"):
                    assistant_message += block.text
                elif block.type == "tool_use":
                    tools_used.append(block.name)
                    tool_result = self._execute_tool(block.name, block.input)
                    assistant_message += f"\n[Executed {block.name}]\n{tool_result}\n"

            return ProviderResponse(
                assistant_message=assistant_message,
                tools_used=tools_used,
                stop_reason=response.stop_reason,
            )

        except ImportError:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="Anthropic SDK not installed. Install with: pip install anthropic",
            )
        except Exception as e:
            logger.error("Anthropic API error: %s", e, exc_info=True)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error=str(e),
            )

    def _build_claude_tools(self, available_tools: dict) -> list:
        """Build Claude-compatible tool schema."""
        tools = []
        for tool_name in self.tools:
            if tool_name in available_tools:
                tool_def = available_tools[tool_name]
                tools.append(
                    {
                        "name": tool_name,
                        "description": tool_def["description"],
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                param: {"type": "string"}
                                for param in tool_def["parameters"].keys()
                            },
                            "required": [],
                        },
                    }
                )
        return tools


class GoogleProvider(LLMProvider):
    """Google Gemini API provider."""

    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message to Google Gemini via API."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="GOOGLE_API_KEY not configured",
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)

            # Build Gemini tools schema
            tools_schema = self._build_gemini_tools(available_tools)

            # Call Gemini with tools
            response = model.generate_content(
                [self.system_prompt, user_message],
                tools=tools_schema if tools_schema else None,
            )

            assistant_message = response.text if response.text else ""
            tools_used = []

            # Process tool calls if any
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        tool_name = part.function_call.name
                        tools_used.append(tool_name)
                        # Extract kwargs from function call
                        params = dict(part.function_call.args)
                        tool_result = self._execute_tool(tool_name, params)
                        assistant_message += f"\n[Executed {tool_name}]\n{tool_result}\n"

            return ProviderResponse(
                assistant_message=assistant_message,
                tools_used=tools_used,
                stop_reason=response.candidates[0].finish_reason.name if response.candidates else "STOP",
            )

        except ImportError:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="Google Generative AI SDK not installed. Install with: pip install google-generativeai",
            )
        except Exception as e:
            logger.error("Google Gemini API error: %s", e, exc_info=True)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error=str(e),
            )

    def _build_gemini_tools(self, available_tools: dict) -> list:
        """Build Google Gemini-compatible tool schema."""
        try:
            import google.generativeai as genai
        except ImportError:
            return []

        tools = []
        for tool_name in self.tools:
            if tool_name in available_tools:
                tool_def = available_tools[tool_name]
                tool = genai.protos.Tool(
                    function_declarations=[
                        genai.protos.FunctionDeclaration(
                            name=tool_name,
                            description=tool_def["description"],
                            parameters=genai.protos.Schema(
                                type=genai.protos.Type.OBJECT,
                                properties={
                                    param: genai.protos.Schema(type=genai.protos.Type.STRING)
                                    for param in tool_def["parameters"].keys()
                                },
                            ),
                        )
                    ]
                )
                tools.append(tool)

        return tools


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API provider."""

    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message to OpenAI GPT via API."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="OPENAI_API_KEY not configured",
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            # Build OpenAI function calling schema
            tools_schema = self._build_openai_tools(available_tools)

            # Call OpenAI with function calling
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=tools_schema if tools_schema else None,
                tool_choice="auto" if tools_schema else None,
                messages=[{"role": "user", "content": user_message}],
            )

            assistant_message = ""
            tools_used = []

            # Process response
            if response.choices and response.choices[0].message:
                message = response.choices[0].message
                if message.content:
                    assistant_message = message.content

                # Handle tool calls
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tools_used.append(tool_name)
                        # Parse parameters from JSON
                        params = json.loads(tool_call.function.arguments)
                        tool_result = self._execute_tool(tool_name, params)
                        assistant_message += f"\n[Executed {tool_name}]\n{tool_result}\n"

            return ProviderResponse(
                assistant_message=assistant_message,
                tools_used=tools_used,
                stop_reason=response.choices[0].finish_reason if response.choices else "stop",
            )

        except ImportError:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="OpenAI SDK not installed. Install with: pip install openai",
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e, exc_info=True)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error=str(e),
            )

    def _build_openai_tools(self, available_tools: dict) -> list:
        """Build OpenAI function calling schema."""
        tools = []
        for tool_name in self.tools:
            if tool_name in available_tools:
                tool_def = available_tools[tool_name]
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool_def["description"],
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    param: {"type": "string"}
                                    for param in tool_def["parameters"].keys()
                                },
                                "required": [],
                            },
                        },
                    }
                )
        return tools


def get_provider(llm_provider: str, config: dict, db_config: dict) -> LLMProvider:
    """Factory function to get the appropriate LLM provider.

    Args:
        llm_provider: Provider name ("anthropic", "google", "openai")
        config: Provider configuration
        db_config: Database configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is not recognized
    """
    providers = {
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "openai": OpenAIProvider,
    }

    if llm_provider not in providers:
        raise ValueError(
            f"Unknown LLM provider: {llm_provider}. Supported: {list(providers.keys())}"
        )

    return providers[llm_provider](config, db_config)
