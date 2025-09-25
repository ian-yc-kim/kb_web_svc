# kb_web_svc

Python Streamlit web application providing comprehensive kanban task management with 7-field task system, drag-and-drop functionality, and PostgreSQL persistence. Includes task creation, status management, export/import collaboration features, and responsive UI design.

## Setup and Installation

### Prerequisites

Ensure you have Poetry installed on your system. If you don't have Poetry, install it by following the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation).

### Installation Steps

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Set up environment configuration:**
   Create a `.env` file in the root directory of the project (see Database Configuration section below for details).

3. **Run database migrations:**
   ```bash
   poetry run alembic upgrade head
   ```

This will set up your development environment with all necessary dependencies and prepare the database schema.

## Database Configuration

The application reads database configuration from the `DATABASE_URL` environment variable. You can set this variable using a `.env` file in the root directory.

### Setting up your `.env` file

Create a `.env` file in the root directory of the project and add your database configuration:

#### PostgreSQL (Production)
```
DATABASE_URL="postgresql://username:password@host:port/dbname"
```

#### SQLite File-based (Development)
```
DATABASE_URL="sqlite:///./test.db"
```

#### SQLite In-memory (Default)
If you omit the `DATABASE_URL` environment variable, the application will default to using an in-memory SQLite database. This is useful for testing and development when you don't need data persistence.

## Database Migrations

This application uses Alembic to manage database schema migrations. Alembic is a database migration tool for SQLAlchemy that allows you to version control your database schema changes and apply them consistently across different environments.

### Prerequisites

Before working with migrations, ensure you have:

1. Installed all dependencies:
   ```bash
   poetry install
   ```

2. Configured your database connection by setting up your `.env` file with the appropriate `DATABASE_URL` (see Database Configuration section above).

### Migration Commands

#### Generate a new migration script
When you make changes to your SQLAlchemy models, generate a new migration script:

```bash
poetry run alembic revision --autogenerate -m "<description_of_change>"
```

**Important:** Always review the generated migration script before applying it to ensure it correctly captures your intended changes.

#### Apply all pending migrations
To apply all pending migrations to your database:

```bash
poetry run alembic upgrade head
```

#### Roll back the last applied migration
To roll back the most recent migration:

```bash
poetry run alembic downgrade -1
```

#### Roll back all migrations to base
To roll back all migrations and return to an empty database:

```bash
poetry run alembic downgrade base
```

### Important Notes

- **Environment Configuration**: Alembic reads the `DATABASE_URL` environment variable to determine which database to target. Always ensure your `.env` file is properly configured and points to the intended database before running migration commands.

- **Migration Scripts Location**: Generated migration scripts are stored in the `alembic/versions/` directory. These files should be committed to version control.

- **Development vs Production**: When working with SQLite for development, you can use a file-based database (`sqlite:///./test.db`) to persist data between application restarts. For production, use PostgreSQL with the appropriate connection string.

## Running the Application

After completing the setup and installation steps, you have two options to run the application:

### Option 1: Using the console script (Recommended)
```bash
poetry run kb_web_svc
```

### Option 2: Direct Streamlit command
```bash
poetry run streamlit run src/kb_web_svc/app.py
```

