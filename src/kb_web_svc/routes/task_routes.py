"""FastAPI routes for task-related operations.

This module implements REST API endpoints for task management including
creation, retrieval, updating, and deletion operations.
"""

import logging
from uuid import UUID
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.task import TaskDeleteResponse
from ..services.task_service import delete_task, TaskNotFoundError

logger = logging.getLogger(__name__)

# Create API router
task_router = APIRouter()


@task_router.delete("/tasks/{task_id}", response_model=TaskDeleteResponse)
async def delete_task_endpoint(
    task_id: UUID,
    soft_delete: bool = True,
    db: Session = Depends(get_db)
) -> TaskDeleteResponse:
    """Delete a task by ID with support for soft and hard deletion.
    
    Args:
        task_id: UUID of the task to delete
        soft_delete: Boolean flag for soft delete (default True). 
                    If True, sets deleted_at timestamp.
                    If False, permanently removes the task from database.
        db: Database session dependency
        
    Returns:
        TaskDeleteResponse with success message and task ID
        
    Raises:
        HTTPException: 404 if task not found, 500 for server errors
    """
    logger.info(f"DELETE /tasks/{task_id} request - soft_delete: {soft_delete}")
    
    try:
        # Call service layer to perform deletion
        result = delete_task(task_id=task_id, db=db, soft=soft_delete)
        
        # Return structured response
        return TaskDeleteResponse(
            message=result["message"],
            task_id=task_id
        )
        
    except TaskNotFoundError as e:
        logger.warning(f"Task not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
