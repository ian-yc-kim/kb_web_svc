import streamlit as st
import logging

# Import database functionality
from .database import get_db

# Import state management functions
from .state_management import initialize_session_state, load_tasks_from_db_to_session

# Import task form component
from .components.task_form import render_task_form

# Global configuration (if needed)
st.set_page_config(page_title="kb_web_svc App", layout="wide")

# Set up logging
logger = logging.getLogger(__name__)


def render_ui() -> None:
    """Render the main UI with session state initialization and task loading.
    
    This function initializes the Streamlit session state and loads tasks from the database,
    then displays the task creation form with database session integration.
    """
    # Initialize session state first
    initialize_session_state()
    
    # Load tasks from database into session state
    db_gen = None
    try:
        db_gen = get_db()
        db = next(db_gen)
        load_tasks_from_db_to_session(db)
        logger.info("Successfully loaded tasks from database to session state")
        
        # Display the kanban board UI
        st.title("Kanban Board")
        
        # Add task creation form with database session
        st.subheader("Create Task")
        render_task_form(db)
        
    except Exception as e:
        logger.error(e, exc_info=True)
        # Continue rendering UI even if task loading fails
        st.error("An error occurred while loading tasks. Please try again.")
        
        # Still render the form but without database functionality
        st.title("Kanban Board")
        st.subheader("Create Task")
        
        # Create a dummy db session for form rendering when database fails
        try:
            render_task_form(None)  # Pass None as fallback
        except Exception as form_error:
            logger.error(f"Error rendering task form: {form_error}", exc_info=True)
            st.error("Unable to render task form. Please refresh the page.")
    finally:
        # Ensure generator cleanup
        if db_gen is not None:
            try:
                next(db_gen)
            except StopIteration:
                pass  # Generator properly closed
            except Exception as cleanup_error:
                logger.error(f"Error during database cleanup: {cleanup_error}", exc_info=True)


# Render the main UI
render_ui()
