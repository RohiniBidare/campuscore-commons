import pandas as pd
import streamlit as st

def calculate_priority_score(request_data: dict):
    """
    Computes an explainable anti-monopoly fairness priority score (0 to 100).
    Safely resolves user metadata and prevents Arrow/Pandas comparison errors.
    """
    user_id = str(request_data.get("user_id", ""))
    project_tier = str(request_data.get("project_tier", "Standard"))
    
    # 1. Resolve base user metrics safely from request or session_state
    monthly_quota = float(request_data.get("monthly_quota_hours", 40.0) or 40.0)
    used_quota = float(request_data.get("used_quota_hours", 0.0) or 0.0)
    strikes = int(request_data.get("penalty_strikes", 0) or 0)
    
    # If not passed directly, lookup safely in users DataFrame
    users_df = st.session_state.get("users", pd.DataFrame())
    if not users_df.empty and "user_id" in users_df.columns:
        matched = users_df[users_df["user_id"].astype(str) == user_id]
        if not matched.empty:
            row = matched.iloc[0]
            monthly_quota = float(row.get("monthly_quota_hours", monthly_quota) or 40.0)
            used_quota = float(row.get("used_quota_hours", used_quota) or 0.0)
            strikes = int(row.get("penalty_strikes", strikes) or 0)

    # 2. Quota Fairness Factor (0 - 40 points)
    # Rewards borrowers who have not exhausted their monthly allotment
    quota_ratio = used_quota / monthly_quota if monthly_quota > 0 else 1.0
    quota_ratio = min(max(quota_ratio, 0.0), 1.0)
    quota_score = (1.0 - quota_ratio) * 40.0

    # 3. Academic Urgency Multiplier (0 - 40 points)
    tier_scores = {
        "Critical_Thesis": 40.0,
        "Urgent_Capstone": 30.0,
        "Standard": 20.0,
        "Low": 10.0
    }
    urgency_score = tier_scores.get(project_tier, 20.0)

    # 4. Reputation & Strike Penalty Deduction (0 - 20 points)
    reputation_score = 20.0 - (strikes * 10.0)
    reputation_score = max(reputation_score, 0.0)

    # Final Composite Score
    total_score = round(quota_score + urgency_score + reputation_score, 2)
    total_score = min(max(total_score, 0.0), 100.0)

    breakdown = (
        f"Quota Factor: +{quota_score:.1f}/40 | "
        f"Urgency ({project_tier}): +{urgency_score:.1f}/40 | "
        f"Discipline: +{reputation_score:.1f}/20 (Strikes: {strikes})"
    )

    return total_score, breakdown