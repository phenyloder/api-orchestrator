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

class APICallPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_name: str
    operation_id: str
    method: str
    path: str
    parameters: Dict[str, Any] = {}
    body: Optional[Dict[str, Any]] = None
    depends_on: List[str] = []
    extract_fields: Dict[str, str] = {}

class ExecutionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    parsed_query: ParsedQuery
    steps: List[APICallPlan] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_dependency_order(self) -> List[APICallPlan]:
        import networkx as nx

        G = nx.DiGraph()
        for step in self.steps:
            G.add_node(step.id)
            for dep in step.depends_on:
                G.add_edge(dep, step.id)

        try:
            ordered_ids = list(nx.topological_sort(G))
            return [next(s for s in self.steps if s.id == sid) for sid in ordered_ids]
        except nx.NetworkXError:
            raise ValueError("Circular dependency detected")

class ExecutionResult(BaseModel):
    plan_id: str
    success: bool
    data: Any
    errors: List[str] = []
    execution_time: float
    api_calls_made: int