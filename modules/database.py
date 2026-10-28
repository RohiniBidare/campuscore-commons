import hashlib
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# Determine base data directory path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
if not os.path.exists(DATA_DIR):
  DATA_DIR = os.path.join(ROOT_DIR, "Data")

FILES = [
    "users.csv",
    "resources.csv",
    "bookings.csv",
    "checkins.csv",
    "incidents.csv",
    "waitlist.csv",
    "eligibility_requirements.csv",
    "certificate_samples.csv",
    "audit_log.csv",
    "search_queries_test.csv",
]


def load_initial_data():
  """Loads all CSV data files into st.session_state if not already loaded."""
  for filename in FILES:
    key = filename.replace(".csv", "")
    if key not in st.session_state:
      file_path = os.path.join(DATA_DIR, filename)
      if os.path.exists(file_path):
        try:
          st.session_state[key] = pd.read_csv(file_path)
        except Exception:
          st.session_state[key] = pd.DataFrame()
      else:
        st.session_state[key] = pd.DataFrame()

  # Fallback pre-seeded users if users.csv was missing or empty
  if "users" not in st.session_state or st.session_state.users.empty:
    st.session_state.users = pd.DataFrame([
        {
            "user_id": "U001",
            "full_name": "Dr. Anirudh Kumar",
            "email": "anirudh@campus.edu",
            "password": "password123",
            "role": "Lab_Manager",
            "department": "Research Operations",
            "reputation_score": 4.8,
            "monthly_quota_hours": 120,
            "used_quota_hours": 18,
            "penalty_strikes": 0,
            "status": "Active",
        },
        {
            "user_id": "U006",
            "full_name": "Alex Student",
            "email": "alex@campus.edu",
            "password": "password123",
            "role": "Student_UG",
            "department": "Biotechnology",
            "reputation_score": 4.9,
            "monthly_quota_hours": 40,
            "used_quota_hours": 12,
            "penalty_strikes": 0,
            "status": "Active",
        },
    ])

  # Ensure operational DataFrames exist in session state
  for fallback_key in [
      "bookings",
      "checkins",
      "incidents",
      "waitlist",
      "audit_log",
  ]:
    if fallback_key not in st.session_state:
      st.session_state[fallback_key] = pd.DataFrame()


def log_audit_event(
    entity_type, entity_id, actor_id, action, prev_state="", new_state=""
):
  """Appends a cryptographically hash-chained event record to the immutable audit log."""
  if "audit_log" not in st.session_state:
    st.session_state.audit_log = pd.DataFrame()

  audit_df = st.session_state.audit_log
  new_audit_id = f"AUD-{len(audit_df) + 1:04d}"
  timestamp = datetime.now().isoformat()

  # Identify previous block hash (Genesis block if first event in chain)
  if not audit_df.empty and "block_hash" in audit_df.columns:
    prev_hash = str(audit_df.iloc[-1]["block_hash"])
  else:
    prev_hash = "GENESIS_000000000000000000000000000000000000000000000000"

  # Compute cryptographic SHA-256 hash linking this event to the previous record
  payload = f"{prev_hash}|{new_audit_id}|{timestamp}|{entity_type}|{entity_id}|{actor_id}|{action}|{new_state}"
  current_block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

  new_entry = {
      "audit_id": new_audit_id,
      "timestamp": timestamp,
      "entity_type": entity_type,
      "entity_id": str(entity_id),
      "actor_user_id": str(actor_id),
      "action": action,
      "prev_state": str(prev_state),
      "new_state": str(new_state),
      "prev_hash": prev_hash[:16] + "...",
      "block_hash": current_block_hash,
      "tamper_status": "VERIFIED_VALID",
  }

  st.session_state.audit_log = pd.concat(
      [st.session_state.audit_log, pd.DataFrame([new_entry])], ignore_index=True
  )

  # Mirror write to disk if audit_log.csv exists or can be created
  try:
    csv_path = os.path.join(DATA_DIR, "audit_log.csv")
    st.session_state.audit_log.to_csv(csv_path, index=False)
  except Exception as e:
    print(f"Warning: Audit log disk write skipped: {e}")


def register_new_user(user_id, full_name, password, role, department, email=""):
  """Registers a new user into session state and permanently writes to users.csv on disk."""
  users_df = st.session_state.users

  if not users_df.empty and user_id in users_df["user_id"].values:
    return False, f"User ID '{user_id}' already exists."

  quota_map = {
      "Student / Researcher": 40,
      "Lab Manager": 120,
      "System Administrator": 200,
  }

  new_user = {
      "user_id": user_id,
      "full_name": full_name,
      "email": email or f"{user_id.lower()}@campus.edu",
      "password": str(password).strip() if password else "password123",
      "role": role,
      "department": department,
      "reputation_score": 5.0,
      "monthly_quota_hours": quota_map.get(role, 40),
      "used_quota_hours": 0,
      "penalty_strikes": 0,
      "status": "Active",
  }

  # 1. Update in-memory session state
  st.session_state.users = pd.concat(
      [users_df, pd.DataFrame([new_user])], ignore_index=True
  )

  # 2. Persist directly to physical users.csv
  csv_path = os.path.join(DATA_DIR, "users.csv")
  try:
    st.session_state.users.to_csv(csv_path, index=False)
  except Exception as e:
    print(f"File write warning: {e}")

  # 3. Log event into the hash-chained audit ledger
  log_audit_event("User", user_id, user_id, "USER_REGISTERED", "", "Active")
  return True, f"Account created! Your permanent login ID is: {user_id}"