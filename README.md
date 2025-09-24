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