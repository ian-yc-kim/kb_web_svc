"""JSON Import/Export UI component for task management.

This module provides a Streamlit UI for importing and exporting tasks in JSON format,
including conflict resolution strategies, automatic backup, and rollback capabilities.
"""

import json
import logging
from datetime import datetime
from io import StringIO
from typing import Dict, Any, List

import streamlit as st
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..schemas.import_export_schemas import TaskImportData
from ..services.json_import_export_service import (
    export_all_tasks_to_json,
    import_tasks_logic,
    restore_database_from_json_backup
)
from ..state_management import load_tasks_from_db_to_session

logger = logging.getLogger(__name__)


def render_json_import_export_ui(db: Session) -> None:
    """Render the JSON import/export UI component.
    
    This function creates a comprehensive UI for task import/export operations including:
    - Export section: Button to download all tasks as JSON
    - Import section: File uploader with validation and conflict resolution
    - Automatic database backup before import
    - Rollback capability on import failure
    - Progress indication and detailed result summaries
    
    Args:
        db: SQLAlchemy database session for backend operations
    """
    logger.info("Rendering JSON import/export UI")
    
    try:
        if db is None:
            st.error("Database connection is not available. Please refresh the page and try again.")
            return
        
        # Export Section
        st.subheader("Export Tasks")
        st.write("Download all current tasks as a JSON file for backup or sharing.")
        
        if st.button(
            "Export All Tasks to JSON",
            help="Click to export all current tasks to a downloadable JSON file for backup or sharing purposes.",
            key="export_tasks_button"
        ):
            _handle_export_tasks(db)
        
        st.markdown("---")
        
        # Import Section
        st.subheader("Import Tasks")
        st.write("Upload a JSON file to import tasks. Choose how to handle conflicts with existing tasks.")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload JSON file for Import",
            type=["json"],
            help="Select a JSON file containing task data to import. The file must contain a valid list of task objects.",
            key="import_file_uploader"
        )
        
        if uploaded_file is not None:
            _handle_import_section(db, uploaded_file)
        
        logger.info("JSON import/export UI rendered successfully")
        
    except Exception as e:
        logger.error(f"Error rendering JSON import/export UI: {e}", exc_info=True)
        st.error("An error occurred while loading the import/export interface. Please refresh the page.")


def _handle_export_tasks(db: Session) -> None:
    """Handle the export tasks operation.
    
    Args:
        db: SQLAlchemy database session
    """
    logger.info("Handling export tasks operation")
    
    try:
        with st.spinner("Exporting tasks..."):
            # Call the export service
            json_data = export_all_tasks_to_json(db)
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kanban_tasks_export_{timestamp}.json"
            
            # Parse JSON to count tasks for user feedback
            try:
                parsed_data = json.loads(json_data)
                task_count = len(parsed_data)
            except json.JSONDecodeError:
                task_count = 0
            
            st.success(f"✅ Successfully exported {task_count} tasks!")
            
            # Provide download button
            st.download_button(
                label="Download JSON File",
                data=json_data,
                file_name=filename,
                mime="application/json",
                help=f"Click to download the exported tasks as {filename}",
                key="download_exported_json"
            )
            
        logger.info(f"Export completed successfully: {task_count} tasks exported")
        
    except Exception as e:
        logger.error(f"Error during export: {e}", exc_info=True)
        st.error("❌ Failed to export tasks. Please try again or contact support if the problem persists.")


def _handle_import_section(db: Session, uploaded_file) -> None:
    """Handle the import section UI and operations.
    
    Args:
        db: SQLAlchemy database session
        uploaded_file: Streamlit UploadedFile object
    """
    logger.info("Handling import section")
    
    try:
        # Read and parse the uploaded file
        file_content = _read_uploaded_file(uploaded_file)
        if file_content is None:
            return
        
        # Validate JSON content
        tasks_data = _validate_json_content(file_content)
        if tasks_data is None:
            return
        
        st.success(f"✅ File uploaded successfully! Found {len(tasks_data)} tasks to import.")
        
        # Conflict resolution strategy selection
        conflict_strategy = _render_conflict_strategy_selection()
        
        # Import button
        if st.button(
            "Import Tasks", 
            type="primary",
            help="Click to import the uploaded tasks using the selected conflict resolution strategy.",
            key="import_tasks_button"
        ):
            _handle_import_execution(db, tasks_data, conflict_strategy)
        
    except Exception as e:
        logger.error(f"Error in import section: {e}", exc_info=True)
        st.error("❌ An error occurred while processing the import. Please try again or contact support if the problem persists.")


