"""Pydantic models for API request/response."""

from pydantic import BaseModel, Field
from typing import Optional


# --- Tool ---

class ToolOut(BaseModel):
    id: str
    name: str
    description: str
    parameters: dict
    category: str
    created_at: str


# --- Agent Definition ---

class AgentDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    tool_ids: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    llm_config: dict = Field(default_factory=lambda: {"model": "mock-gpt", "temperature": 0.7})
    system_prompt: str = ""


class AgentDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tool_ids: Optional[list[str]] = None
    permissions: Optional[list[str]] = None
    llm_config: Optional[dict] = None
    system_prompt: Optional[str] = None


class AgentDefinitionOut(BaseModel):
    id: str
    name: str
    description: str
    tool_ids: list[str]
    permissions: list[str]
    llm_config: dict
    system_prompt: str
    created_at: str


# --- Agent Instance ---

class InstanceCreate(BaseModel):
    definition_id: str
    name: str = Field(..., min_length=1, max_length=100)
    config_override: dict = Field(default_factory=dict)


class InstanceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(running|paused|stopped)$")
    config_override: Optional[dict] = None


class InstanceOut(BaseModel):
    id: str
    definition_id: str
    definition_name: str = ""
    name: str
    status: str
    config_override: dict
    created_at: str
    updated_at: str
    # stats
    total_executions: int = 0
    error_count: int = 0


# --- Execution ---

class ExecuteRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ExecutionLogOut(BaseModel):
    id: str
    instance_id: str
    input_message: str
    output_message: str
    tools_used: list[str]
    status: str
    error_message: Optional[str] = None
    duration_ms: int = 0
    created_at: str
