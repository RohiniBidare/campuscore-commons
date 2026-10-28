import pandas as pd
import streamlit as st
from datetime import datetime

def handle_checkin(booking_id: str, user_id: str, condition: str, notes: str):
    """
    Records physical pickup check-in, transitions booking state to In_Custody,
    and updates session records.
    """
    if "checkins" not in st.session_state:
        st.session_state.checkins = pd.DataFrame()
    if "bookings" not in st.session_state:
        st.session_state.bookings = pd.DataFrame()

    # Check if booking exists
    b_df = st.session_state.bookings
    if b_df.empty or booking_id not in b_df["booking_id"].values:
        return False, f"Booking '{booking_id}' not found."

    # Record check-in record
    checkin_id = f"CHK-{len(st.session_state.checkins) + 1:04d}"
    new_checkin = {
        "checkin_id": checkin_id,
        "booking_id": booking_id,
        "user_id": user_id,
        "pickup_time": datetime.now().isoformat(),
        "pickup_condition": condition,
        "pickup_notes": notes,
        "return_time": "",
        "return_condition": "",
        "return_notes": "",
        "status": "In_Custody"
    }

    # Update checkins DataFrame
    st.session_state.checkins = pd.concat(
        [st.session_state.checkins, pd.DataFrame([new_checkin])], 
        ignore_index=True
    )

    # Update booking status
    st.session_state.bookings.loc[
        st.session_state.bookings["booking_id"] == booking_id, "status"
    ] = "In_Custody"

    return True, f"Check-in verified! Custody activated for booking {booking_id}."


def handle_checkout(booking_id: str, user_id: str, condition: str, notes: str):
    """
    Records return handover, updates condition deltas, and ends custody.
    """
    if "checkins" not in st.session_state or st.session_state.checkins.empty:
        return False, "No active check-in record found for this booking."

    chk_df = st.session_state.checkins
    match_idx = chk_df[chk_df["booking_id"] == booking_id].index

    if match_idx.empty:
        return False, f"No prior pickup check-in found for booking {booking_id}."

    idx = match_idx[-1]
    st.session_state.checkins.at[idx, "return_time"] = datetime.now().isoformat()
    st.session_state.checkins.at[idx, "return_condition"] = condition
    st.session_state.checkins.at[idx, "return_notes"] = notes
    st.session_state.checkins.at[idx, "status"] = "Returned"

    # Update booking status
    if "bookings" in st.session_state and not st.session_state.bookings.empty:
        st.session_state.bookings.loc[
            st.session_state.bookings["booking_id"] == booking_id, "status"
        ] = "Completed"

    return True, f"Return handover logged for booking {booking_id}."


def update_incident_status(incident_id: str, new_status: str):
    """
    Updates the adjudication status of a reported incident in session state.
    """
    if "incidents" not in st.session_state or st.session_state.incidents.empty:
        return False

    inc_df = st.session_state.incidents
    if incident_id in inc_df["incident_id"].values:
        st.session_state.incidents.loc[
            st.session_state.incidents["incident_id"] == incident_id, "status"
        ] = new_status
        return True
    return False