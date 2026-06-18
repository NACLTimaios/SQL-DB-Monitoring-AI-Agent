"""Chatbot configuration and conversation models."""

import json
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, Boolean
from store.models import Base


def _now():
    return datetime.now(tz=timezone.utc)


class ChatbotConfig(Base):
    """Chatbot configuration stored in database."""

    __tablename__ = "chatbot_config"

    id = Column(Integer, primary_key=True, default=1)
    llm_provider = Column(String(50), default="anthropic")
    llm_model = Column(String(100), default="claude-3-5-sonnet-20241022")
    llm_api_key = Column(String(500), nullable=True)  # Encrypted in production
    system_prompt = Column(Text, default="")
    tools = Column(JSON, default=list)  # List of tool names
    guardrails = Column(JSON, default=dict)  # Safety constraints
    enabled = Column(Boolean, default=True)
    prisma_airs_enabled = Column(Boolean, default=True)  # Toggle for demo purposes
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    def to_dict(self):
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "system_prompt": self.system_prompt,
            "tools": self.tools or [],
            "guardrails": self.guardrails or {},
            "enabled": self.enabled,
            "prisma_airs_enabled": self.prisma_airs_enabled,
        }


class ChatMessage(Base):
    """Chat message history."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=True)  # Which user sent this message (nullable for backward compatibility)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=True)
    tools_used = Column(JSON, default=list)
    tool_outputs = Column(JSON, nullable=True)  # Raw tool outputs for audit
    prisma_airs_user_safe = Column(Boolean, default=True)  # User input scan result
    prisma_airs_response_safe = Column(Boolean, default=True)  # Response scan result
    created_at = Column(DateTime(timezone=True), default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
            "tools_used": self.tools_used or [],
            "tool_outputs": self.tool_outputs or {},
            "prisma_airs_user_safe": self.prisma_airs_user_safe,
            "prisma_airs_response_safe": self.prisma_airs_response_safe,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
