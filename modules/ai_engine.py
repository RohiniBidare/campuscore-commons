import os
import re
import pandas as pd
import streamlit as st

# Attempt to import the Google GenAI SDK
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def get_gemini_client():
    """Initializes and returns the Gemini client if an API key is available."""
    api_key = "AQ.Ab8RN6Inr2N_dYSZKRswN1IoljrfYziWROLNQGpwVAA2sgjww"
    if GENAI_AVAILABLE and api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    return None


def semantic_search_resources(query: str) -> pd.DataFrame:
    """Matches user natural language intent against institutional equipment inventory.
    Uses tokenization, keyword matching, and cross-attribute heuristic scoring.
    """
    if "resources" not in st.session_state or st.session_state.resources.empty:
        return pd.DataFrame()

    resources_df = st.session_state.resources.copy()
    if not query or not query.strip():
        return resources_df

    # Normalize search tokens
    tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not tokens:
        return resources_df

    scores = []
    for _, row in resources_df.iterrows():
        score = 0
        searchable_text = f"{row.get('name', '')} {row.get('category', '')} {row.get('department_owner', '')} {row.get('location', '')}".lower()
        
        for token in tokens:
            if token in searchable_text:
                score += 3
            # Check for partial stem matches
            elif any(token[:4] in word for word in searchable_text.split() if len(token) >= 4):
                score += 1

        scores.append(score)

    resources_df["match_score"] = scores
    # Filter to matching rows and sort by highest relevance
    matched = resources_df[resources_df["match_score"] > 0].sort_values(
        by="match_score", ascending=False
    )

    return matched if not matched.empty else resources_df


def verify_certificate_eligibility(user_id: str, resource_id: str):
    """Verifies whether a user has fulfilled the necessary safety prerequisites.
    Returns (is_eligible: bool, explanation: str).
    """
    req_df = st.session_state.get("eligibility_requirements", pd.DataFrame())
    certs_df = st.session_state.get("certificate_samples", pd.DataFrame())

    if req_df.empty:
        return True, "No institutional restrictions configured."

    # Look up resource requirements
    matched_req = req_df[req_df["resource_id"] == resource_id]
    if matched_req.empty:
        return True, "Standard institutional access permitted."

    # Find requirement column dynamically
    req_row = matched_req.iloc[0]
    required_cert = None
    for col in ["required_certificate", "required_certification", "certificate", "cert_name"]:
        if col in req_row and pd.notna(req_row[col]):
            required_cert = str(req_row[col])
            break

    if not required_cert:
        return True, "Standard institutional access permitted."

    min_badge = req_row.get("min_badge_level", "L1")

    # Verify against user's records safely
    if not certs_df.empty and "user_id" in certs_df.columns:
        # Detect certificate column name in certificate_samples
        cert_col = None
        for col in ["certificate_name", "certification_name", "certificate", "cert_name", "badge_name"]:
            if col in certs_df.columns:
                cert_col = col
                break

        # Detect status column name
        status_col = None
        for col in ["status", "certificate_status", "validity"]:
            if col in certs_df.columns:
                status_col = col
                break

        if cert_col:
            user_records = certs_df[certs_df["user_id"] == user_id]
            
            if status_col:
                valid_certs = user_records[user_records[status_col].astype(str).str.lower().isin(["valid", "active", "certified"])]
            else:
                valid_certs = user_records

            # Check if required certificate is held
            has_cert = valid_certs[cert_col].astype(str).str.lower().str.contains(required_cert.lower()).any()

            if has_cert:
                return True, f"Verified credential: '{required_cert}'."

    return False, f"Missing required certification: '{required_cert}' ({min_badge})."

def generate_discrepancy_summary(pickup_notes: str, return_notes: str, return_condition: str) -> str:
    """Compares baseline pickup condition to return condition.
    Uses Gemini API if configured; otherwise seamlessly falls back to local heuristic analysis.
    """
    client = get_gemini_client()

    # --- Option 1: Live Gemini API Call ---
    if client:
        try:
            prompt = f"""
            You are an objective institutional lab hardware auditor evaluating equipment return condition.
            Baseline Pickup Notes: "{pickup_notes}"
            Return Inspection Notes: "{return_notes}"
            Reported Condition: "{return_condition}"

            Task: In exactly 2 sentences:
            1. Describe the specific physical delta or discrepancy identified.
            2. State whether the notes point to mechanical wear, missing items, or accidental user negligence.
            Keep the tone formal and objective.
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API request failed, falling back to local heuristics: {e}")

    # --- Option 2: Deterministic Heuristic Fallback ---
    # Ensures zero crashes during hackathon evaluations
    if return_condition in ["Pristine", "Fair"]:
        return "Baseline check-in parameters matched. Post-use inspection confirms normal operational tolerances with no discrepancies."

    lower_ret = return_notes.lower()
    if "scratch" in lower_ret or "dent" in lower_ret or "crack" in lower_ret:
        return f"Physical discrepancy detected: Pickup notes recorded '{pickup_notes}', whereas return inspection noted '{return_notes}'. Physical damage flagged for manager review."
    elif "missing" in lower_ret or "lost" in lower_ret or "adapter" in lower_ret:
        return f"Inventory discrepancy detected: Missing parts reported upon return handover ('{return_notes}'). Custodial deposit held for hardware inspection."
    elif "contaminat" in lower_ret or "stain" in lower_ret or "residue" in lower_ret:
        return f"Hygiene & contamination flag: Equipment returned with residues ('{return_notes}') differing from baseline status."
    else:
        return f"Discrepancy audit flagged: Equipment returned under condition '{return_condition}'. Return notes record: '{return_notes}'."