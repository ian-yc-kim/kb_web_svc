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