from pydantic import BaseModel
from typing import Optional, List

class SessionsPatchParams(BaseModel):
    session_key: str
    label: Optional[str] = None
    model_override: Optional[str] = None
    thinking_level: Optional[int] = None
    verbose_level: Optional[int] = None
    reasoning_level: Optional[int] = None

class ExecAllowParams(BaseModel):
    request_id: str
    persist: Optional[bool] = False
    command: Optional[str] = None
    tool_name: Optional[str] = None

class ExecDenyParams(BaseModel):
    request_id: str
    feedback: Optional[str] = None
    command: Optional[str] = None
    tool_name: Optional[str] = None

class ChannelsListModel(BaseModel):
    channels: List[str]
