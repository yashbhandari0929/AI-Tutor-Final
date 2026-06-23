"""
schemas/chat.py — Phase 8: chat history

New file. Doesn't touch the old api/chat.py contract — that endpoint
keeps working exactly as before for backward compatibility.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class MessageOut(BaseModel):
    id: int
    role: str            # "user" | "assistant"
    content: str
    used_rag: bool
    created_at: datetime
    used_file_context: bool = False
    sources: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationOut]


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
    attachments: list[dict]   # lightweight — see api/conversations.py for shape


class CreateMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    used_file_context: bool = False
    sources: list[str] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str
