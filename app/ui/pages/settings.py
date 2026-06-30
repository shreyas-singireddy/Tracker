import streamlit as st
import uuid
from app.services.user import UserService
from app.models.domain import User, UserProfile
from app.repositories.user import UserRepository

def render():
    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Settings & Profiles</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Manage user profiles, physical baselines, and configuration parameters.</p>
        </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.current_user_id
    user_service = UserService()

    tab_active, tab_register, tab_system = st.tabs(["👤 Active Profile", "➕ Register Profile", "⚙️ System Configuration"])

    # --- TAB 1: Active Profile details ---
    with tab_active:
        if user_id:
            try:
                res = user_service.get_user_and_profile(user_id)
            except Exception:
                res = None
                
            if res:
                user_obj, profile_obj = res
                st.markdown(f"""
                    <div class='glass-card bento-header'>
                        <h3 style='margin:0; color:#5E6AD2;'>{user_obj.name}</h3>
                        <p style='margin:0; font-size:0.9rem; color:#A5B4FC;'>{user_obj.email}</p>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                    <div class='glass-card'>
                        <h4 style='margin:0 0 10px 0; color:#E2E8F0;'>Physical Profile Stats</h4>
                        <div style='display:flex; gap:40px;'>
                            <div>
                                <span style='font-size:0.8rem; color:#94a3b8;'>HEIGHT</span><br>
                                <span style='font-weight:600; color:#E2E8F0;'>{profile_obj.height_cm:.1f} cm</span>
                            </div>
                            <div>
                                <span style='font-size:0.8rem; color:#94a3b8;'>WEIGHT</span><br>
                                <span style='font-weight:600; color:#E2E8F0;'>{profile_obj.weight_kg:.1f} kg</span>
                            </div>
                            <div>
                                <span style='font-size:0.8rem; color:#94a3b8;'>BIRTH DATE</span><br>
                                <span style='font-weight:600; color:#E2E8F0;'>{profile_obj.birth_date}</span>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Delete profile button
                if st.button("Delete Active Profile", use_container_width=True):
                    try:
                        user_service.user_repo.delete_user(user_id)
                        st.session_state.current_user_id = None
                        st.success("Profile deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete profile: {e}")
            else:
                st.warning("Failed to retrieve profile details.")
        else:
            st.info("No active profile selected. Please select a profile in the sidebar or register a new one.")

    # --- TAB 2: Register Profile ---
    with tab_register:
        st.subheader("Register a New Profile")
        with st.form(key="register_profile_form"):
            reg_name = st.text_input("Full Name (e.g. John Doe)")
            reg_email = st.text_input("Email Address (e.g. john@domain.com)")
            reg_birth = st.date_input("Birth Date")
            reg_height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=175.0, step=1.0)
            reg_weight = st.number_input("Weight (kg)", min_value=20.0, max_value=250.0, value=70.0, step=0.5)
            
            submit_reg = st.form_submit_button("Create Profile", use_container_width=True)
            if submit_reg:
                if not reg_name.strip() or not reg_email.strip():
                    st.error("Name and Email are required.")
                else:
                    try:
                        new_uid = f"usr-{uuid.uuid4().hex[:8]}"
                        new_user = User(
                            user_id=new_uid,
                            name=reg_name.strip(),
                            email=reg_email.strip()
                        )
                        new_profile = UserProfile(
                            user_id=new_uid,
                            birth_date=reg_birth.strftime("%Y-%m-%d"),
                            weight_kg=reg_weight,
                            height_cm=reg_height
                        )
                        
                        user_service.register_user(new_user, new_profile)
                        st.session_state.current_user_id = new_uid
                        st.success(f"Profile for {reg_name} registered successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to register profile: {e}")

    # --- TAB 3: System Configuration parameters ---
    with tab_system:
        st.subheader("System Status Parameters")
        from app.core.config import settings
        
        st.markdown(f"""
            <div class='glass-card'>
                <h4 style='margin:0 0 10px 0; color:#E2E8F0;'>Active Environments</h4>
                <div style='display:flex; flex-direction:column; gap:8px;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#94a3b8;'>Environment:</span>
                        <span style='font-weight:600; color:#5E6AD2;'>{settings.ENV}</span>
                    </div>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#94a3b8;'>Offline Mode Enforced:</span>
                        <span style='font-weight:600; color:#10B981;'>{settings.OFFLINE_MODE}</span>
                    </div>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#94a3b8;'>Database Path:</span>
                        <span style='font-weight:600; color:#F1F5F9;'>{settings.DB_PATH}</span>
                    </div>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#94a3b8;'>Logging Level:</span>
                        <span style='font-weight:600; color:#F1F5F9;'>{settings.LOG_LEVEL}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
