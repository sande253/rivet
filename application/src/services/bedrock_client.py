"""AWS Bedrock client adapter for Claude models.

This module provides a drop-in replacement for the Anthropic SDK,
using AWS Bedrock instead of direct API calls.

Key differences from Anthropic SDK:
- Uses IAM role credentials (no API keys)
- Model IDs use Bedrock format (e.g., anthropic.claude-3-5-sonnet-20241022-v2:0)
- Response format is slightly different but compatible
"""
import base64
import json
import logging
import os
from typing import Any, Generator

import boto3
import botocore.config

log = logging.getLogger(__name__)


class BedrockClient:
    """AWS Bedrock client that mimics the Anthropic SDK interface."""

    def __init__(self, region: str = None):
        """Initialize Bedrock client.
        
        Args:
            region: AWS region (defaults to AWS_REGION env var or us-east-1)
        """
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        
        config = botocore.config.Config(
            read_timeout=120,
            connect_timeout=10,
            retries={"max_attempts": 2, "mode": "adaptive"},
        )
        
        # Credentials come from IAM role - no keys needed
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            config=config,
        )
        
        log.info("Bedrock client initialized [region=%s]", self.region)

    @property
    def messages(self):
        """Return messages API interface (mimics anthropic.Anthropic().messages)."""
        return MessagesAPI(self.client, self.region)


class MessagesAPI:
    """Messages API that mimics anthropic.Anthropic().messages interface."""

    def __init__(self, client, region: str):
        self.client = client
        self.region = region

    def create(
        self,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str = None,
        **kwargs
    ) -> "MessageResponse":
        """Create a message (mimics Anthropic SDK).
        
        Args:
            model: Model ID (e.g., "claude-opus-4-6" or Bedrock format)
            max_tokens: Maximum tokens to generate
            messages: List of message dicts with role and content
            system: System prompt (optional)
            **kwargs: Additional parameters (ignored for compatibility)
        
        Returns:
            MessageResponse object with .content[0].text attribute
        """
        # Convert model ID to Bedrock format if needed
        bedrock_model = self._convert_model_id(model)
        
        # Check if using Titan model (different API format)
        if bedrock_model.startswith("amazon.titan"):
            return self._invoke_titan(bedrock_model, max_tokens, messages, system, **kwargs)

        # Nova models use Amazon's native request/response format
        if bedrock_model.startswith("amazon.nova"):
            return self._invoke_nova(bedrock_model, max_tokens, messages, system, **kwargs)
        
        # Build Bedrock request body for Anthropic models
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        
        if system:
            body["system"] = system
        
        # Add optional parameters
        if "temperature" in kwargs:
            body["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            body["top_p"] = kwargs["top_p"]
        
        try:
            response = self.client.invoke_model(
                modelId=bedrock_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            
            result = json.loads(response["body"].read())
            return MessageResponse(result)
            
        except Exception as e:
            log.error("Bedrock invocation failed: %s", e)
            raise
    
    def _invoke_nova(
        self,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str = None,
        **kwargs
    ) -> "MessageResponse":
        """Invoke Amazon Nova model (supports vision + text)."""
        nova_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, str):
                nova_content = [{"text": content}]
            elif isinstance(content, list):
                nova_content = []
                for block in content:
                    if block.get("type") == "text":
                        nova_content.append({"text": block["text"]})
                    elif block.get("type") == "image":
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            # e.g. "image/jpeg" → "jpeg"
                            fmt = source.get("media_type", "image/jpeg").split("/")[-1]
                            nova_content.append({
                                "image": {
                                    "format": fmt,
                                    "source": {"bytes": source["data"]},
                                }
                            })
            else:
                nova_content = [{"text": str(content)}]

            nova_messages.append({"role": role, "content": nova_content})

        body = {
            "messages": nova_messages,
            "inferenceConfig": {"max_new_tokens": max_tokens},
        }
        if system:
            body["system"] = [{"text": system}]
        if "temperature" in kwargs:
            body["inferenceConfig"]["temperature"] = kwargs["temperature"]

        try:
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            text = (
                result.get("output", {})
                      .get("message", {})
                      .get("content", [{}])[0]
                      .get("text", "")
            )
            return MessageResponse({
                "content": [{"type": "text", "text": text}],
                "role": "assistant",
                "model": model,
            })
        except Exception as e:
            log.error("Nova invocation failed: %s", e)
            raise

    def _invoke_titan(
        self,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str = None,
        **kwargs
    ) -> "MessageResponse":
        """Invoke Amazon Titan model (different API format)."""
        # Convert messages to Titan format
        prompt = ""
        if system:
            prompt = f"{system}\n\n"
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Handle content that might be a list (for images)
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                content = " ".join(text_parts)
            
            if role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        
        prompt += "Assistant:"
        
        # Build Titan request body
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.9),
            }
        }
        
        try:
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            
            result = json.loads(response["body"].read())
            
            # Convert Titan response to Anthropic format
            text = result.get("results", [{}])[0].get("outputText", "")
            
            return MessageResponse({
                "content": [{"type": "text", "text": text}],
                "role": "assistant",
                "model": model,
            })
            
        except Exception as e:
            log.error("Titan invocation failed: %s", e)
            raise

    def stream(
        self,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str = None,
        **kwargs
    ):
        """Create a streaming message (mimics Anthropic SDK).
        
        Returns a context manager that yields text chunks.
        """
        bedrock_model = self._convert_model_id(model)

        if bedrock_model.startswith("amazon.nova"):
            # Nova streaming format
            nova_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, str):
                    nova_content = [{"text": content}]
                elif isinstance(content, list):
                    nova_content = [{"text": b["text"]} for b in content if b.get("type") == "text"]
                else:
                    nova_content = [{"text": str(content)}]
                nova_messages.append({"role": role, "content": nova_content})

            body = {"messages": nova_messages, "inferenceConfig": {"max_new_tokens": max_tokens}}
            if system:
                body["system"] = [{"text": system}]
        else:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                body["system"] = system
        
        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=bedrock_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            
            return StreamingResponse(response)
            
        except Exception as e:
            log.error("Bedrock streaming failed: %s", e)
            raise

    def _convert_model_id(self, model: str) -> str:
        """Convert model ID to Bedrock format.

        Uses Amazon Nova Pro which has vision capabilities and needs no approval.
        """
        # Explicit mapping takes priority
        model_map = {
            # All models → Amazon Nova Pro (vision-capable, no approval needed)
            "claude-opus-4-6": "amazon.nova-pro-v1:0",
            "claude-sonnet-4-6": "amazon.nova-pro-v1:0",
            "claude-3-5-sonnet-20241022": "amazon.nova-pro-v1:0",
            "claude-haiku-4-5-20251001": "amazon.nova-pro-v1:0",
            "claude-3-5-haiku-20241022": "amazon.nova-pro-v1:0",
            "claude-3-haiku-20240307": "amazon.nova-pro-v1:0",
            # Bedrock-format Anthropic IDs → Amazon Nova Pro
            "anthropic.claude-3-5-sonnet-20241022-v2:0": "amazon.nova-pro-v1:0",
            "anthropic.claude-3-5-haiku-20241022-v1:0": "amazon.nova-pro-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0": "amazon.nova-pro-v1:0",
        }
        if model in model_map:
            return model_map[model]

        # Already an Amazon model ID — use as-is
        if model.startswith("amazon."):
            return model

        # Strip cross-region prefix
        if model.startswith("us.anthropic."):
            stripped = model.replace("us.anthropic.", "anthropic.")
            return model_map.get(stripped, "amazon.nova-pro-v1:0")

        # Any remaining anthropic.* IDs → Amazon Nova Pro
        if model.startswith("anthropic."):
            return "amazon.nova-pro-v1:0"

        log.warning("Unknown model ID '%s', defaulting to Amazon Nova Pro", model)
        return "amazon.nova-pro-v1:0"



