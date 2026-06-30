import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.services.analytics import AnalyticsService

def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Progress Analytics</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Computed metrics, trend charts, and fitness score breakdowns.</p>
        </div>
    """, unsafe_allow_html=True)

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to load progress analytics.")
        return

    analytics_service = AnalyticsService()

    with st.spinner("Compiling biometric trends..."):
        try:
            # 1. Fetch current fitness score breakdown
            score_log = analytics_service.compute_fitness_score(user_id, selected_date)
        except Exception as e:
            st.warning(f"Unable to compute Fitness Score for today: {e}")
            score_log = None

    if score_log:
        st.subheader("Daily Fitness Score Breakdown")
        
        # Display breakdown progress bars
        st.markdown(f"""
            <div class='glass-card bento-header'>
                <div class='kpi-lbl'>Overall Computed Score</div>
                <div class='kpi-val gradient-indigo'>{score_log.overall_score:.1f} / 100</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Score Component Breakdown")
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.metric("Nutrition Score (25%)", f"{score_log.nutrition_score:.1f}%")
            st.progress(score_log.nutrition_score / 100.0)
            
            st.metric("Workout Consistency (20%)", f"{score_log.workout_consistency_score:.1f}%")
            st.progress(score_log.workout_consistency_score / 100.0)
            
            st.metric("Progressive Overload (15%)", f"{score_log.progressive_overload_score:.1f}%")
            st.progress(score_log.progressive_overload_score / 100.0)

        with col_right:
            st.metric("Recovery Component (15%)", f"{score_log.recovery_score:.1f}%")
            st.progress(score_log.recovery_score / 100.0)
            
            st.metric("Habits Completion (10%)", f"{score_log.habits_score:.1f}%")
            st.progress(score_log.habits_score / 100.0)
            
            st.metric("Body Progress Score (10%)", f"{score_log.body_progress_score:.1f}%")
            st.progress(score_log.body_progress_score / 100.0)

    # Historical metrics trend
    st.divider()
    st.subheader("14-Day Multi-Metric Trends")
    try:
        dates = []
        scores = []
        cals = []
        sleep = []
        
        end_date_dt = datetime.strptime(selected_date, "%Y-%m-%d")
        for i in range(13, -1, -1):
            d = (end_date_dt - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(d)
            
            # score
            try:
                fs = analytics_service.compute_fitness_score(user_id, d)
                scores.append(fs.overall_score)
            except Exception:
                scores.append(0.0)

            # cals/sleep
            agg = analytics_service.get_aggregated_day(user_id, d)
            cals.append(agg.get("calories_consumed", 0.0))
            sleep.append(agg.get("sleep_hours") or 0.0)

        df_trends = pd.DataFrame({
            "Date": dates,
            "Fitness Score": scores,
            "Calories (kcal)": cals,
            "Sleep (hrs)": sleep
        })

        # Render charts
        st.markdown("**Fitness Score Trend**")
        st.line_chart(df_trends, x="Date", y="Fitness Score", color="#5E6AD2")
        
        st.markdown("**Calories Consumed vs Sleep Duration**")
        st.line_chart(df_trends, x="Date", y=["Calories (kcal)", "Sleep (hrs)"])
    except Exception as e:
        st.warning(f"Could not load trends visualization: {e}")
