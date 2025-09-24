import streamlit as st
import logging

# Import database functionality
from .database import check_db_connection

# Global configuration (if needed)
st.set_page_config(page_title="kb_web_svc App", layout="wide")

# Set up logging
logger = logging.getLogger(__name__)


def render_ui() -> None:
    """Render the main UI with database connection test functionality.
    
    This function creates a button that allows users to test database connectivity.
    When clicked, it calls check_db_connection() and displays the result.
    """
    st.title("Database Connection Test")
    
    if st.button("Test Database Connection"):
        logger.info("Testing database connection...")
        
        try:
            result = check_db_connection()
            
            if result:
                st.success("Database connection successful!")
                logger.info("Database connection test: SUCCESS")
            else:
                st.error("Database connection failed!")
                logger.info("Database connection test: FAILED")
                
        except Exception as e:
            st.error("Database connection failed!")
            # Log the raw exception object as expected by tests
            logging.error(e, exc_info=True)


def render_db_connection_check() -> None:
    """Render the database connection check UI component.
    
    This function creates a button that allows users to test database connectivity.
    When clicked, it calls check_db_connection() and displays the result.
    
    This function is kept for backward compatibility but delegates to render_ui.
    """
    render_ui()


# Render the main UI
render_ui()
