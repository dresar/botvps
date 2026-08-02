"""Data models untuk ai_assistant plugin dengan Hermes Memory System."""

from datetime import datetime
from pydantic import BaseModel, Field


class AIMemoryDTO(BaseModel):
    """DTO memori jangka panjang / aturan pengguna."""

    id: int | None = None
    telegram_id: int
    memory_type: str = "rule"  # 'rule', 'preference', 'fact'
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AIChatMessageDTO(BaseModel):
    """DTO histori pesan percakapan."""

    id: int | None = None
    telegram_id: int
    role: str  # 'user', 'assistant'
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
