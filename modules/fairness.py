import streamlit as st
import pandas as pd

def calculate_priority_score(user_id, urgency_level="Medium", days_since_last_booking=5):
    """
    Calculates an explainable allocation score (0 to 100) based on fairness rules:
    Score = (Urgency * 0.4) + (Quota_Remaining * 0.35) - (Strikes * 15) + (Days_Since_Last * 0.25)
    """
    users_df = st.session_state.users
    user = users_df[users_df["user_id"] == user_id]
    
    if user.empty:
        return 50.0, "Standard user baseline applied."
    
    user_row = user.iloc[0]
    total_quota = float(user_row.get("monthly_quota_hours", 40))
    used_quota = float(user_row.get("used_quota_hours", 0))
    strikes = int(user_row.get("penalty_strikes", 0))
    quota_remaining = max(0.0, total_quota - used_quota)
    
    urgency_map = {"Low": 20.0, "Medium": 50.0, "High": 85.0, "Critical_Thesis": 100.0}
    urgency_val = urgency_map.get(urgency_level, 50.0)
    
    score = (
        (urgency_val * 0.4) +
        (quota_remaining * 0.35) -
        (strikes * 15.0) +
        (min(days_since_last_booking, 30) * 0.25)
    )
    score = max(0.0, min(100.0, round(score, 2)))
    
    explanation = (
        f"Score {score}/100: "
        f"{quota_remaining:.1f}h quota remaining, "
        f"{strikes} penalty strike(s), "
        f"{urgency_level} stated urgency."
    )
    
    return score, explanation

def add_to_waitlist(resource_id, slot_start, slot_end, user_id, urgency_level="Medium"):
    """
    Evaluates fairness and appends the user to the waitlist queue with priority ranking.
    """
    score, reason = calculate_priority_score(user_id, urgency_level)
    waitlist_df = st.session_state.waitlist
    
    current_queue = waitlist_df[
        (waitlist_df["resource_id"] == resource_id) &
        (waitlist_df["booking_slot_start"] == slot_start)
    ]
    position = len(current_queue) + 1
    
    new_waitlist_id = f"WL-{len(waitlist_df) + 1:04d}"
    new_entry = {
        "waitlist_id": new_waitlist_id,
        "resource_id": resource_id,
        "booking_slot_start": slot_start,
        "booking_slot_end": slot_end,
        "user_id": user_id,
        "priority_score": score,
        "queue_position": position,
        "explainable_reason": reason
    }
    
    st.session_state.waitlist = pd.concat(
        [st.session_state.waitlist, pd.DataFrame([new_entry])],
        ignore_index=True
    )
    return position, score, reason