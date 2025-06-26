import httpx
import asyncio
from typing import Dict, Any
import time
import structlog
from jsonpath_ng import parse
from .models import ExecutionPlan, ExecutionResult, APICallPlan
from .api_registry import APIRegistry
from ..config import settings

logger = structlog.get_logger()

class PlanExecutor:
    def __init__(self, api_registry: APIRegistry):
        self.api_registry = api_registry
        self.client = httpx.AsyncClient(timeout=settings.api_timeout)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        start_time = time.time()
        context = {}
        errors = []
        api_calls_made = 0
        resource_results = {}

        try:
            ordered_steps = plan.get_dependency_order()

            for step in ordered_steps:
                try:
                    step = self._substitute_parameters(step, context)

                    result = await self._execute_step(step)
                    context[step.id] = result
                    api_calls_made += 1

                    for field_name, json_path in step.extract_fields.items():
                        value = self._extract_value(result, json_path)
                        context[field_name] = value
                        logger.info(f"Extracted {field_name}={value}")

                    # Group results by resource (operation_id or resource name)
                    resource_key = step.operation_id
                    resource_results[resource_key] = result

                except Exception as e:
                    logger.error(f"Step failed: {step.operation_id}", error=str(e))
                    errors.append(f"Step {step.operation_id}: {str(e)}")

        except Exception as e:
            errors.append(f"Execution failed: {str(e)}")

        execution_time = time.time() - start_time

        final_data = resource_results

        return ExecutionResult(
            plan_id=plan.id,
            success=len(errors) == 0,
            data=final_data,
            errors=errors,
            execution_time=execution_time,
            api_calls_made=api_calls_made
        )

    async def _execute_step(self, step: APICallPlan) -> Dict[str, Any]:
        op_details = self.api_registry.get_operation_details(step.operation_id)
        if not op_details:
            raise ValueError(f"Operation {step.operation_id} not found")

        url = op_details['base_url'] + step.path

        for param in op_details.get('parameters', []):
            if param.get('in') == 'path':
                param_name = param['name']
                if param_name in step.parameters:
                    url = url.replace(f"{{{param_name}}}", str(step.parameters[param_name]))

        request_kwargs = {
            'method': step.method,
            'url': url,
        }

        query_params = {}
        for param in op_details.get('parameters', []):
            if param.get('in') == 'query' and param['name'] in step.parameters:
                query_params[param['name']] = step.parameters[param['name']]

        if query_params:
            request_kwargs['params'] = query_params

        if step.body:
            request_kwargs['json'] = step.body
        elif step.method in ['POST', 'PUT', 'PATCH']:
            body_params = {k: v for k, v in step.parameters.items() 
                          if k not in query_params}
            if body_params:
                request_kwargs['json'] = body_params

        if settings.rws_username and settings.rws_password:
            request_kwargs['auth'] = (settings.rws_username, settings.rws_password)

        logger.info(f"Executing API call", 
                   operation=step.operation_id, 
                   url=url,
                   method=step.method)

        response = await self.client.request(**request_kwargs)
        response.raise_for_status()

        return response.json()

    def _substitute_parameters(self, step: APICallPlan, context: Dict[str, Any]) -> APICallPlan:
        import copy
        step_copy = copy.deepcopy(step)

        def substitute(obj):
            if isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
                var_name = obj[2:-1]
                return context.get(var_name, obj)
            elif isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(v) for v in obj]
            return obj

        step_copy.parameters = substitute(step_copy.parameters)
        if step_copy.body:
            step_copy.body = substitute(step_copy.body)

        return step_copy

    def _extract_value(self, data: Dict[str, Any], json_path: str) -> Any:
        try:
            if json_path.startswith('$.'):
                json_path = json_path[2:]

            if '.' not in json_path and '[' not in json_path:
                return data.get(json_path)

            jsonpath_expr = parse(json_path)
            matches = jsonpath_expr.find(data)
            return matches[0].value if matches else None
        except Exception:
            return data.get(json_path.split('.')[-1])