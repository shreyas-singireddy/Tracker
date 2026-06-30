import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
from app.services.analytics import AnalyticsService

def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Weekly & Monthly Reports</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Compile, read, and export comprehensive performance summaries of your fitness journey.</p>
        </div>
    """, unsafe_allow_html=True)

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to generate reports.")
        return

    analytics_service = AnalyticsService()

    tab_weekly, tab_monthly = st.tabs(["📋 Weekly Reports", "📅 Monthly Reports"])

    # --- TAB 1: Weekly Reports ---
    with tab_weekly:
        st.subheader("Generate Weekly Report")
        
        # Calculate current week's Monday
        selected_dt = datetime.strptime(selected_date, "%Y-%m-%d")
        monday_dt = selected_dt - timedelta(days=selected_dt.weekday())
        monday_str = monday_dt.strftime("%Y-%m-%d")
        
        week_start_input = st.text_input("Week Start Date (Monday - YYYY-MM-DD)", value=monday_str)
        
        if st.button("Compile Weekly Report", use_container_width=True):
            try:
                with st.spinner("Analyzing weekly logs..."):
                    report = analytics_service.generate_weekly_report(user_id, week_start_input)
                
                st.success("Weekly report generated successfully!")
                
                # Render Report Dashboard Card
                st.markdown(f"""
                    <div class='glass-card bento-header'>
                        <h3 style='margin:0; color:#5E6AD2;'>Weekly Report: {report.week_start} to {report.week_end}</h3>
                        <p style='margin:0; font-size:0.95rem; color:#A5B4FC;'>Average Daily Fitness Score: <b>{report.avg_fitness_score:.1f}/100</b></p>
                    </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Total Workouts</div>
                            <div class='kpi-val'>{report.total_workouts}</div>
                            <div class='kpi-lbl'>Adherence Rate: {report.adherence_rate:.1f}%</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Avg Daily Nutrition</div>
                            <div class='kpi-val'>{report.avg_calories:.0f} kcal</div>
                            <div class='kpi-lbl'>Protein: {report.avg_protein_g:.1f}g</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Avg Recovery Score</div>
                            <div class='kpi-val'>{report.avg_recovery_score:.0f}%</div>
                            <div class='kpi-lbl'>Best Habit Streak: {report.habit_streaks_best} Days</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Insights Section
                st.markdown(f"""
                    <div class='glass-card'>
                        <h4 style='margin:0 0 8px 0; color:#E2E8F0;'>💡 Automated Weekly Insights</h4>
                        <p style='margin:0; color:#94a3b8; font-size:0.9rem;'>{report.insight_summary}</p>
                    </div>
                """, unsafe_allow_html=True)

                # Download Options
                report_dict = report.to_dict()
                report_json = json.dumps(report_dict, indent=2)
                st.download_button(
                    label="📥 Export Report to JSON",
                    data=report_json,
                    file_name=f"weekly_report_{report.week_start}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Failed to compile weekly report: {e}")

    # --- TAB 2: Monthly Reports ---
    with tab_monthly:
        st.subheader("Generate Monthly Report")
        
        # Calculate current month's 1st day
        selected_dt = datetime.strptime(selected_date, "%Y-%m-%d")
        first_day_str = selected_dt.replace(day=1).strftime("%Y-%m-%d")
        
        month_start_input = st.text_input("Month Start Date (1st of month - YYYY-MM-DD)", value=first_day_str)
        
        if st.button("Compile Monthly Report", use_container_width=True):
            try:
                with st.spinner("Analyzing monthly logs..."):
                    report = analytics_service.generate_monthly_report(user_id, month_start_input)
                
                st.success("Monthly report generated successfully!")

                # Render Report Dashboard Card
                st.markdown(f"""
                    <div class='glass-card bento-header'>
                        <h3 style='margin:0; color:#5E6AD2;'>Monthly Report: {report.month_start} to {report.month_end}</h3>
                        <p style='margin:0; font-size:0.95rem; color:#A5B4FC;'>Average Daily Fitness Score: <b>{report.avg_fitness_score:.1f}/100</b></p>
                    </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Total Workouts</div>
                            <div class='kpi-val'>{report.total_workouts}</div>
                            <div class='kpi-lbl'>Adherence Rate: {report.adherence_rate:.1f}%</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Avg Daily Nutrition</div>
                            <div class='kpi-val'>{report.avg_calories:.0f} kcal</div>
                            <div class='kpi-lbl'>Protein: {report.avg_protein_g:.1f}g</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                        <div class='glass-card'>
                            <div class='kpi-lbl'>Avg Recovery Score</div>
                            <div class='kpi-val'>{report.avg_recovery_score:.0f}%</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Summaries Section
                st.markdown(f"""
                    <div class='glass-card'>
                        <h4 style='margin:0 0 8px 0; color:#E2E8F0;'>📊 Monthly Progress Summaries</h4>
                        <div style='display:flex; flex-direction:column; gap:12px; font-size:0.9rem; color:#94a3b8;'>
                            <div><b>Strength Improvements:</b> {report.strength_improvements or 'No workouts recorded.'}</div>
                            <div><b>Body Changes Summary:</b> {report.body_changes_summary or 'No changes recorded.'}</div>
                            <div><b>General Progress:</b> {report.progress_summary or 'No logs recorded.'}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Download Options
                report_dict = report.to_dict()
                report_json = json.dumps(report_dict, indent=2)
                st.download_button(
                    label="📥 Export Report to JSON",
                    data=report_json,
                    file_name=f"monthly_report_{report.month_start}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Failed to compile monthly report: {e}")
