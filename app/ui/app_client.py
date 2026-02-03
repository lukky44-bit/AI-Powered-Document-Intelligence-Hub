import requests

BASE_URL = "http://127.0.0.1:8000"


def login(email, password):
    res = requests.post(
        f"{BASE_URL}/auth/login", json={"email": email, "password": password}
    )
    return res.json()


def upload_file(token, file, domain):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": file}
    data = {"file_domain": domain}

    res = requests.post(
        f"{BASE_URL}/upload/file", headers=headers, files=files, data=data
    )
    return res.json()


def rag_query(token, payload):
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.post(f"{BASE_URL}/rag/answer", headers=headers, json=payload)
    return res.json()


def update_user_role(token, email, new_role):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "new_role": new_role,
    }

    res = requests.put(
        f"{BASE_URL}/admin/users/role",
        headers=headers,
        json=payload,
    )
    return res.json()


def signup(username, email, password):
    res = requests.post(
        f"{BASE_URL}/auth/signup",
        json={"username": username, "email": email, "password": password},
    )
    return res.json()