def _read_uploaded_file(uploaded_file) -> str | None:
    """Read content from uploaded file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        File content as string, or None if reading failed
    """
    try:
        # Read file content
        if hasattr(uploaded_file, 'getvalue'):
            # UploadedFile object
            file_bytes = uploaded_file.getvalue()
            if isinstance(file_bytes, bytes):
                file_content = file_bytes.decode('utf-8')
            else:
                file_content = str(file_bytes)
        else:
            # StringIO or similar
            file_content = uploaded_file.read()
        
        return file_content
        
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}", exc_info=True)
        st.error("❌ Failed to read the uploaded file. Please ensure it's a valid text file and try again.")
        return None


def _validate_json_content(file_content: str) -> List[TaskImportData] | None:
    """Validate JSON content and parse into TaskImportData objects.
    
    Args:
        file_content: Raw file content as string
        
    Returns:
        List of TaskImportData objects, or None if validation failed
    """
    try:
        # Parse JSON
        try:
            json_data = json.loads(file_content)
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON format: {str(e)}")
            return None
        
        # Check if it's a list
        if not isinstance(json_data, list):
            st.error("❌ JSON file must contain a list of task objects.")
            return None
        
        if len(json_data) == 0:
            st.warning("⚠️ The JSON file contains no tasks to import.")
            return []
        
        # Validate each task object
        tasks_data = []
        errors = []
        
        for i, task_data in enumerate(json_data):
            try:
                task_import = TaskImportData.model_validate(task_data)
                tasks_data.append(task_import)
            except ValidationError as e:
                error_msg = f"Task {i + 1}: {str(e)}"
                errors.append(error_msg)
                # Limit error display to first 5 errors
                if len(errors) >= 5:
                    break
        
        # Display validation errors if any
        if errors:
            st.error("❌ **Validation Errors Found:**")
            for error in errors:
                st.error(f"• {error}")
            
            if len(errors) >= 5 and len(json_data) > 5:
                st.error(f"• ... and possibly more errors in remaining {len(json_data) - 5} tasks")
            
            st.error("Please fix the errors in your JSON file and try again.")
            return None
        
        return tasks_data
        
    except Exception as e:
        logger.error(f"Error validating JSON content: {e}", exc_info=True)
        st.error("❌ An error occurred while validating the JSON file. Please check the file format and try again.")
        return None


def _render_conflict_strategy_selection() -> str:
    """Render conflict resolution strategy selection UI.
    
    Returns:
        Selected conflict strategy for the service layer
    """
    # User-friendly options mapped to service values
    strategy_options = {
        "Skip duplicates (keep existing tasks unchanged)": "skip",
        "Replace existing with imported data": "replace",
        "Merge (update if imported is newer)": "merge_with_timestamp"
    }
    
    # Get current selection from session state
    current_selection = st.session_state.get("import_conflict_strategy", list(strategy_options.keys())[0])
    
    # Render selection UI
    selected_option = st.radio(
        "**How should conflicts with existing tasks be handled?**",
        options=list(strategy_options.keys()),
        index=list(strategy_options.keys()).index(current_selection) if current_selection in strategy_options else 0,
        help="Choose how to handle tasks that already exist in your database. Skip keeps existing data unchanged, Replace overwrites with imported data, Merge updates only if the imported task is newer.",
        key="conflict_strategy_radio"
    )
    
    # Store selection in session state
    st.session_state.import_conflict_strategy = selected_option
    
    # Return the service value
    return strategy_options[selected_option]