### Accessing the Application
Once started, open your web browser and navigate to [http://localhost:8501](http://localhost:8501) (default Streamlit port).

The application will automatically load the environment variables from your `.env` file and connect to the specified database. If no `DATABASE_URL` is provided, it will use an in-memory SQLite database by default.

## How to Create Tasks

The application provides an intuitive web interface for creating and managing kanban tasks:

1. **Access the task creation page:**
   - Once the application is running, navigate to the "Create Task" tab in the Streamlit interface
   - The tab is located in the main navigation area of the application

2. **Fill out the task creation form:**
   - **Title** (required): Enter a descriptive title for your task
   - **Assignee** (optional): Specify who the task is assigned to
   - **Labels** (optional): Add comma-separated labels for categorization (e.g., "frontend, urgent, bug-fix")
   - **Due Date** (optional): Select a due date using the date picker
   - **Priority** (optional): Choose from Critical, High, Medium, or Low priority levels
   - **Status** (required): Select the initial status - To Do, In Progress, or Done
   - **Description** (optional): Provide detailed information about the task
   - **Estimated Time** (optional): Use the "Advanced Options" section to specify estimated time in hours

3. **Submit the task:**
   - Click the "Create Task" button to save your task
   - The system will validate your input and provide feedback
   - Successfully created tasks are automatically persisted to the database
   - You'll see a success message confirming the task creation

4. **Task validation:**
   - The system automatically validates input fields
   - Due dates cannot be set in the past
   - Priority and status values must be from the predefined lists
   - Error messages will guide you if any validation fails

## Task Retrieval

### Overview

The task retrieval functionality allows you to list tasks with comprehensive filtering, pagination, and sorting capabilities, as well as retrieve individual tasks by their unique identifier. This is useful for building task dashboards, search functionality, and detailed task views.

### Functions

#### get_task_by_id

**Signature:** `get_task_by_id(db: Session, task_id: UUID) -> Optional[Dict[str, Any]]`

**Parameters:**
- `db`: SQLAlchemy database session
- `task_id`: UUID of the task to retrieve

**Returns:** Dictionary representation of the task if found, `None` otherwise

**Error Behavior:** Re-raises database errors after logging them with full exception information.

#### list_tasks

**Signature:** `list_tasks(db: Session, filters: TaskFilterParams) -> Tuple[List[Dict[str, Any]], int]`

**Parameters:**
- `db`: SQLAlchemy database session
- `filters`: TaskFilterParams object containing filter, sort, and pagination options

**Returns:** Tuple containing:
- List of task dictionaries (serialized tasks)
- Total count of matching tasks (before pagination is applied)

**Error Behavior:** Raises `ValueError` for invalid `sort_by` or `sort_order` parameters. Re-raises database errors after logging them with full exception information.

### Filter Parameters (TaskFilterParams)

The `TaskFilterParams` schema provides comprehensive filtering and pagination options:

- **status** (Optional[str]): Filter by exact task status. Must be one of: "To Do", "In Progress", "Done"
- **priority** (Optional[str]): Filter by exact task priority. Must be one of: "Critical", "High", "Medium", "Low"
- **assignee** (Optional[str]): Filter by assignee using case-insensitive partial matching
- **due_date_start** (Optional[date]): Filter tasks due on or after this date (inclusive)
- **due_date_end** (Optional[date]): Filter tasks due on or before this date (inclusive)
- **search_term** (Optional[str]): Search in task title and description using case-insensitive partial matching
- **limit** (int): Maximum number of results to return (minimum: 1, default: 10)
- **offset** (int): Number of results to skip for pagination (minimum: 0, default: 0)
- **sort_by** (str): Field to sort by. Must be one of: "created_at", "due_date", "priority" (default: "created_at")
- **sort_order** (str): Sort order. Must be one of: "asc", "desc" (default: "desc")

**Note:** All optional string fields treat empty strings as `None` and are ignored in filtering.

### Sorting Semantics

- **created_at**: Standard chronological ordering (oldest first for "asc", newest first for "desc")
- **due_date**: Standard date ordering (earliest first for "asc", latest first for "desc")
- **priority**: Logical priority ordering where Critical > High > Medium > Low
  - "desc": Critical, High, Medium, Low, then tasks with no priority
  - "asc": Low, Medium, High, Critical, then tasks with no priority

### Return Format

Both functions return serialized task dictionaries with the following structure:

```python
{
    'id': str,                    # UUID as string
    'title': str,                 # Task title
    'assignee': Optional[str],    # Assigned person
    'due_date': Optional[str],    # ISO 8601 date string (YYYY-MM-DD)
    'description': Optional[str], # Task description
    'priority': Optional[str],    # Priority enum value as string
    'labels': List[str],          # List of labels (empty list if no labels)
    'estimated_time': Optional[float], # Estimated time in hours
    'status': str,                # Status enum value as string
    'created_at': str,           # ISO 8601 datetime string with timezone
    'last_modified': str         # ISO 8601 datetime string with timezone
}
```

The `list_tasks` function returns this along with a total count integer representing the number of matching tasks before pagination is applied.

### Usage Examples (Python)

#### Example 1: Basic Task Listing

```python
from kb_web_svc.services.task_service import list_tasks
from kb_web_svc.schemas.task import TaskFilterParams
from kb_web_svc.database import get_db

# Create database session
with next(get_db()) as db:
    # Get first 10 tasks with default sorting (newest first)
    filters = TaskFilterParams()
    tasks, total_count = list_tasks(db, filters)
    
    print(f"Retrieved {len(tasks)} tasks out of {total_count} total")
    if tasks:
        first_task = tasks[0]
        print(f"First task: {first_task['title']} - Status: {first_task['status']}")
        print(f"Task fields: {list(first_task.keys())}")
```

#### Example 2: Filter by Status and Assignee

```python
from kb_web_svc.services.task_service import list_tasks
from kb_web_svc.schemas.task import TaskFilterParams
from kb_web_svc.database import get_db

# Create database session
with next(get_db()) as db:
    # Find "In Progress" tasks assigned to anyone with "john" in their name
    filters = TaskFilterParams(
        status="In Progress",
        assignee="john",
        limit=20,
        offset=0,
        sort_by="created_at",
        sort_order="desc"
    )
    tasks, total_count = list_tasks(db, filters)
    
    print(f"Found {len(tasks)} 'In Progress' tasks for John out of {total_count} total matching")
    for task in tasks:
        print(f"- {task['title']} (Assignee: {task['assignee']})")
```

#### Example 3: Filter by Due Date Range and Priority

```python
from datetime import date, timedelta
from kb_web_svc.services.task_service import list_tasks
from kb_web_svc.schemas.task import TaskFilterParams
from kb_web_svc.database import get_db

# Create database session
with next(get_db()) as db:
    # Find high-priority tasks due in the next week
    today = date.today()
    next_week = today + timedelta(days=7)
    
    filters = TaskFilterParams(
        priority="High",
        due_date_start=today,
        due_date_end=next_week,
        sort_by="due_date",
        sort_order="asc"
    )
    tasks, total_count = list_tasks(db, filters)
    
    print(f"Found {len(tasks)} high-priority tasks due this week")
    for task in tasks:
        print(f"- {task['title']} (Due: {task['due_date']})")
```

#### Example 4: Full-text Search with Pagination

```python
from kb_web_svc.services.task_service import list_tasks
from kb_web_svc.schemas.task import TaskFilterParams
from kb_web_svc.database import get_db

# Create database session
with next(get_db()) as db:
    # Search for tasks containing "bug" in title or description
    # Get second page of results, sorted by priority (most critical first)
    filters = TaskFilterParams(
        search_term="bug",
        limit=10,
        offset=10,  # Skip first 10 results (page 2)
        sort_by="priority",
        sort_order="desc"
    )
    tasks, total_count = list_tasks(db, filters)
    
    print(f"Page 2 of bug-related tasks: {len(tasks)} tasks (Total: {total_count})")
    for task in tasks:
        priority = task['priority'] or 'No Priority'
        print(f"- [{priority}] {task['title']}")
```

#### Example 5: Retrieve Task by ID

```python
from uuid import UUID
from kb_web_svc.services.task_service import get_task_by_id
from kb_web_svc.database import get_db

# Create database session
with next(get_db()) as db:
    # Retrieve a specific task by UUID
    task_id = UUID("123e4567-e89b-12d3-a456-426614174000")  # Example UUID
    task = get_task_by_id(db, task_id)
    
    if task:
        print(f"Found task: {task['title']}")
        print(f"Status: {task['status']}")
        print(f"Created: {task['created_at']}")
        print(f"Assignee: {task['assignee'] or 'Unassigned'}")
    else:
        print(f"Task with ID {task_id} not found")
```

### Error Handling Notes

- **Invalid Parameters**: The `list_tasks` function raises `ValueError` for invalid `sort_by` or `sort_order` values. Valid `sort_by` options are: "created_at", "due_date", "priority". Valid `sort_order` options are: "asc", "desc".

- **Database Errors**: Both functions log database errors using `logging.error(e, exc_info=True)` and then re-raise the original exception. Your application should handle these exceptions appropriately.

- **Session Management**: Always ensure proper database session cleanup using context managers or try/finally blocks. The examples above use the `get_db()` generator with context manager syntax for automatic cleanup.

## Running Tests

The project includes comprehensive unit tests to ensure code quality and functionality:

```bash
poetry run pytest
```

**Important:** The tests use an SQLite in-memory database for isolation and speed. You don't need to connect to a real PostgreSQL database to run the tests - the testing framework automatically handles database setup and teardown for each test.

### Test Coverage

The test suite covers:
- Database models and ORM functionality
- Task service layer business logic
- Streamlit UI components
- Database connection and session management
- Input validation and error handling
- Data persistence and retrieval