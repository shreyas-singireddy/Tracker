import streamlit as st
import uuid
from datetime import datetime
from app.services.workout import WorkoutService
from app.services.exercise import ExerciseService
from app.repositories.workout import WorkoutSessionRepository
from app.models.domain import Exercise
from app.models.workout import WorkoutPlan, WorkoutSession

def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Workouts & Exercise Tracking</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Log, track, and manage your workout sessions and progressive overload stats.</p>
        </div>
    """, unsafe_allow_html=True)

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to track workouts.")
        return

    workout_service = WorkoutService()
    exercise_service = ExerciseService()
    session_repo = WorkoutSessionRepository()

    # Get active session if any
    active_session = session_repo.get_active_session(user_id)

    # Tabs for navigation
    tab_active, tab_history, tab_catalog = st.tabs(["🏋️ Active Session", "📊 Session History", "📚 Exercise Catalog"])

    # --- TAB 1: Active Session ---
    with tab_active:
        if active_session:
            st.markdown("""
                <div class='glass-card bento-header'>
                    <h3 style='margin:0; color:#5E6AD2;'>⚡ Workout Session in Progress</h3>
                    <p style='margin:0; font-size:0.85rem; color:#94a3b8;'>Status: ACTIVE</p>
                </div>
            """, unsafe_allow_html=True)

            # Show active exercises logged in session
            session_id = active_session.session_id
            exercise_logs = workout_service.log_repo.get_session_logs(session_id)

            if exercise_logs:
                st.subheader("Logged Exercises")
                for elog in exercise_logs:
                    ex = exercise_service.get_exercise(elog.exercise_id)
                    ex_name = ex.name if ex else "Unknown Exercise"
                    
                    with st.expander(f"💪 {ex_name}", expanded=True):
                        # Fetch sets
                        sets = workout_service.set_repo.get_log_sets(elog.exercise_log_id)
                        if sets:
                            for s in sorted(sets, key=lambda x: x.set_number):
                                st.write(f"Set {s.set_number}: **{s.weight:.1f} kg** × **{s.reps} reps** (RPE: {s.rpe or 'N/A'})")
                        else:
                            st.caption("No sets logged for this exercise.")

                        # Add set form
                        with st.form(key=f"set_form_{elog.exercise_log_id}"):
                            col_w, col_r, col_rp = st.columns(3)
                            weight = col_w.number_input("Weight (kg)", min_value=0.0, step=2.5, key=f"w_{elog.exercise_log_id}")
                            reps = col_r.number_input("Reps", min_value=1, step=1, key=f"r_{elog.exercise_log_id}")
                            rpe = col_rp.slider("RPE (Intensity)", min_value=1.0, max_value=10.0, value=8.0, step=0.5, key=f"rp_{elog.exercise_log_id}")
                            submit_set = st.form_submit_button("Log Set")
                            if submit_set:
                                try:
                                    set_id = f"set-{uuid.uuid4().hex[:8]}"
                                    set_num = len(sets) + 1
                                    workout_service.log_set(set_id, session_id, elog.exercise_log_id, set_num, weight, reps, rpe)
                                    st.success(f"Logged Set {set_num}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to log set: {e}")
            else:
                st.info("No exercises added to this session yet.")

            # Form to Add Exercise to Session
            st.divider()
            st.subheader("Add Exercise to Session")
            exercises = exercise_service.list_exercises()
            if exercises:
                ex_options = {e.exercise_id: e.name for e in exercises}
                selected_ex_id = st.selectbox("Select Exercise", options=list(ex_options.keys()), format_func=lambda x: ex_options[x])
                if st.button("Add Selected Exercise"):
                    try:
                        elog_id = f"elog-{uuid.uuid4().hex[:8]}"
                        workout_service.add_exercise_to_session(session_id, selected_ex_id, elog_id)
                        st.success("Exercise added to session!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add exercise: {e}")
            else:
                st.warning("No exercises in catalog. Go to 'Exercise Catalog' tab to add one.")

            # End Session Form
            st.divider()
            st.subheader("Complete Workout Session")
            with st.form(key="end_session_form"):
                calories = st.number_input("Calories Burned (kcal)", min_value=0.0, value=300.0, step=50.0)
                hr = st.number_input("Average Heart Rate (bpm)", min_value=0, value=130)
                end_submit = st.form_submit_button("End Session & Save", use_container_width=True)
                if end_submit:
                    try:
                        workout_service.end_session(session_id, calories, hr if hr > 0 else None)
                        st.success("Workout session successfully completed and saved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to end session: {e}")
        else:
            # Start new session
            st.info("No active workout session found.")
            plans = workout_service.get_user_plans(user_id)
            plan_options = {"None": None}
            for p in plans:
                plan_options[p.name] = p.plan_id
            
            selected_plan_name = st.selectbox("Select Workout Plan (Optional)", list(plan_options.keys()))
            if st.button("Start New Session", use_container_width=True):
                try:
                    new_session_id = f"sess-{uuid.uuid4().hex[:8]}"
                    workout_service.start_session(new_session_id, user_id, plan_options[selected_plan_name])
                    st.success("New workout session started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start session: {e}")

    # --- TAB 2: History ---
    with tab_history:
        st.subheader("Workout Session History")
        sessions = session_repo.get_user_sessions(user_id)
        # Filter sessions for selected_date or show all
        filter_date = st.checkbox("Filter by target date only", value=True)
        
        display_sessions = []
        for s in sessions:
            if s.status == "COMPLETED":
                session_date = s.start_time.split()[0]
                if not filter_date or session_date == selected_date:
                    display_sessions.append(s)

        if display_sessions:
            for s in display_sessions:
                with st.expander(f"📅 Workout on {s.start_time} — {s.calories_burned_kcal or 0:.0f} kcal"):
                    st.write(f"**Start Time:** {s.start_time}")
                    st.write(f"**End Time:** {s.end_time}")
                    st.write(f"**Heart Rate:** {s.avg_heart_rate or 'N/A'} bpm")
                    
                    # Fetch exercises for this session
                    elogs = workout_service.log_repo.get_session_logs(s.session_id)
                    if elogs:
                        st.markdown("**Exercises & Sets:**")
                        for elog in elogs:
                            ex = exercise_service.get_exercise(elog.exercise_id)
                            ex_name = ex.name if ex else "Unknown Exercise"
                            sets = workout_service.set_repo.get_log_sets(elog.exercise_log_id)
                            sets_str = ", ".join([f"{s.weight:.1f}kg×{s.reps}" for s in sorted(sets, key=lambda x: x.set_number)])
                            st.write(f"- **{ex_name}**: {sets_str if sets_str else 'No sets logged'}")
                    else:
                        st.caption("No exercises logged.")
        else:
            st.info("No completed workout sessions found for the selected filter.")

    # --- TAB 3: Catalog ---
    with tab_catalog:
        st.subheader("Configure Exercise Catalog")
        
        # Display existing
        exercises = exercise_service.list_exercises()
        if exercises:
            for ex in exercises:
                st.markdown(f"""
                    <div class='glass-card'>
                        <h4 style='margin:0; color:#818CF8;'>{ex.name}</h4>
                        <p style='margin:0; font-size:0.85rem; color:#94a3b8;'>Category: {ex.category}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Catalog is empty. Register exercises below.")

        st.divider()
        st.subheader("Add New Exercise to Catalog")
        with st.form(key="add_ex_form"):
            ex_name = st.text_input("Name (e.g. Bench Press)")
            ex_cat = st.selectbox("Category", ["strength", "cardio", "mobility"])
            primary_muscles = st.text_input("Primary Muscles (JSON list, e.g. [\"Chest\", \"Triceps\"])", value="[\"Chest\"]")
            form_rules = st.text_area("Form Rules (JSON dict, e.g. {\"setup\": \"Feet flat\", \"execution\": \"Lower to chest\"})", value="{\"setup\": \"\", \"execution\": \"\"}")
            
            ex_submit = st.form_submit_button("Add Exercise")
            if ex_submit:
                try:
                    new_ex = Exercise(
                        exercise_id=f"ex-{uuid.uuid4().hex[:8]}",
                        name=ex_name,
                        category=ex_cat,
                        primary_muscles=primary_muscles,
                        form_rules=form_rules
                    )
                    exercise_service.add_exercise(new_ex)
                    st.success(f"Added {ex_name} to catalog!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add exercise: {e}")
