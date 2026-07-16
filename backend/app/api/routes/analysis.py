from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from backend.app.workers.celery_worker import celery_app
from backend.app.services.analyzer import RISK_CATEGORIES
from backend.app.utils.logger import logger

router = APIRouter()

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Checks the status of a Celery background analysis job.
    """
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "status": async_result.status,
            "info": str(async_result.info) if async_result.info else None
        }

        if async_result.ready():
            response["result"] = async_result.result if async_result.successful() else None
            if async_result.failed():
                response["error"] = str(async_result.result)

        return response
    except Exception as e:
        logger.error(f"Error checking Celery task status for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve task status: {str(e)}"
        )

@router.get("/rules")
async def get_keyword_rules():
    """
    Returns the loaded risk keyword list and weights, grouped by category.
    """
    return RISK_CATEGORIES
