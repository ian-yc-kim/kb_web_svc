import streamlit as st
import logging

# Import database functionality
from .database import get_db

# Import state management functions
from .state_management import initialize_session_state, load_tasks_from_db_to_session

# Global configuration (if needed)
st.set_page_config(page_title="kb_web_svc App", layout="wide")

# Set up logging
logger = logging.getLogger(__name__)


def render_ui() -> None:
    """Render the main UI with session state initialization and task loading.
    
    This function initializes the Streamlit session state and loads tasks from the database,
    then displays the current board state for verification.
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
    except Exception as e:
        logger.error(e, exc_info=True)
        # Continue rendering UI even if task loading fails
    finally:
        # Ensure generator cleanup
        if db_gen is not None:
            try:
                next(db_gen)
            except StopIteration:
                pass  # Generator properly closed
            except Exception as cleanup_error:
                logger.error(f"Error during database cleanup: {cleanup_error}", exc_info=True)
    
    # Display the kanban board UI
    st.title("Kanban Board")
    
    # Temporary UI component to display the loaded session state for verification
    st.subheader("Current Board State:")
    st.json(st.session_state.tasks_by_status)


# Render the main UI
render_ui()
