from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid
from datetime import datetime

class QueryType(str, Enum):
    GET = "get"
    LIST = "list"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class ParsedQuery(BaseModel):
    query_type: QueryType
    target_resource: str
    filters: Dict[str, Any] = {}
    required_fields: List[str] = []

class MultiParsedQuery(BaseModel):
    queries: List[ParsedQuery]

class APICallPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_name: str
    operation_id: str
    method: str
    path: str
    parameters: Dict[str, Any] = {}
    body: Optional[Dict[str, Any]] = None
    extract_fields: Dict[str, str] = {}

class ExecutionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    parsed_queries: MultiParsedQuery
    steps: List[APICallPlan] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)



class ExecutionResult(BaseModel):
    plan_id: str
    success: bool
    data: Any
    errors: List[str] = []
    execution_time: float
    api_calls_made: int