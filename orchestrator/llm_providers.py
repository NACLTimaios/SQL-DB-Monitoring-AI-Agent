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
        tool_outputs: Optional[dict] = None,
    ):
        self.assistant_message = assistant_message
        self.tools_used = tools_used
        self.stop_reason = stop_reason
        self.error = error
        self.tool_outputs = tool_outputs or {}

    def to_dict(self) -> dict:
        return {
            "assistant_message": self.assistant_message,
            "tools_used": self.tools_used,
            "stop_reason": self.stop_reason,
            "error": self.error,
            "tool_outputs": self.tool_outputs,
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
        """Send message to Claude via Anthropic API with proper tool use loop."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="ANTHROPIC_API_KEY not configured",
                tool_outputs={},
            )

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            tools_schema = self._build_claude_tools(available_tools)

            # Initialize message list
            messages = [{"role": "user", "content": user_message}]
            tools_used = []
            tool_outputs = {}

            # Agentic loop - keep calling until model stops using tools
            max_iterations = 10
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Call Claude
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=tools_schema if tools_schema else None,
                    messages=messages,
                )

                # Check if we should continue the loop
                if response.stop_reason == "end_turn":
                    # Model finished, extract final text response
                    final_message = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_message += block.text

                    return ProviderResponse(
                        assistant_message=final_message.strip(),
                        tools_used=tools_used,
                        stop_reason=response.stop_reason,
                        tool_outputs=tool_outputs,
                    )

                # Process tool calls
                if response.stop_reason == "tool_use":
                    # Add assistant response to messages
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute tools and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            if block.name not in tools_used:
                                tools_used.append(block.name)
                            tool_result = self._execute_tool(block.name, block.input)
                            tool_outputs[block.name] = tool_result

                            # SECURITY: Scan tool output with Prisma AIRS BEFORE sending to LLM
                            import os
                            prisma_airs_enabled = os.environ.get("PRISMA_AIRS_API_KEY") and os.environ.get("PRISMA_AIRS_PROFILE_ID")

                            if prisma_airs_enabled:
                                from api.prisma_airs import scan_response
                                tool_scan = scan_response(tool_result, model=self.model)
                                logger.info(f"Tool output scan ({block.name}): safe={tool_scan['safe']}, risk_level={tool_scan['risk_level']}, threats={tool_scan['threats']}")

                                if not tool_scan["safe"]:
                                    # Unsafe tool output - STOP processing immediately
                                    threat_summary = ", ".join(tool_scan["threats"]) if tool_scan["threats"] else "Sensitive data detected"
                                    error_msg = f"🚨 [STAGE: TOOL OUTPUT] Security threat detected in {block.name} results\n\nThreats: {threat_summary}\nRisk Level: {tool_scan['risk_level'].upper()}\n\nThe tool returned data flagged as unsafe. Processing stopped to prevent data leakage."
                                    logger.warning(f"SECURITY: Unsafe tool output blocked in {block.name}: {threat_summary}")
                                    return ProviderResponse(
                                        assistant_message="",
                                        tools_used=tools_used,
                                        stop_reason="security_block",
                                        error=error_msg,
                                        tool_outputs=tool_outputs,
                                    )

                            # Safe to send to LLM
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result,
                            })

                    # Add tool results as user message (only if all scans passed)
                    if tool_results:
                        messages.append({"role": "user", "content": tool_results})
                else:
                    # Unexpected stop reason
                    final_message = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_message += block.text

                    return ProviderResponse(
                        assistant_message=final_message.strip(),
                        tools_used=tools_used,
                        stop_reason=response.stop_reason,
                        tool_outputs=tool_outputs,
                    )

            # Max iterations reached
            return ProviderResponse(
                assistant_message="",
                tools_used=tools_used,
                error="Max tool use iterations reached",
                tool_outputs=tool_outputs,
            )

        except ImportError:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="Anthropic SDK not installed. Install with: pip install anthropic",
                tool_outputs={},
            )
        except Exception as e:
            logger.error("Anthropic API error: %s", e, exc_info=True)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error=str(e),
                tool_outputs={},
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

            assistant_message = ""
            tools_used = []

            # Process tool calls and text responses
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        tool_name = part.function_call.name
                        tools_used.append(tool_name)
                        # Extract kwargs from function call
                        params = dict(part.function_call.args)
                        tool_result = self._execute_tool(tool_name, params)
                        assistant_message += f"[Executed {tool_name}]\n{tool_result}\n"
                    elif hasattr(part, "text") and part.text:
                        assistant_message += part.text

            # Fallback to response.text if no parts processed
            if not assistant_message and hasattr(response, "text"):
                try:
                    assistant_message = response.text
                except Exception:
                    pass

            return ProviderResponse(
                assistant_message=assistant_message.strip(),
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


class PrismaAIProvider(LLMProvider):
    """Prisma AI (or compatible OpenAI-compatible) API provider.

    SECURITY: API key is ONLY stored in environment variable and NEVER exposed to:
    - The LLM (Claude, etc.)
    - Logs or error messages
    - Response data returned to user
    - System prompts or tool schemas
    """

    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message to Prisma AI via compatible OpenAI API.

        The API key is loaded from PRISMA_API_KEY environment variable and:
        - Used only in HTTP Authorization header for Prisma API calls
        - Never passed in request payload
        - Never logged in error messages
        - Never sent to LLM (Claude, GPT, etc.)
        """
        api_key = os.environ.get("PRISMA_API_KEY")
        api_url = os.environ.get("PRISMA_API_URL")

        if not api_key or not api_url:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="PRISMA_API_KEY or PRISMA_API_URL not configured",
            )

        try:
            import requests

            # Initialize conversation with system prompt
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": user_message})

            # Build tools for the API
            tools = self._build_openai_compatible_tools(available_tools)

            # Prepare request payload (API key NEVER included in payload)
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
            }

            # Add tools if available
            if tools:
                payload["tools"] = tools

            # Make API request
            # API key ONLY goes in Authorization header, never in request body
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{api_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()
            result = response.json()

            # Extract response
            assistant_message = ""
            tools_used = []
            stop_reason = "end_turn"

            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                message = choice.get("message", {})

                # Get text content (LLM response - API key never here)
                if "content" in message and message["content"]:
                    assistant_message = message["content"]

                # Handle tool calls if present
                if "tool_calls" in message and message["tool_calls"]:
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call.get("function", {}).get("name")
                        if tool_name:
                            tools_used.append(tool_name)
                            try:
                                # Parse arguments from LLM response
                                args_str = tool_call.get("function", {}).get("arguments", "{}")
                                params = json.loads(args_str) if isinstance(args_str, str) else args_str
                                tool_result = self._execute_tool(tool_name, params)
                                assistant_message += f"\n[Executed {tool_name}]\n{tool_result}\n"
                            except Exception as e:
                                # Log error without exposing sensitive data
                                logger.error(f"Tool execution failed: {type(e).__name__}")
                                assistant_message += f"\n[Tool execution failed. Check server logs.]\n"

                stop_reason = choice.get("finish_reason", "stop")

            return ProviderResponse(
                assistant_message=assistant_message,
                tools_used=tools_used,
                stop_reason=stop_reason,
            )

        except requests.exceptions.RequestException as e:
            # Log without exposing headers, URL details, or exception details
            logger.error("Prisma AI API request failed: %s", type(e).__name__)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="LLM API request failed. Please try again.",
            )
        except Exception as e:
            # Log error type only, never the full exception which might contain sensitive info
            logger.error("Prisma AI error: %s", type(e).__name__)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="LLM service error. Please try again.",
            )

    def _build_openai_compatible_tools(self, available_tools: dict) -> list:
        """Build OpenAI-compatible function calling schema for Prisma AI."""
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


