from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from ...core.models import ExecutionPlan, ExecutionResult
from ...core.orchestrator import APIOrchestrator
from ...core.plan_executor import PlanExecutor
from ...core.api_registry import APIRegistry
from ...config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["orchestration"])

# Initialize components
api_registry = None
orchestrator = None
executor = None

async def get_orchestrator():
    global api_registry, orchestrator, executor
    if not orchestrator:
        api_registry = APIRegistry(settings.assets_path)
        await api_registry.load_all_specs()
        orchestrator = APIOrchestrator(api_registry)
        executor = PlanExecutor(api_registry)
    return orchestrator, executor, api_registry

@router.post("/query")
async def execute_query(
    query: Dict[str, str],
    deps = Depends(get_orchestrator)
) -> Dict[str, Any]:
    orchestrator, executor, _ = deps

    try:
        user_query = query.get("query", "")
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")

        logger.info("Processing query", query=user_query)

        # Create plan
        plan = await orchestrator.create_execution_plan(user_query)

        # Execute plan
        result = await executor.execute(plan)

        return {
            "success": result.success,
            "data": result.data,  # Dict of operation_id -> result
            "errors": result.errors,
            "plan": {
                "id": plan.id,
                "steps": len(plan.steps),
                "resources": [q.target_resource for q in plan.parsed_queries.queries],
                "execution_time": result.execution_time,
                "api_calls_made": result.api_calls_made,
                "step_details": [
                    {
                        "id": step.id,
                        "operation_id": step.operation_id,
                        "api_name": step.api_name,
                        "method": step.method,
                        "path": step.path,
                        "parameters": step.parameters,
                        "depends_on": step.depends_on,
                        "extract_fields": step.extract_fields
                    }
                    for step in plan.steps
                ]
            }
        }

    except Exception as e:
        logger.error("Query execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan/{query}")
async def get_execution_plan(
    query: str,
    deps = Depends(get_orchestrator)
) -> Dict[str, Any]:
    orchestrator, _, _ = deps

    try:
        plan = await orchestrator.create_execution_plan(query)
        return {
            "query": plan.query,
            "resources": [q.target_resource for q in plan.parsed_queries.queries],
            "steps": [
                {
                    "id": step.id,
                    "operation_id": step.operation_id,
                    "api_name": step.api_name,
                    "method": step.method,
                    "path": step.path,
                    "parameters": step.parameters,
                    "depends_on": step.depends_on,
                    "extract_fields": step.extract_fields
                }
                for step in plan.steps
            ]
        }
    except Exception as e:
        logger.error("Plan creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/apis")
async def list_apis(deps = Depends(get_orchestrator)) -> Dict[str, Any]:
    _, _, api_registry = deps

    return {
        "apis": list(api_registry.specs.keys()),
        "total_operations": len(api_registry.operation_index)
    }

@router.get("/operations/{api_name}")
async def list_operations(
    api_name: str,
    deps = Depends(get_orchestrator)
) -> Dict[str, Any]:
    _, _, api_registry = deps

    operations = []
    for op_id, op_data in api_registry.operation_index.items():
        if op_data['api_name'] == api_name:
            operations.append({
                "operation_id": op_id,
                "method": op_data['method'],
                "path": op_data['path'],
                "summary": op_data['operation'].get('summary', '')
            })

    return {"api": api_name, "operations": operations}