from typing import Dict, List, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import OutputFixingParser
import json
import structlog
from .models import ParsedQuery, ExecutionPlan, APICallPlan, QueryType
from .api_registry import APIRegistry
from ..config import settings
from ..utils.token_manager import get_token
from ..utils.llm_model import LLMModel

logger = structlog.get_logger()

class APIOrchestrator:
    def __init__(self, api_registry: APIRegistry):
        self.api_registry = api_registry

    @property
    def llm(self):
        return LLMModel.get_llm()

    async def create_execution_plan(self, user_query: str) -> ExecutionPlan:
        parsed_query = await self._parse_query(user_query)
        logger.info("Parsed query", query_type=parsed_query.query_type, 
                   target=parsed_query.target_resource)

        relevant_ops = self.api_registry.find_operations_by_resource(
            parsed_query.target_resource
        )

        plan = await self._create_plan_with_llm(
            user_query, parsed_query, relevant_ops
        )

        return plan

    async def _parse_query(self, user_query: str) -> ParsedQuery:
        parser = PydanticOutputParser(pydantic_object=ParsedQuery)
        prompt = f'''
Parse this user query into a structured format.

User Query: {user_query}

Identify:
1. Query type (get, list, create, update, delete)
2. Target resource (e.g., account, rateplan, user)
3. Any filters or conditions
4. Required fields in response

{parser.get_format_instructions()}
'''
        messages = [
            SystemMessage(content="You are an API query parser. Be precise and extract only what's explicitly mentioned."),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm)
        return fixing_parser.parse(response.content)

    async def _create_plan_with_llm(
        self, 
        user_query: str, 
        parsed_query: ParsedQuery,
        relevant_ops: List[Dict[str, Any]]
    ) -> ExecutionPlan:
        ops_summary = self._create_operations_summary(relevant_ops)

        prompt = f'''
Create an execution plan for this query. Be minimal and precise.

User Query: {user_query}
Target Resource: {parsed_query.target_resource}

Available Operations:
{ops_summary}

Rules:
1. Only include necessary API calls
2. If getting a resource by ID, check if ID is in the query
3. Chain calls when output of one is needed as input for another
4. Return a valid JSON array

Example response:
[
  {{
    "operation_id": "getAccount",
    "parameters": {{"accountId": "12345"}},
    "extract_fields": {{"rateplanId": "$.rateplanId"}}
  }},
  {{
    "operation_id": "getRateplan",
    "parameters": {{"rateplanId": "${{rateplanId}}"}},
    "depends_on": ["getAccount"]
  }}
]
'''

        messages = [
            SystemMessage(content="You are an API orchestration expert. Create minimal, efficient execution plans."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)

        try:
            steps_data = json.loads(response.content)
        except:
            import re
            json_match = re.search(r'$$.*$$', response.content, re.DOTALL)
            if json_match:
                steps_data = json.loads(json_match.group())
            else:
                steps_data = []

        plan = ExecutionPlan(
            query=user_query,
            parsed_query=parsed_query
        )

        op_to_step = {}

        for step_data in steps_data:
            op_details = self.api_registry.get_operation_details(step_data['operation_id'])
            if op_details:
                step = APICallPlan(
                    api_name=op_details['api_name'],
                    operation_id=step_data['operation_id'],
                    method=op_details['method'],
                    path=op_details['path'],
                    parameters=step_data.get('parameters', {}),
                    body=step_data.get('body'),
                    extract_fields=step_data.get('extract_fields', {})
                )

                # Map dependencies
                for dep_op in step_data.get('depends_on', []):
                    if dep_op in op_to_step:
                        step.depends_on.append(op_to_step[dep_op])

                op_to_step[step_data['operation_id']] = step.id
                plan.steps.append(step)

        return plan

    def _create_operations_summary(self, operations: List[Dict[str, Any]]) -> str:
        summary = []
        for op in operations[:10]:
            params = [p['name'] for p in op.get('parameters', [])]
            summary.append(
                f"- {op['operation_id']}: {op['method']} {op['path']} "
                f"(params: {', '.join(params)})"
            )
        return '\n'.join(summary)