def _handle_import_execution(db: Session, tasks_data: List[TaskImportData], conflict_strategy: str) -> None:
    """Execute the import operation with backup and rollback capabilities.
    
    Args:
        db: SQLAlchemy database session
        tasks_data: List of validated TaskImportData objects
        conflict_strategy: Conflict resolution strategy
    """
    logger.info(f"Executing import with strategy '{conflict_strategy}' for {len(tasks_data)} tasks")
    
    try:
        # Step 1: Create backup before import
        with st.spinner("Creating database backup..."):
            try:
                backup_json = export_all_tasks_to_json(db)
                st.session_state.db_backup_json = backup_json
                logger.info("Database backup created successfully")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}", exc_info=True)
                st.error("❌ Failed to create database backup. Import cancelled for safety.")
                return
        
        # Step 2: Perform import
        with st.spinner("Importing tasks..."):
            try:
                import_result = import_tasks_logic(db, tasks_data, conflict_strategy)
                
                # Step 3: Handle successful import
                _handle_successful_import(db, import_result)
                
            except Exception as import_error:
                logger.error(f"Import failed: {import_error}", exc_info=True)
                
                # Step 4: Handle failed import with rollback
                _handle_failed_import(db, import_error)
        
    except Exception as e:
        logger.error(f"Critical error during import execution: {e}", exc_info=True)
        st.error("❌ A critical error occurred during import. Please try again or contact support if the problem persists.")
        
        # Refresh UI regardless of outcome
        try:
            load_tasks_from_db_to_session(db)
        except Exception as refresh_error:
            logger.error(f"Failed to refresh UI after error: {refresh_error}", exc_info=True)


def _handle_successful_import(db: Session, import_result: Dict[str, Any]) -> None:
    """Handle successful import by displaying results and refreshing UI.
    
    Args:
        db: SQLAlchemy database session
        import_result: Import operation results dictionary
    """
    logger.info(f"Import completed successfully: {import_result}")
    
    # Display success message
    st.success("🎉 **Import Complete!**")
    
    # Display detailed summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Imported", import_result.get("imported", 0), delta="new tasks")
    
    with col2:
        st.metric("Updated", import_result.get("updated", 0), delta="existing tasks")
    
    with col3:
        st.metric("Skipped", import_result.get("skipped", 0), delta="duplicates")
    
    with col4:
        st.metric("Failed", import_result.get("failed", 0), delta="errors")
    
    # Additional details in expandable section
    with st.expander("📊 Import Summary Details"):
        st.write("**Import Results:**")
        st.json(import_result)
        
        total_processed = sum([
            import_result.get("imported", 0),
            import_result.get("updated", 0),
            import_result.get("skipped", 0),
            import_result.get("failed", 0)
        ])
        st.write(f"**Total tasks processed:** {total_processed}")
    
    # Refresh the main kanban board
    try:
        load_tasks_from_db_to_session(db)
        logger.info("Kanban board refreshed after successful import")
    except Exception as e:
        logger.error(f"Failed to refresh kanban board: {e}", exc_info=True)
        st.warning("⚠️ Import was successful, but the kanban board may need a manual refresh.")


def _handle_failed_import(db: Session, import_error: Exception) -> None:
    """Handle failed import by attempting rollback and displaying error.
    
    Args:
        db: SQLAlchemy database session
        import_error: The exception that caused the import to fail
    """
    logger.info("Handling failed import with rollback attempt")
    
    # Display initial error message
    st.error("❌ **Import failed! Attempting rollback...**")
    
    # Attempt rollback if backup exists
    if hasattr(st.session_state, 'db_backup_json') and st.session_state.db_backup_json:
        try:
            with st.spinner("Rolling back database..."):
                restore_database_from_json_backup(db, st.session_state.db_backup_json)
            
            logger.info("Database rollback completed successfully")
            st.error("❌ **Import failed and rolled back successfully.**")
            st.info("💡 Your database has been restored to its previous state.")
            
        except Exception as rollback_error:
            logger.error(f"Rollback also failed: {rollback_error}", exc_info=True)
            st.error("❌ **Import failed. Rollback also failed! Manual intervention may be required.**")
            st.error(f"**Original error:** {str(import_error)}")
            st.error(f"**Rollback error:** {str(rollback_error)}")
    else:
        logger.warning("No backup available for rollback")
        st.error("❌ **Import failed and no backup is available for rollback.**")
        st.error(f"**Error:** {str(import_error)}")
    
    # Always try to refresh UI to show current database state
    try:
        load_tasks_from_db_to_session(db)
        logger.info("Kanban board refreshed after failed import")
    except Exception as refresh_error:
        logger.error(f"Failed to refresh kanban board after rollback: {refresh_error}", exc_info=True)
        st.warning("⚠️ Unable to refresh the kanban board. Please refresh the page manually.")
