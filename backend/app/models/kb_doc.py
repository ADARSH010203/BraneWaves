from datetime import datetime, timezone
from pydantic import BaseModel, Field

class KBDocument(BaseModel):
    """A document uploaded to the user's persistent knowledge base."""
    id: str = Field(alias="_id")
    user_id: str
    filename: str
    content: str
    word_count: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}

class KBResponse(BaseModel):
    id: str
    filename: str
    word_count: int
    created_at: datetime
