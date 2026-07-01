import uuid
from datetime import datetime, timedelta

import streamlit as st

from app.services.recovery import RecoveryService


def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown(
        """
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Recovery & Sleep</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Log daily sleep, configure baseline metrics, and view computed physical readiness metrics.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to load recovery logs.")
        return

    recovery_service = RecoveryService()

    tab_today, tab_trends = st.tabs(["🔋 Readiness & Sleep", "📈 Recovery Trends"])

    # --- TAB 1: Daily Readiness & Sleep ---
    with tab_today:
        col_stats, col_form = st.columns([2, 1])

        with col_stats:
            st.subheader("Daily Status Overview")

            # Fetch recovery
            rec_log = recovery_service.get_recovery(user_id, selected_date)
            # Fetch sleep log
            sleep_log = recovery_service.sleep_repo.get_sleep_log_by_date(user_id, selected_date)

            if rec_log:
                readiness = rec_log.readiness_state
                badge_color = "#10B981" if readiness == "FULL" else "#F59E0B" if readiness == "MODERATE" else "#EF4444"

                st.markdown(
                    f"""
                    <div class='glass-card bento-header'>
                        <div class='kpi-lbl'>Overall Readiness State</div>
                        <div class='kpi-val' style='color: {badge_color};'>{readiness}</div>
                        <div class='kpi-lbl'>Readiness Score: {rec_log.recovery_score:.1f}%</div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                # Show breakdown components
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h4 style='margin:0 0 10px 0; color:#E2E8F0;'>Recovery Components Breakdown</h4>
                        <div style='display:flex; flex-direction:column; gap:8px;'>
                            <div style='display:flex; justify-content:space-between;'>
                                <span style='color:#94a3b8;'>Sleep Quality Component (40%):</span>
                                <span style='font-weight:600; color:#F1F5F9;'>{rec_log.sleep_quality_component:.1f}%</span>
                            </div>
                            <div style='display:flex; justify-content:space-between;'>
                                <span style='color:#94a3b8;'>Sleep Duration Component (30%):</span>
                                <span style='font-weight:600; color:#F1F5F9;'>{rec_log.sleep_duration_component:.1f}%</span>
                            </div>
                            <div style='display:flex; justify-content:space-between;'>
                                <span style='color:#94a3b8;'>Workout Load Component (20%):</span>
                                <span style='font-weight:600; color:#F1F5F9;'>{rec_log.workout_load_component:.1f}%</span>
                            </div>
                            <div style='display:flex; justify-content:space-between;'>
                                <span style='color:#94a3b8;'>Rest Days Component (10%):</span>
                                <span style='font-weight:600; color:#F1F5F9;'>{rec_log.rest_days_component:.1f}%</span>
                            </div>
                        </div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.info(
                    "No recovery readiness score has been computed for this date yet. Log sleep on the right to calculate."
                )

            if sleep_log:
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h4 style='margin:0; color:#818CF8;'>Sleep Details</h4>
                        <p style='margin:4px 0 0 0; color:#E2E8F0;'>
                            Duration: <b>{sleep_log.hours:.1f} hours</b> | Quality: <b>{sleep_log.quality_score:.1f}/10</b>
                        </p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No sleep data logged for today.")

        with col_form:
            st.subheader("Log Daily Sleep")
            with st.form(key="sleep_log_form"):
                sleep_hours = st.number_input("Hours Slept", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
                sleep_quality = st.slider("Sleep Quality Score", min_value=1.0, max_value=10.0, value=7.0, step=0.5)

                submit_sleep = st.form_submit_button("Log Sleep & Calculate Recovery", use_container_width=True)
                if submit_sleep:
                    try:
                        sleep_id = f"slp-{uuid.uuid4().hex[:8]}"
                        # Delete existing sleep log if any to prevent duplicate errors
                        existing_slp = recovery_service.sleep_repo.get_sleep_log_by_date(user_id, selected_date)
                        if existing_slp:
                            recovery_service.sleep_repo.delete("sleep_logs", "sleep_log_id", existing_slp.sleep_log_id)

                        # Log and calculate
                        recovery_service.log_sleep(sleep_id, user_id, selected_date, sleep_hours, sleep_quality)
                        recovery_service.calculate_recovery(user_id, selected_date)

                        st.success("Sleep logged and recovery updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to log sleep: {e}")

            # Configure profile baseline sleep target
            st.divider()
            st.subheader("Target baseline setting")
            try:
                profile = recovery_service.get_or_create_profile(user_id)
                current_baseline = profile.baseline_sleep_hours
            except Exception:
                current_baseline = 8.0

            with st.form(key="baseline_form"):
                baseline_h = st.number_input(
                    "Sleep Goal Target (hours)", min_value=4.0, max_value=12.0, value=current_baseline, step=0.5
                )
                baseline_submit = st.form_submit_button("Update Baseline Goal")
                if baseline_submit:
                    try:
                        recovery_service.update_baseline_sleep(user_id, baseline_h)
                        st.success("Baseline sleep target updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update: {e}")

    # --- TAB 2: Trends ---
    with tab_trends:
        st.subheader("Sleep & Recovery History Trends")
        try:
            # Load last 14 days of recovery scores
            dates = []
            recovery_history = []
            sleep_history = []
            end_date_dt = datetime.strptime(selected_date, "%Y-%m-%d")
            for i in range(13, -1, -1):
                d = (end_date_dt - timedelta(days=i)).strftime("%Y-%m-%d")
                dates.append(d)

                # recovery
                rec = recovery_service.get_recovery(user_id, d)
                recovery_history.append(rec.recovery_score if rec else 0.0)

                # sleep
                slp = recovery_service.sleep_repo.get_sleep_log_by_date(user_id, d)
                sleep_history.append(slp.hours if slp else 0.0)

            import pandas as pd

            df_history = pd.DataFrame(
                {"Date": dates, "Recovery Score (%)": recovery_history, "Sleep Duration (hrs)": sleep_history}
            )

            st.markdown("**Recovery Score Over Time (%)**")
            st.line_chart(df_history, x="Date", y="Recovery Score (%)", color="#5E6AD2")

            st.markdown("**Sleep Duration Over Time (hrs)**")
            st.bar_chart(df_history, x="Date", y="Sleep Duration (hrs)", color="#818CF8")
        except Exception as e:
            st.warning(f"Unable to load recovery history charts: {e}")
