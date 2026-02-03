import streamlit as st
import base64
import json

from app_client import (
    login,
    signup,
    upload_file,
    rag_query,
    update_user_role,
)

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Document AI Hub", layout="wide")
st.title("📄 AI-Powered Document Intelligence Hub")

# ---------------- SESSION STATE ----------------
if "token" not in st.session_state:
    st.session_state.token = None

if "page" not in st.session_state:
    st.session_state.page = "login"


# ---------------- JWT ROLE DECODE (UI ONLY) ----------------
def get_role_from_token(token):
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        data = json.loads(decoded)
        return data.get("role")
    except Exception:
        return None


# ===================== LOGIN PAGE =====================
if st.session_state.page == "login" and not st.session_state.token:
    st.subheader("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = login(email, password)
        if "token" in response:
            st.session_state.token = response["token"]
            st.session_state.page = "app"
            st.success("Login successful")
            st.rerun()
        else:
            st.error(response.get("detail", "Login failed"))

    st.markdown("---")

    if st.button("New user? Sign up"):
        st.session_state.page = "signup"
        st.rerun()

    st.stop()


# ===================== SIGNUP PAGE =====================
if st.session_state.page == "signup" and not st.session_state.token:
    st.subheader("📝 Sign Up")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        response = signup(username, email, password)
        if "message" in response:
            st.success("Signup successful. Please login.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error(response.get("detail", "Signup failed"))

    st.markdown("---")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

    st.stop()


# ===================== MAIN APP =====================
user_role = get_role_from_token(st.session_state.token)
st.sidebar.write(f"👤 Role: **{user_role}**")


# ===================== ADMIN PANEL =====================
if user_role == "admin":
    st.sidebar.divider()
    st.sidebar.title("🛠 Admin Panel")
    st.sidebar.subheader("Update User Role")

    admin_email = st.sidebar.text_input("User Email")
    new_role = st.sidebar.selectbox(
        "New Role",
        ["researcher", "doctor", "lawyer", "finance", "business", "admin"],
    )

    if st.sidebar.button("Update Role"):
        if not admin_email:
            st.sidebar.error("Email is required")
        else:
            response = update_user_role(
                st.session_state.token,
                admin_email,
                new_role,
            )

            if "new_role" in response:
                st.sidebar.success(f"{response['email']} → {response['new_role']}")
            else:
                st.sidebar.error(response.get("detail", "Failed to update role"))


# ===================== FILE UPLOAD =====================
st.subheader("📤 Upload Document")

uploaded_file = st.file_uploader(
    "Upload PDF / DOCX / Image / Audio",
    type=["pdf", "docx", "png", "jpg", "jpeg", "mp3", "wav"],
)

file_domain = st.selectbox(
    "Select Document Domain",
    ["legal", "healthcare", "finance", "academic", "business"],
)

if st.button("Upload File") and uploaded_file:
    response = upload_file(
        st.session_state.token,
        uploaded_file,
        file_domain,
    )

    if "file_id" in response:
        st.success("File uploaded and indexed successfully")
        st.session_state.last_file_id = response["file_id"]
    else:
        st.error(response.get("detail", "Upload failed"))


# ===================== RAG QUERY =====================
st.subheader("💬 Ask a Question")

query = st.text_input("Your question")

mode = st.selectbox(
    "Select Mode",
    ["general", "legal", "healthcare", "finance", "academic", "business"],
)

format_type = st.selectbox(
    "Response Format",
    ["text", "markdown", "json", "table"],
)

use_specific_file = st.checkbox("Query specific file")

file_id = None
if use_specific_file:
    file_id = st.text_input("Enter file_id")

if st.button("Ask"):
    payload = {
        "query": query,
        "mode": mode,
        "format": format_type,
    }

    if file_id:
        payload["file_id"] = file_id

    response = rag_query(st.session_state.token, payload)

    if "answer" in response:
        st.subheader("🧠 Answer")

        if format_type == "markdown":
            st.markdown(response["answer"])
        else:
            st.write(response["answer"])

        st.subheader("📚 Sources")
        for src in response["sources"]:
            with st.expander(f"{src['filename']} (chunk {src['chunk_id']})"):
                st.write(src["text"])
    else:
        st.error(response.get("detail", "Query failed"))


# ===================== LOGOUT =====================
st.sidebar.divider()
if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.session_state.page = "login"
    st.rerun()
