# KB Web Service API Documentation

## Overview

The KB Web Service provides a REST API for managing kanban tasks with comprehensive CRUD operations. The API supports both soft and hard deletion of tasks, with proper error handling and validation.

## Base URL

```
http://localhost:8501/api
```

## Authentication

Currently, the API does not implement authentication or authorization. All endpoints are publicly accessible. **Note:** In a production environment, proper authentication and authorization mechanisms should be implemented at the application or infrastructure level.

## Endpoints

### Health Check

**GET** `/health`

Returns the health status of the API service.

**Response:**
```json
{
  "status": "healthy"
}
```

### Delete Task

**DELETE** `/api/tasks/{task_id}`

Deletes a task by its unique identifier. Supports both soft deletion (default) and hard deletion based on the `soft_delete` query parameter.

#### Purpose
- **Soft Delete:** Marks the task as deleted by setting the `deleted_at` timestamp while preserving the task data in the database. This allows for potential recovery and maintains referential integrity.
- **Hard Delete:** Permanently removes the task from the database. This action is irreversible.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | UUID | Yes | The unique identifier of the task to delete |

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `soft_delete` | boolean | No | `true` | Whether to perform soft deletion (`true`) or hard deletion (`false`) |

#### Example Requests

**Soft Delete (Default):**
```bash
curl -X DELETE "http://localhost:8501/api/tasks/123e4567-e89b-12d3-a456-426614174000"
```

**Explicit Soft Delete:**
```bash
curl -X DELETE "http://localhost:8501/api/tasks/123e4567-e89b-12d3-a456-426614174000?soft_delete=true"
```

**Hard Delete:**
```bash
curl -X DELETE "http://localhost:8501/api/tasks/123e4567-e89b-12d3-a456-426614174000?soft_delete=false"
```

#### Success Responses

**Soft Delete Success (200 OK):**
```json
{
  "message": "Task soft-deleted successfully",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Hard Delete Success (200 OK):**
```json
{
  "message": "Task hard-deleted successfully",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Error Responses

**Task Not Found (404 Not Found):**

Returned when the specified task ID does not exist in the database.

```json
{
  "detail": "Task with ID 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

**Invalid Task ID Format (422 Unprocessable Entity):**

Returned when the task ID is not a valid UUID format.

```json
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["path", "task_id"],
      "msg": "Input should be a valid UUID, invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found `g` at 35",
      "input": "123e4567-e89b-12d3-a456-42661417400g"
    }
  ]
}
```

**Internal Server Error (500 Internal Server Error):**

Returned when an unexpected error occurs during task deletion.

```json
{
  "detail": "Internal server error"
}
```

#### Response Schema

**TaskDeleteResponse:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Success message indicating the type of deletion performed |
| `task_id` | UUID | The UUID of the deleted task |

#### Behavior Notes

1. **Soft Deletion:** When `soft_delete=true` (default):
   - The task remains in the database
   - The `deleted_at` field is set to the current timestamp
   - The `last_modified` field is automatically updated
   - All other task data is preserved
   - The task can potentially be restored by clearing the `deleted_at` field

2. **Hard Deletion:** When `soft_delete=false`:
   - The task is permanently removed from the database
   - All task data is lost and cannot be recovered
   - This operation is irreversible

3. **Idempotency:** 
   - Soft deleting an already soft-deleted task will succeed and update the `deleted_at` timestamp
   - Hard deleting an already hard-deleted task will return a 404 error

4. **Transaction Management:** All deletion operations are performed within database transactions with automatic rollback on errors

#### Security Considerations

- **Authorization:** This API layer does not implement authorization checks. In production environments, ensure that:
  - Only authorized users can delete tasks
  - Users can only delete tasks they have permission to modify
  - Consider implementing role-based access control (RBAC)
  - Log all deletion operations for audit purposes

- **Data Protection:** 
  - Consider requiring additional confirmation for hard deletion operations
  - Implement soft deletion as the default to prevent accidental data loss
  - Consider data retention policies for soft-deleted tasks

- **Rate Limiting:** Consider implementing rate limiting to prevent abuse of deletion endpoints

## Error Handling

All API endpoints follow consistent error response patterns:

- **4xx Client Errors:** Indicate issues with the request (invalid parameters, missing resources)
- **5xx Server Errors:** Indicate internal server issues (database errors, unexpected exceptions)
- **Detailed Error Messages:** All errors include descriptive messages to help with debugging
- **Structured Error Responses:** Error responses follow FastAPI's standard error format

## Development and Testing

For development and testing purposes:

1. **Health Check:** Use the `/health` endpoint to verify API availability
2. **Database State:** Soft-deleted tasks remain in the database and can be queried directly
3. **Testing:** The API includes comprehensive test coverage for all scenarios
4. **Logging:** All operations are logged with appropriate severity levels

## Future Enhancements

- Authentication and authorization implementation
- Bulk deletion operations
- Task restoration endpoint for soft-deleted tasks
- Deletion history and audit logs
- Scheduled cleanup of old soft-deleted tasks