class MessageResponse:
    """Response object that mimics anthropic.types.Message."""

    def __init__(self, bedrock_response: dict):
        self.raw_response = bedrock_response
        self.content = [ContentBlock(bedrock_response.get("content", [{}])[0])]
        self.id = bedrock_response.get("id", "")
        self.model = bedrock_response.get("model", "")
        self.role = bedrock_response.get("role", "assistant")
        self.stop_reason = bedrock_response.get("stop_reason")
        self.usage = bedrock_response.get("usage", {})


class ContentBlock:
    """Content block that mimics anthropic.types.ContentBlock."""

    def __init__(self, content_dict: dict):
        self.type = content_dict.get("type", "text")
        self.text = content_dict.get("text", "")


class StreamingResponse:
    """Streaming response that mimics anthropic.Stream."""

    def __init__(self, bedrock_stream_response):
        self.stream = bedrock_stream_response.get("body")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def text_stream(self) -> Generator[str, None, None]:
        """Yield text chunks from the stream (handles both Nova and Anthropic events)."""
        for event in self.stream:
            chunk = event.get("chunk")
            if not chunk:
                continue
            chunk_data = json.loads(chunk.get("bytes").decode())
            # Anthropic-format streaming
            if chunk_data.get("type") == "content_block_delta":
                delta = chunk_data.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield delta.get("text", "")
            # Nova-format streaming
            elif chunk_data.get("type") == "contentBlockDelta":
                yield chunk_data.get("delta", {}).get("text", "")


# Factory function for backward compatibility
def create_client(api_key: str = None, **kwargs) -> BedrockClient:
    """Create a Bedrock client.
    
    Args:
        api_key: Ignored (kept for API compatibility)
        **kwargs: Additional arguments (region, etc.)
    
    Returns:
        BedrockClient instance
    """
    if api_key:
        log.warning("API key provided but will be ignored - using IAM role")
    
    return BedrockClient(**kwargs)
