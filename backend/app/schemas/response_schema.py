from pydantic import BaseModel
from typing import Any, Dict, Optional

class SystemStatusResponse(BaseModel):
    status: str
    postgres: str
    redis: str
    version: str = "1.0.0"

class BulkAnalysisRequest(BaseModel):
    domains: list[str]

class BulkAnalysisResponse(BaseModel):
    task_id: str
    message: str
