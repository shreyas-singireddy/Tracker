from datetime import datetime, timedelta

import streamlit as st

from app.services.analytics import AnalyticsService
from app.services.habit import HabitService
from app.services.recovery import RecoveryService


def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    # Title header
    st.markdown(
        """
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Dashboard</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Your daily fitness, nutrition, and recovery indicators at a glance.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to load the dashboard.")
        return

    # Services
    analytics_service = AnalyticsService()
    habit_service = HabitService()
    recovery_service = RecoveryService()

    # Load active data context
    with st.spinner("Synchronizing fitness metrics..."):
        try:
            # 1. Fetch aggregation data
            agg = analytics_service.get_aggregated_day(user_id, selected_date)

            # 2. Fetch Fitness Score
            try:
                fit_score_obj = analytics_service.compute_fitness_score(user_id, selected_date)
                fitness_score = fit_score_obj.overall_score
            except Exception:
                fitness_score = 0.0

            # 3. Calculate habit streak (find first habit if any to get a representative streak)
            habits = habit_service.get_user_habits(user_id)
            best_streak = 0
            if habits:
                streaks = [habit_service.compute_streak(h.habit_id, user_id) for h in habits]
                best_streak = max(streaks) if streaks else 0

            # 4. Fetch recovery details
            rec_log = recovery_service.get_recovery(user_id, selected_date)
            readiness = rec_log.readiness_state if rec_log else "UNKNOWN"
            rec_val = rec_log.recovery_score if rec_log else 0.0

        except Exception as e:
            st.error(f"Error loading dashboard metrics: {e!s}")
            return

    # Bento Grid Row 1: KPI Cards
    col1, col2, col3 = st.columns(3)

    # Fitness Score Card
    with col1:
        st.markdown(
            f"""
            <div class='glass-card bento-header'>
                <div class='kpi-lbl'>🏆 Daily Fitness Score</div>
                <div class='kpi-val gradient-indigo'>{fitness_score:.1f}</div>
                <div style='font-size: 0.8rem; color: #10B981;'>Deterministic formula (0-100)</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # Recovery Card
    with col2:
        badge_color = "#10B981" if readiness == "FULL" else "#F59E0B" if readiness == "MODERATE" else "#EF4444"
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='kpi-lbl'>🔋 Recovery & Readiness</div>
                <div class='kpi-val'>{rec_val:.0f}%</div>
                <div style='font-size: 0.85rem; font-weight: 600; color: {badge_color};'>{readiness} READINESS</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # Habits Card
    with col3:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='kpi-lbl'>💧 Habits Streak</div>
                <div class='kpi-val'>{best_streak} Days</div>
                <div style='font-size: 0.8rem; color: #94a3b8;'>Best active daily streak</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # Bento Grid Row 2: Secondary indicators
    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='kpi-lbl'>🍎 Calories Consumed</div>
                <div class='kpi-val'>{agg["calories_consumed"]:.0f} kcal</div>
                <div style='font-size: 0.8rem; color: #94a3b8;'>Protein: {agg["protein_g"]:.1f}g</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='kpi-lbl'>🏋️ Workouts Completed</div>
                <div class='kpi-val'>{agg["total_workouts"]} Completed</div>
                <div style='font-size: 0.8rem; color: #94a3b8;'>Burned: {agg["calories_burned"]:.0f} kcal</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with col6:
        comp_rate = agg["habits_completion_rate"]
        st.markdown(
            f"""
            <div class='glass-card'>
                <div class='kpi-lbl'>✅ Habits Completion</div>
                <div class='kpi-val'>{comp_rate:.0f}%</div>
                <div style='font-size: 0.8rem; color: #94a3b8;'>{agg["habits_completed"]}/{agg["habits_total"]} completed today</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # Weekly Trends Chart
    st.subheader("Weekly Trend Analysis")
    try:
        # Load last 7 days of fitness scores
        dates = []
        scores = []
        end_date_dt = datetime.strptime(selected_date, "%Y-%m-%d")
        for i in range(6, -1, -1):
            d = (end_date_dt - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(d)
            try:
                fs = analytics_service.compute_fitness_score(user_id, d)
                scores.append(fs.overall_score)
            except Exception:
                scores.append(0.0)

        import pandas as pd

        df_trend = pd.DataFrame({"Date": dates, "Fitness Score": scores})
        st.line_chart(df_trend, x="Date", y="Fitness Score", color="#5E6AD2")
    except Exception as e:
        st.warning(f"Unable to render weekly trends chart: {e}")
