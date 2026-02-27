import streamlit as st
import base64
import json

from app_client import (
    login,
    signup,
    upload_file,
    rag_query,
    update_user_role,
    get_my_files,
    delete_file,
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
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        data = json.loads(decoded)
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

    admin_email = st.sidebar.text_input("User Email")
    new_roles = st.sidebar.multiselect(
        "Assign Roles",
        ["researcher", "doctor", "lawyer", "finance", "business", "admin"],
        default=["researcher"],
    )

    if st.sidebar.button("Update Roles"):
        response = update_user_role(
            st.session_state.token,
            admin_email,
            new_roles,
        )
        if "roles" in response:
            st.sidebar.success(f"{response['email']} → {', '.join(response['roles'])}")
        else:
            st.sidebar.error(response.get("detail", "Failed to update roles"))


# ===================== SIDEBAR: MY FILES =====================
st.sidebar.divider()
st.sidebar.title("📂 My Files")

files_response = get_my_files(st.session_state.token)
files = files_response.get("files", [])

if not files:
    st.sidebar.info("No files uploaded yet.")
else:
    for f in files:
        col1, col2 = st.sidebar.columns([4, 1])
        col1.write(f"📄 {f['filename']}")
        if col2.button("🗑", key=f"del_{f['file_id']}"):
            resp = delete_file(st.session_state.token, f["file_id"])
            if "message" in resp:
                st.sidebar.success("Deleted")
                st.rerun()
            else:
                st.sidebar.error(resp.get("detail", "Delete failed"))


# ===================== FILE UPLOAD =====================
st.subheader("📤 Upload Documents")

uploaded_files = st.file_uploader(
    "Upload PDF / DOCX / Image / Audio",
    type=["pdf", "docx", "png", "jpg", "jpeg", "mp3", "wav"],
    accept_multiple_files=True,
)

file_domain = None
if "admin" in user_roles:
    file_domain = st.selectbox(
        "Select Document Domain",
        ["legal", "healthcare", "finance", "academic", "business"],
    )
else:
    st.info("📌 Domain is assigned automatically based on your roles")

if st.button("Upload Files") and uploaded_files:
    progress = st.progress(0)
    success = False

    for i, f in enumerate(uploaded_files):
        response = upload_file(
            st.session_state.token,
            f,
            file_domain,
        )

        if "file_id" in response:
            st.toast(f"✅ {f.name} uploaded")
            success = True
        else:
            st.error(f"❌ {f.name}: {response.get('detail')}")

        progress.progress((i + 1) / len(uploaded_files))

    # 🔥 IMPORTANT: refresh sidebar file list
    if success:
        st.success("Upload complete")
        st.rerun()


# ===================== RAG QUERY =====================
st.subheader("💬 Ask a Question")

query = st.text_input("Your question")

mode = st.selectbox(
    "Select Mode",
    ["legal", "healthcare", "finance", "academic", "business"],
)

format_type = st.selectbox(
    "Response Format",
    ["text", "markdown", "json", "table"],
)

# -------- SIMPLE FILE OPTION --------
use_filename = st.radio(
    "Restrict context to a specific file?",
    ["No", "Yes"],
)

filename = None
if use_filename == "Yes":
    filename = st.text_input("Enter filename (exact match)")

if st.button("Ask"):
    payload = {
        "query": query,
        "mode": mode,
        "format": format_type,
    }

    if use_filename == "Yes":
        if not filename:
            st.error("Please enter a filename")
            st.stop()
        payload["filename"] = filename

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
