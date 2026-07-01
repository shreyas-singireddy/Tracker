import sys
from pathlib import Path

# Add project root to path to ensure modules are importable when run directly via Streamlit
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


import streamlit as st

from app.core.config import settings
from app.core.logging import logger
from app.database.connection import db_manager
from app.repositories.user import UserRepository

# Configure premium page layout
st.set_page_config(
    page_title="FitOS // Offline AI Fitness Operating System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load and inject custom CSS stylesheet
css_path = Path(__file__).resolve().parent / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def check_db_health() -> bool:
    """Verifies that the database manager is functioning and responsive."""
    try:
        result = db_manager.execute_read("SELECT 1;")
        return len(result) > 0
    except Exception as e:
        logger.error(f"Database health check failed: {e!s}")
        return False


def init_session_state():
    """Initialise global application state variables."""
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    if "selected_date" not in st.session_state:
        from datetime import date

        st.session_state.selected_date = date.today().strftime("%Y-%m-%d")


from app.core.bootloader import Bootloader


def run_app():
    """Renders the main layout, sidebar navigation, and page router."""
    # Boot system modules & migrations
    try:
        Bootloader.boot()
    except Exception as e:
        st.error(f"System Boot Failure: {e}")
        st.stop()

    init_session_state()

    # Sidebar Header
    st.sidebar.markdown(
        """
        <div style='padding: 10px 0px; text-align: left;'>
            <h1 style='margin: 0; color: #5E6AD2; font-size: 1.8rem;'>⚡ FitOS</h1>
            <p style='margin: 0; color: #94a3b8; font-size: 0.85rem;'>Offline AI Fitness OS</p>
        </div>
    """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    # User Selection & Context
    db_ok = check_db_health()
    user_repo = UserRepository()

    if db_ok:
        try:
            users = user_repo.list_all("users")
        except Exception:
            users = []

        if users:
            user_options = {u["user_id"]: f"{u['name']} ({u['email']})" for u in users}
            selected_uid = st.sidebar.selectbox(
                "👤 Active Profile", options=list(user_options.keys()), format_func=lambda x: user_options[x]
            )
            st.session_state.current_user_id = selected_uid
        else:
            st.sidebar.warning("No active profiles. Register in Settings.")
            st.session_state.current_user_id = None
    else:
        st.sidebar.error("Database connection failed.")
        st.session_state.current_user_id = None

    # Global Date Selector
    from datetime import datetime

    try:
        current_date_obj = datetime.strptime(st.session_state.selected_date, "%Y-%m-%d")
    except Exception:
        from datetime import date

        current_date_obj = date.today()

    new_date = st.sidebar.date_input("📅 Target Date", current_date_obj)
    st.session_state.selected_date = new_date.strftime("%Y-%m-%d")

    st.sidebar.divider()

    # Dynamic Page Imports (Deferred to avoid circular dependencies/performance issues)
    from app.ui.pages import (
        ai_coach,
        analytics,
        dashboard,
        habits,
        nutrition,
        recovery,
        reports,
        workout,
    )
    from app.ui.pages import (
        settings as settings_page,
    )

    pages = {
        "📊 Dashboard Overview": dashboard.render,
        "🏋️ Workouts & Training": workout.render,
        "🍎 Nutrition & Meals": nutrition.render,
        "💧 Habit Tracking": habits.render,
        "🔋 Recovery & Sleep": recovery.render,
        "🤖 AI Coach Chat": ai_coach.render,
        "📈 Progress Analytics": analytics.render,
        "📋 Weekly/Monthly Reports": reports.render,
        "⚙️ Settings & Profiles": settings_page.render,
    }

    # Sidebar Navigation Menu
    selection = st.sidebar.radio("Navigation", list(pages.keys()))
    st.sidebar.divider()

    # System Status Panel (Strict health audits)
    st.sidebar.markdown(
        "<p style='font-size: 0.8rem; font-weight: 600; color: #94a3b8; margin-bottom: 8px;'>SYSTEM HEALTH</p>",
        unsafe_allow_html=True,
    )
    if settings.OFFLINE_MODE:
        st.sidebar.markdown(
            "<span style='color: #10B981; font-size: 0.85rem;'>🔒 Offline Mode: Enforced</span>", unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            "<span style='color: #EF4444; font-size: 0.85rem;'>⚠️ Offline Mode: Compromised</span>",
            unsafe_allow_html=True,
        )

    if db_ok:
        st.sidebar.markdown(
            "<span style='color: #10B981; font-size: 0.85rem;'>💾 Database: Connected</span>", unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            "<span style='color: #EF4444; font-size: 0.85rem;'>❌ Database: Disconnected</span>", unsafe_allow_html=True
        )

    st.sidebar.caption(f"v1.0.0 // Environment: {settings.ENV}")

    # Main content rendering container
    main_container = st.container()
    with main_container:
        render_func = pages[selection]
        try:
            render_func()
        except Exception as e:
            st.error(f"Failed to load page '{selection}': {e!s}")
            logger.exception(f"Error rendering page {selection}")


if __name__ == "__main__":
    run_app()
