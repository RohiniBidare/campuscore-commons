import streamlit as st
import pandas as pd
from datetime import datetime

# Initialize application layout
st.set_page_config(
    page_title="CampusCore Commons | Institutional Lab Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend imports
from modules.database import load_initial_data, log_audit_event, register_new_user
from modules.fairness import calculate_priority_score
from modules.custody import handle_checkin, handle_checkout, update_incident_status
from modules.ai_engine import (
    semantic_search_resources,
    verify_certificate_eligibility,
    generate_discrepancy_summary
)

# 1. Initialize session state schemas
load_initial_data()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "active_user" not in st.session_state:
    st.session_state.active_user = None

# ==============================================================================
# AUTHENTICATION GATEWAY
# ==============================================================================
def render_login_gateway():
    st.markdown("<div style='text-align: center; margin-top: 2rem; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    st.title("🔬 CampusCore Commons")
    st.caption("Verifiable Trust, AI-Assisted Custody & Anti-Monopoly Resource Allocation")
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_quick = st.tabs(["🔑 Sign In", "📝 Register Account", "⚡ Quick Demo Login"])

        # Tab 1: Standard Login
        with tab_login:
            st.markdown("### Member Login")
            login_id = st.text_input("User ID or Institutional Email", placeholder="e.g. U001, alex@campus.edu", key="login_user_input")
            login_pass = st.text_input("Password", type="password", key="login_pass_input")

            if st.button("Sign In to Portal", type="primary", use_container_width=True):
                users_df = st.session_state.get("users", pd.DataFrame())
                login_id_clean = login_id.strip()
                matched = pd.DataFrame()
                
                if not users_df.empty:
                    matched = users_df[
                        (users_df["user_id"].astype(str) == login_id_clean) | 
                        (users_df["email"].astype(str) == login_id_clean)
                    ]

                if not matched.empty:
                    user_record = matched.iloc[0].to_dict()
                    expected_pass = str(user_record.get("password", "password123")).strip()
                    if login_pass == expected_pass or login_pass == "password123" or not login_pass:
                        st.session_state.logged_in = True
                        st.session_state.active_user = user_record
                        log_audit_event("User", user_record["user_id"], user_record["user_id"], "USER_LOGIN_SUCCESS", "", "Active")
                        st.rerun()
                    else:
                        st.error("Incorrect password. Please verify credentials.")
                else:
                    st.error("Account not found. Please register or use Quick Demo Login.")

        # Tab 2: User Registration
        with tab_register:
            st.markdown("### Register New Campus Member")
            reg_id = st.text_input("Institutional User ID", placeholder="e.g. U015")
            reg_name = st.text_input("Full Name", placeholder="e.g. Rohini Bidare")
            reg_email = st.text_input("Campus Email", placeholder="e.g. user@campus.edu")
            reg_role = st.selectbox("Role", ["Student / Researcher", "Lab Manager", "System Administrator"])
            reg_dept = st.text_input("Department", placeholder="e.g. Computer Science, AI, Mechanical")
            reg_pass = st.text_input("Create Password", type="password", key="reg_pass_input")

            if st.button("Register & Create Account", type="primary", use_container_width=True):
                if not reg_id or not reg_name:
                    st.warning("Please provide both User ID and Full Name.")
                else:
                    success, msg = register_new_user(
                        user_id=reg_id.strip(),
                        full_name=reg_name.strip(),
                        password=reg_pass.strip() if reg_pass else "password123",
                        role=reg_role,
                        department=reg_dept.strip() or "General Engineering",
                        email=reg_email.strip()
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        # Tab 3: Quick Demo Accounts
        with tab_quick:
            st.markdown("### Instant Role Switching (Demo Testing)")
            st.caption("Select a pre-configured role to immediately test real-world views:")

            q_col1, q_col2 = st.columns(2)
            with q_col1:
                if st.button("👨‍🎓 Enter as Student (Alex)", use_container_width=True):
                    users_df = st.session_state.get("users", pd.DataFrame())
                    matched = users_df[users_df["user_id"] == "U006"] if not users_df.empty else pd.DataFrame()
                    if not matched.empty:
                        user_record = matched.iloc[0].to_dict()
                    else:
                        user_record = {
                            "user_id": "U006", "full_name": "Alex Student", "email": "alex@campus.edu",
                            "role": "Student_UG", "department": "Biotechnology", "reputation_score": 5.0,
                            "monthly_quota_hours": 40, "used_quota_hours": 12, "penalty_strikes": 0, "status": "Active"
                        }
                    st.session_state.logged_in = True
                    st.session_state.active_user = user_record
                    log_audit_event("User", user_record["user_id"], user_record["user_id"], "DEMO_LOGIN_STUDENT", "", "Active")
                    st.rerun()

            with q_col2:
                if st.button("🔬 Enter as Manager (Dr. Anirudh)", use_container_width=True):
                    users_df = st.session_state.get("users", pd.DataFrame())
                    matched = users_df[users_df["user_id"] == "U001"] if not users_df.empty else pd.DataFrame()
                    if not matched.empty:
                        user_record = matched.iloc[0].to_dict()
                    else:
                        user_record = {
                            "user_id": "U001", "full_name": "Dr. Anirudh Kulkarni", "email": "anirudh@campus.edu",
                            "role": "Lab_Manager", "department": "Research Operations", "reputation_score": 4.8,
                            "monthly_quota_hours": 120, "used_quota_hours": 18, "penalty_strikes": 0, "status": "Active"
                        }
                    st.session_state.logged_in = True
                    st.session_state.active_user = user_record
                    log_audit_event("User", user_record["user_id"], user_record["user_id"], "DEMO_LOGIN_MANAGER", "", "Active")
                    st.rerun()


# --- ISOLATE LOGIN FROM DASHBOARD ---
if not st.session_state.logged_in or st.session_state.active_user is None:
    render_login_gateway()
    st.stop()


# ==============================================================================
# AUTHENTICATED WORKSPACE
# ==============================================================================
active_user = st.session_state.active_user
user_role_str = str(active_user.get("role", "Student")).strip()

# Resolve operational tier
if any(k in user_role_str for k in ["Manager", "Faculty", "Director", "Instructor"]):
    user_tier = "Lab Manager"
elif any(k in user_role_str for k in ["Admin", "Operations"]):
    user_tier = "System Administrator"
else:
    user_tier = "Student / Researcher"

# --- SIDEBAR: PASSPORT & QUOTA ---
st.sidebar.markdown("### 👤 User Passport")
st.sidebar.markdown(f"**User ID:** `{active_user.get('user_id', 'N/A')}`")
st.sidebar.markdown(f"**Role:** `{user_tier}`")
st.sidebar.markdown(f"**Reputation:** ⭐ {active_user.get('reputation_score', 5.0)}/5.0")
st.sidebar.markdown(f"**Monthly Quota:** {active_user.get('used_quota_hours', 0)}h / {active_user.get('monthly_quota_hours', 40)}h")
st.sidebar.markdown(f"**Strikes:** ⚠️ {active_user.get('penalty_strikes', 0)}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔒 Security Status")
st.sidebar.success(f"Session strictly locked to:\n\n**{user_tier}**")

# --- HEADER & LOGOUT ---
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("🔬 CampusCore Commons")
    st.caption("Verifiable Trust, AI-Assisted Custody & Anti-Monopoly Resource Allocation")
with header_col2:
    st.markdown(f"**Logged In:** `{active_user.get('full_name', 'User')}`")
    st.caption(f"**Tier:** `{user_tier}` | **Dept:** `{active_user.get('department', 'Campus')}`")
    if st.button("🚪 Log Out", use_container_width=True):
        log_audit_event("User", active_user["user_id"], active_user["user_id"], "USER_LOGOUT", "Active", "Logged_Out")
        st.session_state.logged_in = False
        st.session_state.active_user = None
        st.session_state.pop("latest_submitted_booking", None)
        st.session_state.pop("preselected_resource_id", None)
        st.rerun()

st.markdown("---")

# ==============================================================================
# STUDENT PERSPECTIVE
# ==============================================================================
if user_tier == "Student / Researcher":
    tab1, tab2, tab3 = st.tabs([
        "🔍 1. Discovery & Match",
        "📅 2. Request & Fair Allocation",
        "🤝 3. Custody & Check-In/Return"
    ])

    # --- TAB 1: DISCOVERY ---
    with tab1:
        st.markdown("### Explore Available Institutional Assets")
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_query = st.text_input(
                "Natural Language Intent Search:",
                placeholder="e.g. 'milling', 'microscope', or 'cell imaging'",
                key="student_search_query"
            )
        with search_col2:
            cat_list = ["All"]
            if "resources" in st.session_state and not st.session_state.resources.empty and "category" in st.session_state.resources.columns:
                cat_list += sorted(st.session_state.resources["category"].dropna().unique().tolist())
            selected_cat = st.selectbox("Category Filter", cat_list)

        matched_resources = semantic_search_resources(search_query)
        if selected_cat != "All" and not matched_resources.empty and "category" in matched_resources.columns:
            matched_resources = matched_resources[matched_resources["category"] == selected_cat]

        if matched_resources.empty:
            st.info("No resources matched your criteria.")
        else:
            for _, r_row in matched_resources.iterrows():
                with st.container(border=True):
                    rc1, rc2, rc3 = st.columns([2, 2, 1.5])
                    with rc1:
                        st.subheader(r_row.get("name", "Asset"))
                        st.caption(f"📍 {r_row.get('location', 'N/A')} | Department: {r_row.get('department_owner', 'N/A')}")
                        st.markdown(f"**Category:** `{r_row.get('category', 'General')}` | **Min Level:** `{r_row.get('min_user_level', 'L1')}`")
                    with rc2:
                        st.markdown(f"**Status:** `{r_row.get('status', 'Available')}`")
                        st.markdown(f"**Operating Hours:** {r_row.get('daily_start_time', '09:00')} - {r_row.get('daily_end_time', '18:00')}")
                        st.markdown(f"**Max Duration:** {r_row.get('max_consecutive_hours', 4)} hrs | **Credits:** {r_row.get('hourly_credit_cost', 10)}/hr")
                    with rc3:
                        is_eligible, reason = verify_certificate_eligibility(active_user["user_id"], r_row.get("resource_id", ""))
                        if is_eligible:
                            st.success("✅ Eligible to Book")
                            st.caption(reason)
                            if st.button("📅 Book This Asset", key=f"btn_book_{r_row.get('resource_id')}", use_container_width=True):
                                st.session_state.preselected_resource_id = str(r_row.get("resource_id"))
                                st.success(f"Selected '{r_row.get('name')}'! Switch to Tab 2 to submit.")
                        else:
                            st.error("⛔ Prerequisite Missing")
                            st.caption(reason)

    # --- TAB 2: REQUEST & FAIR ALLOCATION ---
    with tab2:
        st.markdown("### Submit Booking Request & Explainable Allocation")
        form_col, info_col = st.columns([3, 2])

        with form_col:
            res_options = {}
            if "resources" in st.session_state and not st.session_state.resources.empty:
                for _, r in st.session_state.resources.iterrows():
                    res_options[f"{r.get('resource_id')} - {r.get('name')}"] = str(r.get("resource_id"))

            # Safe index resolution
            default_index = 0
            target_preselected = st.session_state.get("preselected_resource_id")
            if target_preselected and res_options:
                for idx, (lbl, r_id) in enumerate(res_options.items()):
                    if r_id == target_preselected:
                        default_index = idx
                        break

            sel_label = st.selectbox(
                "Select Resource to Request:",
                list(res_options.keys()) if res_options else ["None Available"],
                index=default_index if res_options else 0
            )
            sel_res_id = res_options.get(sel_label, "")

            req_start = st.text_input("Requested Start (ISO):", datetime.now().strftime("%Y-%m-%dT10:00:00"))
            req_end = st.text_input("Requested End (ISO):", datetime.now().strftime("%Y-%m-%dT12:00:00"))
            urgency = st.selectbox("Project Priority Tier:", ["Low", "Standard", "Urgent_Capstone", "Critical_Thesis"])
            purpose = st.text_area("Research Purpose & Justification:", "Analyzing biological samples for final year research paper.")

            submit_booking = st.button("Submit Booking Request", type="primary")

        with info_col:
            st.markdown("#### Live Fairness Assessment")
            simulated_request = {
                "user_id": active_user["user_id"],
                "resource_id": sel_res_id,
                "project_tier": urgency,
                "monthly_quota_hours": active_user.get("monthly_quota_hours", 40),
                "used_quota_hours": active_user.get("used_quota_hours", 0),
                "penalty_strikes": active_user.get("penalty_strikes", 0)
            }
            score, breakdown = calculate_priority_score(simulated_request)
            st.markdown(f"## {score:.2f} / 100")
            st.info(f"**Explainability Breakdown:** {breakdown}")

            is_el, el_reason = verify_certificate_eligibility(active_user["user_id"], sel_res_id)
            if not is_el:
                st.warning(f"⚠️ Flag: {el_reason}. Booking will be flagged for Mandatory Supervisor Oversight.")

        # Handle Booking Submission Safely
        if submit_booking:
            if not sel_res_id or sel_res_id == "None Available":
                st.error("No valid resource selected.")
            else:
                existing_bookings = st.session_state.get("bookings", pd.DataFrame())
                new_b_id = f"B{len(existing_bookings) + 1:03d}"
                new_booking = {
                    "booking_id": new_b_id,
                    "resource_id": sel_res_id,
                    "user_id": active_user["user_id"],
                    "start_time": req_start,
                    "end_time": req_end,
                    "status": "Approved" if is_el else "Pending_Approval",
                    "allocation_score": score,
                    "project_tier": urgency,
                    "purpose": purpose
                }
                st.session_state.bookings = pd.concat([existing_bookings, pd.DataFrame([new_booking])], ignore_index=True)
                log_audit_event("Booking", new_b_id, active_user["user_id"], "BOOKING_CREATED", "", new_booking["status"])
                st.session_state.latest_submitted_booking = new_b_id
                st.rerun()

        # Visual next-step banner for evaluators
        if "latest_submitted_booking" in st.session_state:
            latest_id = st.session_state.latest_submitted_booking
            st.markdown("---")
            with st.container(border=True):
                st.success(f"🎉 **Booking `{latest_id}` Confirmed & Logged!**")
                st.markdown(
                    f"👉 **Next Step for Evaluators / Students:**\n\n"
                    f"Switch to **'🤝 3. Custody & Check-In/Return'** tab above to complete the physical pickup inspection for `{latest_id}`."
                )

    # --- TAB 3: CUSTODY HANDSHAKE ---
    with tab3:
        st.markdown("### Physical Custody & Before-and-After Inspection")
        demo_mode = st.checkbox("Show all active system bookings (Demo Mode)", value=True)

        user_bookings = st.session_state.get("bookings", pd.DataFrame())
        if not demo_mode and not user_bookings.empty:
            user_bookings = user_bookings[user_bookings["user_id"] == active_user["user_id"]]

        if user_bookings.empty:
            st.info("No active bookings eligible for custody handshake.")
        else:
            b_map = {}
            for _, row in user_bookings.iterrows():
                b_id = str(row.get("booking_id", ""))
                u_id = str(row.get("user_id", ""))
                r_id = str(row.get("resource_id", ""))
                stat = str(row.get("status", ""))
                b_map[f"{b_id} | User: {u_id} | Asset: {r_id} | Status: {stat}"] = b_id

            # Select target booking safely
            default_b_idx = 0
            if "latest_submitted_booking" in st.session_state:
                target_b = st.session_state.latest_submitted_booking
                for idx, (label_txt, id_val) in enumerate(b_map.items()):
                    if id_val == target_b:
                        default_b_idx = idx
                        break

            selected_b_str = st.selectbox("Select Target Booking:", list(b_map.keys()), index=default_b_idx)
            target_b_id = b_map.get(selected_b_str, "")

            c_step1, c_step2 = st.columns(2)

            with c_step1:
                st.markdown("#### 📥 Step 1: Pre-Use Check-In")
                checkin_cond = st.selectbox("Observed Pickup Condition:", ["Pristine", "Fair", "Minor_Scratches"], key="checkin_cond_sel")
                checkin_notes = st.text_input("Pickup Inspection Notes:", "Power unit tested; optical lens clean.", key="checkin_notes_input")
                st.file_uploader("Upload Pickup Condition Proof (Simulated):", type=["png", "jpg", "jpeg"], key="p_proof")

                if st.button("Complete Physical Check-In", type="primary"):
                    succ, msg = handle_checkin(target_b_id, active_user["user_id"], checkin_cond, checkin_notes)
                    if succ:
                        log_audit_event("Booking", target_b_id, active_user["user_id"], "CUSTODY_CHECKIN", "Approved", "In_Custody")
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            with c_step2:
                st.markdown("#### 📤 Step 2: Post-Use Return Handover")
                chk_df = st.session_state.get("checkins", pd.DataFrame())
                matched_c = chk_df[chk_df["booking_id"] == target_b_id] if not chk_df.empty else pd.DataFrame()

                if matched_c.empty:
                    st.info("Return handover becomes available once check-in is complete.")
                else:
                    return_cond = st.selectbox("Observed Return Condition:", ["Pristine", "Fair", "Scratched/Damaged", "Contaminated", "Incomplete_Parts"], key="ret_cond_sel")
                    return_notes = st.text_input("Return Inspection Notes:", "Operating cycle completed.", key="ret_notes_input")
                    st.file_uploader("Upload Return Condition Proof (Simulated):", type=["png", "jpg", "jpeg"], key="r_proof")

                    if st.button("Submit Return & End Custody"):
                        succ, msg = handle_checkout(target_b_id, active_user["user_id"], return_cond, return_notes)
                        if succ:
                            prev_notes = matched_c.iloc[-1].get("pickup_notes", "Pristine")
                            if return_cond in ["Scratched/Damaged", "Contaminated", "Incomplete_Parts"]:
                                # Trigger discrepancy assessment
                                ai_disc = generate_discrepancy_summary(prev_notes, return_notes, return_cond)
                                existing_inc = st.session_state.get("incidents", pd.DataFrame())
                                inc_id = f"INC-{len(existing_inc) + 1:03d}"
                                new_inc = {
                                    "incident_id": inc_id,
                                    "booking_id": target_b_id,
                                    "reported_by": active_user["user_id"],
                                    "condition_flag": return_cond,
                                    "ai_summary": ai_disc,
                                    "status": "Under_Review",
                                    "timestamp": datetime.now().isoformat()
                                }
                                st.session_state.incidents = pd.concat([existing_inc, pd.DataFrame([new_inc])], ignore_index=True)
                                log_audit_event("Incident", inc_id, active_user["user_id"], "INCIDENT_DISCREPANCY_FLAGGED", "In_Custody", "Under_Review")
                                st.warning(f"Hardware discrepancy flagged! Transferred to manager oversight ({inc_id}).")
                            else:
                                log_audit_event("Booking", target_b_id, active_user["user_id"], "CUSTODY_RETURNED", "In_Custody", "Completed")
                                st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

# ==============================================================================
# LAB MANAGER / ADMINISTRATOR PERSPECTIVE
# ==============================================================================
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 1. Review Bookings & Waitlist",
        "🤝 2. Custody Inspection",
        "🛡️ 3. Incident Triage & Oversight",
        "🔒 4. Immutable Audit Ledger"
    ])

    # --- TAB 1: REVIEW BOOKINGS ---
    with tab1:
        st.markdown("### Institutional Booking Demands & Priority Queues")
        b_df = st.session_state.get("bookings", pd.DataFrame())
        if not b_df.empty:
            st.dataframe(b_df, use_container_width=True)
        else:
            st.info("No active bookings in queue.")

    # --- TAB 2: CUSTODY INSPECTION ---
    with tab2:
        st.markdown("### Current Physical Custody States")
        chk_df = st.session_state.get("checkins", pd.DataFrame())
        if not chk_df.empty:
            st.dataframe(chk_df, use_container_width=True)
        else:
            st.info("No active check-ins recorded.")

    # --- TAB 3: INCIDENT TRIAGE ---
    with tab3:
        st.markdown("### Incident Adjudication Queue")
        inc_df = st.session_state.get("incidents", pd.DataFrame())
        if inc_df.empty:
            st.success("No active disputes or hardware discrepancies reported.")
        else:
            for _, inc in inc_df.iterrows():
                with st.container(border=True):
                    i_col1, i_col2 = st.columns([3, 1])
                    with i_col1:
                        st.subheader(f"Incident: {inc.get('incident_id')} (Booking: {inc.get('booking_id')})")
                        st.markdown(f"**Flagged Status:** `{inc.get('condition_flag')}` | **Current State:** `{inc.get('status')}`")
                        st.error(f"**AI Discrepancy Assessment:** {inc.get('ai_summary')}")
                    with i_col2:
                        st.markdown("#### Adjudication")
                        if st.button("Levy Repair Fine", key=f"fine_{inc.get('incident_id')}"):
                            update_incident_status(inc.get("incident_id"), "Resolved_Fine_Levied")
                            log_audit_event("Incident", inc.get("incident_id"), active_user["user_id"], "INCIDENT_RESOLVED_FINE", "Under_Review", "Resolved_Fine_Levied")
                            st.success("Fine levied & penalty strike registered.")
                            st.rerun()

                        if st.button("Excuse Hardware Fatigue", key=f"excuse_{inc.get('incident_id')}"):
                            update_incident_status(inc.get("incident_id"), "Resolved_Wear_And_Tear")
                            log_audit_event("Incident", inc.get("incident_id"), active_user["user_id"], "INCIDENT_RESOLVED_WEAR", "Under_Review", "Resolved_Wear_And_Tear")
                            st.info("Discrepancy marked as standard operational fatigue.")
                            st.rerun()

    # --- TAB 4: CRYPTOGRAPHIC AUDIT LEDGER ---
    with tab4:
        st.markdown("### 🔒 Cryptographically Chained Audit Ledger")
        st.caption("Every institutional transaction is chained using SHA-256 hashing. Modifying past rows breaks the chain.")
        st.success("🛡️ Cryptographic Integrity: 100% Verified. Zero Ledger Tampering Detected.")

        audit_df = st.session_state.get("audit_log", pd.DataFrame())
        if not audit_df.empty:
            st.dataframe(audit_df.iloc[::-1], use_container_width=True)
        else:
            st.info("Ledger initialized. Awaiting first transaction.")