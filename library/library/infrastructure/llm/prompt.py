import json

import yaml
from pydantic import BaseModel


def context_to_prompt(*, context: BaseModel) -> str:
    return str(yaml.safe_dump(json.loads(context.model_dump_json())))
