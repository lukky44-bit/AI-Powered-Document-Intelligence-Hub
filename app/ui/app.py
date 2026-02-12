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


# ---------------- JWT ROLES DECODE (UI ONLY) ----------------
def get_roles_from_token(token):
    try:
        # Decodes the middle part of the JWT (the payload)
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        data = json.loads(decoded)
        # JSONB roles come in as a list
        roles = data.get("roles", [])
        return roles if isinstance(roles, list) else []
    except Exception:
        return []


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
user_roles = get_roles_from_token(st.session_state.token)
st.sidebar.write(f"👤 Roles: **{', '.join(user_roles)}**")


# ===================== ADMIN PANEL =====================
if "admin" in user_roles:
    st.sidebar.divider()
    st.sidebar.title("🛠 Admin Panel")
    st.sidebar.subheader("Update User Roles")

    admin_email = st.sidebar.text_input("User Email")
    new_roles = st.sidebar.multiselect(
        "Assign Roles (select multiple)",
        ["researcher", "doctor", "lawyer", "finance", "business", "admin"],
        default=["researcher"],
    )

    if st.sidebar.button("Update Roles"):
        if not admin_email:
            st.sidebar.error("Email is required")
        elif not new_roles:
            st.sidebar.error("At least one role must be selected")
        else:
            response = update_user_role(
                st.session_state.token,
                admin_email,
                new_roles,
            )

            if "roles" in response:
                st.sidebar.success(
                    f"{response['email']} → {', '.join(response['roles'])}"
                )
            else:
                st.sidebar.error(response.get("detail", "Failed to update roles"))


# ===================== FILE UPLOAD (MULTIPLE) =====================
st.subheader("📤 Upload Documents")

# accept_multiple_files=True allows selecting multiple medical reports at once
uploaded_files = st.file_uploader(
    "Upload PDF / DOCX / Image / Audio",
    type=["pdf", "docx", "png", "jpg", "jpeg", "mp3", "wav"],
    accept_multiple_files=True,
)

# Admin chooses domain, others don't
file_domain = None
if "admin" in user_roles:
    file_domain = st.selectbox(
        "Select Document Domain",
        ["legal", "healthcare", "finance", "academic", "business"],
    )
else:
    st.info(
        f"📌 Document domain will be set automatically based on your roles ({', '.join(user_roles)})"
    )

if st.button("Upload Files") and uploaded_files:
    progress_bar = st.progress(0)
    total_files = len(uploaded_files)
    success_count = 0

    for index, file in enumerate(uploaded_files):
        st.write(f"⏳ Processing: **{file.name}**...")

        response = upload_file(
            st.session_state.token,
            file,
            file_domain,
        )

        if "file_id" in response:
            success_count += 1
            st.toast(f"✅ {file.name} indexed!")
        else:
            st.error(
                f"❌ {file.name} failed: {response.get('detail', 'Upload failed')}"
            )

        # Update visual progress bar
        progress_bar.progress((index + 1) / total_files)

    if success_count > 0:
        st.success(f"Successfully processed {success_count}/{total_files} documents.")


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
            # Display source filename so you know which patient the info came from
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
