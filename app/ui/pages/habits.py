import uuid

import streamlit as st

from app.models.habit_recovery import Habit
from app.services.habit import HabitService


def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown(
        """
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Habits Tracking</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Track routines, streaks, and measure overall habit consistency.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to load habit logs.")
        return

    habit_service = HabitService()
    habits = habit_service.get_user_habits(user_id)

    tab_checklist, tab_manage = st.tabs(["📝 Daily Checklist", "⚙️ Manage Habits"])

    # --- TAB 1: Daily Checklist ---
    with tab_checklist:
        st.subheader(f"Checklist for {selected_date}")

        if habits:
            for h in habits:
                # Find log for this date if exists
                logs = habit_service.get_habit_logs(h.habit_id)
                current_log = None
                for l in logs:
                    if l.log_date == selected_date and l.user_id == user_id:
                        current_log = l
                        break

                status = current_log.status if current_log else "Not Logged"

                # Render Habit Card
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h4 style='margin:0; color:#5E6AD2;'>{h.name}</h4>
                        <p style='margin:0; font-size:0.85rem; color:#94a3b8;'>{h.description or "No description"}</p>
                        <p style='margin:4px 0 0 0; font-size:0.85rem; color:#A5B4FC;'>
                            Target: {h.target_value:.1f} {h.unit} | Status: <b>{status.upper()}</b>
                        </p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                # Log actions
                col_c, col_m, col_p = st.columns(3)

                if col_c.button("✓ Completed", key=f"comp_{h.habit_id}"):
                    try:
                        log_id = f"hl-{uuid.uuid4().hex[:8]}"
                        # Delete existing if any to prevent duplicate constraint
                        if current_log:
                            habit_service.habit_log_repo.delete_habit_log(current_log.habit_log_id)
                        habit_service.log_habit(log_id, h.habit_id, user_id, selected_date, h.target_value, "completed")
                        st.success(f"Logged '{h.name}' as completed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to log: {e}")

                if col_m.button("✗ Missed", key=f"miss_{h.habit_id}"):
                    try:
                        log_id = f"hl-{uuid.uuid4().hex[:8]}"
                        if current_log:
                            habit_service.habit_log_repo.delete_habit_log(current_log.habit_log_id)
                        habit_service.log_habit(log_id, h.habit_id, user_id, selected_date, 0.0, "missed")
                        st.success(f"Logged '{h.name}' as missed.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to log: {e}")

                if col_p.button("◂ Partial", key=f"part_{h.habit_id}"):
                    try:
                        log_id = f"hl-{uuid.uuid4().hex[:8]}"
                        if current_log:
                            habit_service.habit_log_repo.delete_habit_log(current_log.habit_log_id)
                        habit_service.log_habit(
                            log_id, h.habit_id, user_id, selected_date, h.target_value / 2, "partial"
                        )
                        st.success(f"Logged '{h.name}' as partial progress.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to log: {e}")
                st.divider()
        else:
            st.info("You haven't configured any habits. Go to 'Manage Habits' tab to register one.")

    # --- TAB 2: Manage Habits ---
    with tab_manage:
        st.subheader("Your Habits & Streaks Dashboard")
        if habits:
            for h in habits:
                streak = habit_service.compute_streak(h.habit_id, user_id)
                consistency = habit_service.compute_consistency_score(h.habit_id, user_id, days=30)

                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h4 style='margin:0; color:#818CF8;'>{h.name}</h4>
                        <div style='display:flex; gap:30px; margin-top:8px;'>
                            <div>
                                <span style='font-size:0.8rem; color:#94a3b8;'>STREAK</span><br>
                                <span style='font-weight:600; color:#E2E8F0;'>{streak} Days</span>
                            </div>
                            <div>
                                <span style='font-size:0.8rem; color:#94a3b8;'>30-DAY CONSISTENCY</span><br>
                                <span style='font-weight:600; color:#E2E8F0;'>{consistency:.1f}%</span>
                            </div>
                        </div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                # Delete habit button
                if st.button("Delete Habit", key=f"del_h_{h.habit_id}"):
                    try:
                        habit_service.delete_habit(h.habit_id)
                        st.success("Habit deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")
        else:
            st.info("No configured habits found.")

        st.divider()
        st.subheader("Configure a New Habit")
        with st.form(key="add_habit_form"):
            h_name = st.text_input("Name (e.g. Daily Water Intake)")
            h_desc = st.text_input("Description (e.g. Drink 8 cups of water)")
            h_freq = st.selectbox("Frequency", ["daily", "weekly"])
            h_target = st.number_input("Target Value", min_value=0.1, value=1.0)
            h_unit = st.text_input("Unit (e.g. cups, minutes, times)", value="times")

            h_submit = st.form_submit_button("Register Habit")
            if h_submit:
                try:
                    new_habit = Habit(
                        habit_id=f"h-{uuid.uuid4().hex[:8]}",
                        user_id=user_id,
                        name=h_name,
                        description=h_desc,
                        frequency=h_freq,
                        target_value=h_target,
                        unit=h_unit,
                    )
                    habit_service.create_habit(new_habit)
                    st.success(f"Habit '{h_name}' registered successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to register: {e}")
