import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from prance import ResolvingParser
from openapi_spec_validator import validate_spec
import structlog
from ..config import settings

logger = structlog.get_logger()

class APIRegistry:
    def __init__(self, assets_path: str):
        self.assets_path = Path(assets_path)
        self.specs: Dict[str, Any] = {}
        self.operation_index: Dict[str, Dict[str, Any]] = {}

    async def load_all_specs(self):
        for file_path in self.assets_path.glob("*.json"):
            try:
                print(f"Loading API spec from {file_path}")
                await self.load_spec(file_path)
            except Exception as e:
                logger.error(f"Failed to load {file_path}", error=str(e))

    async def load_spec(self, file_path: Path):
        api_name = file_path.stem.replace('-api', '').replace('_api', '')

        try:
            parser = ResolvingParser(str(file_path))
            spec = parser.specification
        except:
            with open(file_path) as f:
                spec = json.load(f)

        self.specs[api_name] = spec
        self._index_operations(api_name, spec)

        logger.info(f"Loaded API spec: {api_name}")

    def _index_operations(self, api_name: str, spec: Dict[str, Any]):
        base_url = self._get_base_url(spec)

        for path, path_item in spec.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    operation_id = operation.get('operationId', f"{method}_{path}")

                    self.operation_index[operation_id] = {
                        'api_name': api_name,
                        'method': method.upper(),
                        'path': path,
                        'base_url': base_url,
                        'operation': operation,
                        'parameters': operation.get('parameters', []),
                        'request_body': operation.get('requestBody', {}),
                        'responses': operation.get('responses', {})
                    }

    def _get_base_url(self, spec: Dict[str, Any]) -> str:
        scheme = getattr(settings, 'api_scheme', None) or spec.get('schemes', ['https'])[0]
        host = getattr(settings, 'api_host', None) or spec.get('host', 'localhost')
        base_path = spec.get('basePath', '')
        return f"{scheme}://{host}{base_path}"

    def find_operations_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        operations = []
        resource_lower = resource.lower()

        for op_id, op_data in self.operation_index.items():
            if (resource_lower in op_id.lower() or
                resource_lower in op_data['path'].lower() or
                any(resource_lower in tag.lower() 
                    for tag in op_data['operation'].get('tags', []))):
                operations.append({
                    'operation_id': op_id,
                    **op_data
                })

        return operations

    def get_operation_details(self, operation_id: str) -> Optional[Dict[str, Any]]:
        return self.operation_index.get(operation_id)