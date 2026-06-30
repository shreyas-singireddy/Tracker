import streamlit as st
import uuid
from datetime import datetime
from app.services.ai_coach import AICoachService

def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>🤖 AI Coach Chat</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Chat with the offline rule-based fitness intelligence engine for fully transparent guidance.</p>
        </div>
    """, unsafe_allow_html=True)

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to chat with the AI Coach.")
        return

    coach_service = AICoachService()

    # Session Management
    try:
        sessions = coach_service.session_repo.get_user_sessions(user_id)
    except Exception:
        sessions = []

    st.sidebar.subheader("💬 AI Sessions")
    
    session_options = {s.session_id: f"Session from {s.started_at[:16]}" for s in sessions}
    
    if sessions:
        selected_sid = st.sidebar.selectbox(
            "Select Session Thread",
            options=list(session_options.keys()),
            format_func=lambda x: session_options[x]
        )
        st.session_state.ai_session_id = selected_sid
    else:
        st.sidebar.info("No active chat sessions.")
        st.session_state.ai_session_id = None

    if st.sidebar.button("➕ Start New Chat Thread", use_container_width=True):
        try:
            new_sid = f"sess-{uuid.uuid4().hex[:8]}"
            coach_service.start_session(new_sid, user_id)
            st.session_state.ai_session_id = new_sid
            st.success("New chat thread initialized!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create session: {e}")

    # Active Session View
    active_sid = st.session_state.get("ai_session_id")
    if not active_sid:
        st.info("Please start a new chat thread using the sidebar button to begin.")
        return

    # Render History
    st.subheader("Conversation Thread")
    try:
        history = coach_service.get_session_history(active_sid)
    except Exception:
        history = []

    if history:
        for q, r in history:
            # User bubble
            st.markdown(f"""
                <div class='chat-bubble-user'>
                    <div style='font-size:0.75rem; color:#94a3b8; margin-bottom:4px; font-weight:600;'>YOU</div>
                    <div>{q.raw_text}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # AI bubble
            if r:
                st.markdown(f"""
                    <div class='chat-bubble-ai'>
                        <div style='font-size:0.75rem; color:#A5B4FC; margin-bottom:4px; font-weight:600;'>COACH</div>
                        <div style='white-space: pre-wrap;'>{r.response_text}</div>
                        <div style='margin-top: 10px; font-size: 0.75rem; color: #818CF8; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 5px;'>
                            🛡️ <b>Explainability Source:</b> {r.rule_source}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("No queries logged in this session yet. Ask a question below!")

    # Question Input
    st.divider()
    with st.form(key="chat_input_form", clear_on_submit=True):
        user_query = st.text_input("Ask about workout plans, protein goals, recovery status, or sleep logs:", placeholder="Why am I tired today?")
        submit_query = st.form_submit_button("Send Query", use_container_width=True)
        
        if submit_query:
            if not user_query.strip():
                st.warning("Please type a valid question.")
            else:
                try:
                    q_id = f"q-{uuid.uuid4().hex[:8]}"
                    r_id = f"r-{uuid.uuid4().hex[:8]}"
                    with st.spinner("Processing rule-based response..."):
                        coach_service.process_query(active_sid, q_id, r_id, user_id, user_query, date_str=selected_date)
                    st.success("Query completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to process query: {e}")
