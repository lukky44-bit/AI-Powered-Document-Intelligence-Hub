import requests

BASE_URL = "http://backend:8000"


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


def update_user_role(token, email, new_roles):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "roles": new_roles,
    }

    res = requests.put(
        f"{BASE_URL}/admin/users/roles",
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


def get_my_files(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/files/my", headers=headers)
    return r.json()


def delete_file(token, file_id):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{BASE_URL}/files/{file_id}", headers=headers)
    return r.json()