class PortkeyProvider(LLMProvider):
    """Portkey AI Gateway provider - OpenAI-compatible API gateway.

    Portkey routes requests to configured models through their gateway.
    Supports routing to multiple LLM providers (OpenAI, Google, Anthropic, etc.)
    """

    def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
        """Send message through Portkey AI Gateway."""
        api_key = os.environ.get("PORTKEY_API_KEY")
        if not api_key:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="PORTKEY_API_KEY not configured",
            )

        try:
            from portkey_ai import Portkey

            portkey = Portkey(api_key=api_key)

            # Build OpenAI-compatible function calling schema
            tools_schema = self._build_portkey_tools(available_tools)

            # Call Portkey with function calling
            response = portkey.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                tools=tools_schema if tools_schema else None,
                tool_choice="auto" if tools_schema else None,
            )

            assistant_message = ""
            tools_used = []
            tool_outputs = {}

            # Process response
            if response.choices and response.choices[0].message:
                message = response.choices[0].message
                if message.content:
                    assistant_message = message.content

                # Handle tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tools_used.append(tool_name)
                        # Parse parameters from JSON
                        params = json.loads(tool_call.function.arguments)
                        tool_result = self._execute_tool(tool_name, params)
                        # SECURITY: Capture raw tool output so chatbot_service can
                        # scan it with Prisma AIRS (Stage 2 - tool output scanning)
                        # before it is surfaced. Without this, the dedicated tool
                        # output scan stage is bypassed.
                        tool_outputs[tool_name] = tool_result
                        assistant_message += f"\n[Executed {tool_name}]\n{tool_result}\n"

            return ProviderResponse(
                assistant_message=assistant_message,
                tools_used=tools_used,
                stop_reason=response.choices[0].finish_reason if response.choices else "stop",
                tool_outputs=tool_outputs,
            )

        except ImportError:
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error="Portkey SDK not installed. Install with: pip install portkey-ai",
            )
        except Exception as e:
            logger.error("Portkey API error: %s", e, exc_info=True)
            return ProviderResponse(
                assistant_message="",
                tools_used=[],
                error=str(e),
            )

    def _build_portkey_tools(self, available_tools: dict) -> list:
        """Build OpenAI-compatible function calling schema for Portkey."""
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
        llm_provider: Provider name ("anthropic", "google", "openai", "prisma", "portkey")
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
        "prisma": PrismaAIProvider,
        "portkey": PortkeyProvider,
    }

    if llm_provider not in providers:
        raise ValueError(
            f"Unknown LLM provider: {llm_provider}. Supported: {list(providers.keys())}"
        )

    return providers[llm_provider](config, db_config)
