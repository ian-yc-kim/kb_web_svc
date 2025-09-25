# kb_web_svc

Python Streamlit web application providing comprehensive kanban task management with 7-field task system, drag-and-drop functionality, and PostgreSQL persistence.

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

### Running the Application

After setting up your `.env` file with the desired database configuration:

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run the application:
   ```bash
   poetry run kb_web_svc
   ```

The application will automatically load the environment variables from your `.env` file and connect to the specified database. If no `DATABASE_URL` is provided, it will use an in-memory SQLite database by default.