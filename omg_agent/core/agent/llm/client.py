"""
LLM Client - OpenAI compatible LLM interface.

Supports:
- OpenAI official API
- Local models (Ollama, vLLM, LocalAI, etc.)
- Any OpenAI-compatible API
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration (OpenAI compatible)."""

    # Model
    model: str = "gpt-4o"

    # API settings
    api_key: str | None = None
    api_base: str | None = None

    # Generation parameters
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0

    # Image handling
    resize_images: bool = True
    max_image_size: int = 1024

    # Timeout
    timeout: int = 120

    # Language (for prompts)
    lang: str = "zh"

    def __post_init__(self):
        # Load from environment if not set
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")

        if self.api_base is None:
            self.api_base = os.environ.get("OPENAI_API_BASE", "http://localhost:8000/v1")

    # Aliases for backward compatibility with phone_agent.model.ModelConfig
    @property
    def base_url(self) -> str | None:
        return self.api_base

    @base_url.setter
    def base_url(self, value: str | None):
        self.api_base = value

    @property
    def model_name(self) -> str:
        return self.model

    @model_name.setter
    def model_name(self, value: str):
        self.model = value


# Alias for backward compatibility
ModelConfig = LLMConfig


@dataclass
class LLMResponse:
    """LLM response container."""

    content: str
    thinking: str = ""
    action: str = ""
    raw_response: dict = field(default_factory=dict)

    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Timing
    latency_ms: int = 0

    def parse_thinking_and_action(self) -> None:
        """Parse thinking and action from content."""
        content = self.content

        # Try to extract <think>...</think> or <THINK>...</THINK>
        import re
        think_match = re.search(r"<[Tt][Hh][Ii][Nn][Kk]>(.*?)</[Tt][Hh][Ii][Nn][Kk]>", content, re.DOTALL)
        if think_match:
            self.thinking = think_match.group(1).strip()
            # Action is everything after </THINK>
            action_part = re.sub(r"<[Tt][Hh][Ii][Nn][Kk]>.*?</[Tt][Hh][Ii][Nn][Kk]>", "", content, flags=re.DOTALL)
            self.action = action_part.strip()
        else:
            self.action = content


class LLMClient:
    """
    Multi-provider LLM client.

    Supports vision models for screenshot understanding.
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = None

    def _get_openai_client(self):
        """Get OpenAI client (lazy init)."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base,
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    def request(self, messages: list[dict[str, Any]], **kwargs) -> LLMResponse:
        """
        Send request to LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Override config parameters

        Returns:
            LLMResponse with parsed content
        """
        start_time = time.time()

        # Merge config with kwargs
        params = {
            "model": kwargs.get("model", self.config.model),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "stream": True,  # Force stream mode for robustness
        }

        # Preprocess messages (handle images)
        processed_messages = self._preprocess_messages(messages)

        response = self._request_openai(processed_messages, params)

        # Calculate latency
        response.latency_ms = int((time.time() - start_time) * 1000)

        # Parse thinking and action
        response.parse_thinking_and_action()

        return response

    def _preprocess_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Preprocess messages, handling image encoding."""
        import base64

        processed = []
        for msg in messages:
            new_msg = {"role": msg["role"]}

            content = msg.get("content")
            if isinstance(content, str):
                new_msg["content"] = content
            elif isinstance(content, list):
                # Multi-modal content
                new_content = []
                for item in content:
                    if item.get("type") == "text":
                        new_content.append(item)
                    elif item.get("type") == "image_url":
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:image/"):
                            # Already base64 encoded
                            new_content.append(item)
                        elif url.startswith(("http://", "https://")):
                            # Remote URL, keep as is
                            new_content.append(item)
                        else:
                            # Local file path, encode
                            try:
                                with open(url, "rb") as f:
                                    data = f.read()
                                b64 = base64.b64encode(data).decode("utf-8")
                                # Detect format
                                fmt = "png"
                                if data[:2] == b"\xff\xd8":
                                    fmt = "jpeg"
                                new_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/{fmt};base64,{b64}"}
                                })
                            except Exception as e:
                                # Skip failed images
                                logger.warning(f"Failed to load image {url}: {e}")
                    elif item.get("type") == "image_base64":
                        # Convert to standard format
                        b64 = item.get("image_base64", {}).get("data", "")
                        new_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"}
                        })

                new_msg["content"] = new_content
            else:
                new_msg["content"] = content

            processed.append(new_msg)

        return processed

    def _request_openai(self, messages: list[dict], params: dict) -> LLMResponse:
        """Send request using OpenAI API."""
        client = self._get_openai_client()

        recovered_json = None
        response_stream = None

        try:
            logger.debug(f"Requesting with params: {params}")
            response_stream = client.chat.completions.create(
                messages=messages,
                **params
            )
        except json.decoder.JSONDecodeError as e:
            logger.error(f"JSON Decode Error from server: {e}")
            
            # Attempt recovery: "Extra data" means valid JSON exists at the start
            raw_data = getattr(e, 'doc', '')
            if raw_data:
                logger.debug(f"Raw response prefix: {raw_data[:500]}")
                try:
                    # e.pos indicates where parsing failed (start of extra data)
                    valid_json_str = raw_data[:e.pos]
                    recovered_json = json.loads(valid_json_str)
                    logger.info("Successfully recovered valid JSON object from response.")
                except Exception as rec_err:
                    logger.error(f"Recovery failed: {rec_err}")
                    raise RuntimeError(f"Server returned invalid JSON. Raw: {raw_data[:200]}") from e
            else:
                raise e
        except Exception as e:
             raise e

        content = ""
        role = "assistant"
        
        # Handle recovered static JSON (if stream failed but data recovered)
        if recovered_json:
            try:
                choices = recovered_json.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "") or ""
                    role = message.get("role", "assistant")
            except Exception as parse_err:
                logger.error(f"Error parsing recovered JSON: {parse_err}")

        # Handle normal stream
        elif response_stream:
            for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content += delta.content
                    if delta.role:
                        role = delta.role

        # Create response object
        return LLMResponse(
            content=content,
            raw_response=recovered_json or {}, 
            prompt_tokens=0, 
            completion_tokens=0,
        )

    def stream(self, messages: list[dict[str, Any]], **kwargs):
        """
        Stream response from LLM.

        Yields chunks of text as they arrive.
        """
        params = {
            "model": kwargs.get("model", self.config.model),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        processed_messages = self._preprocess_messages(messages)
        client = self._get_openai_client()

        response = client.chat.completions.create(
            messages=processed_messages,
            **params
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
