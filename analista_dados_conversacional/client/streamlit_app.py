"""Interface do analista. O Streamlit só fala com a API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Analista Aurora", layout="wide")
st.title("Analista de dados da Aurora")
st.caption("Pergunte em português. O sistema escreve o SQL, executa só leitura e explica o resultado.")


def _login_screen() -> None:
    with st.form("login"):
        email = st.text_input("E-mail", value="demo@aurora.local")
        password = st.text_input("Senha", type="password", value="demo1234")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        response = httpx.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        if response.status_code != 200:
            st.error(response.json().get("detail", "Não foi possível entrar."))
            return
        payload = response.json()
        st.session_state["token"] = payload["access_token"]
        st.session_state["name"] = payload["name"]
        st.session_state["email"] = payload["email"]
        st.rerun()

    with st.expander("Criar conta"):
        with st.form("register"):
            name = st.text_input("Nome")
            new_email = st.text_input("E-mail da conta")
            new_password = st.text_input("Senha da conta", type="password")
            create = st.form_submit_button("Cadastrar")
        if create:
            response = httpx.post(
                f"{API_URL}/auth/register",
                json={"name": name, "email": new_email, "password": new_password},
                timeout=30,
            )
            if response.status_code != 200:
                detail = response.json().get("detail", "Não foi possível cadastrar.")
                st.error(detail if isinstance(detail, str) else "Revise os campos.")
                return
            payload = response.json()
            st.session_state["token"] = payload["access_token"]
            st.session_state["name"] = payload["name"]
            st.session_state["email"] = payload["email"]
            st.rerun()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    response = httpx.request(method, f"{API_URL}{path}", headers=_headers(), timeout=30, **kwargs)
    if response.status_code == 401:
        st.session_state.clear()
        st.rerun()
    return response


def _ensure_conversation() -> str:
    if st.session_state.get("conversation_id"):
        return st.session_state["conversation_id"]
    listed = _api("GET", "/conversations")
    listed.raise_for_status()
    conversations = listed.json()
    if conversations:
        st.session_state["conversation_id"] = conversations[0]["id"]
        return conversations[0]["id"]
    created = _api("POST", "/conversations", json={"title": "Nova conversa"})
    created.raise_for_status()
    st.session_state["conversation_id"] = created.json()["id"]
    return st.session_state["conversation_id"]


def _load_messages(conversation_id: str) -> None:
    response = _api("GET", f"/conversations/{conversation_id}/messages")
    response.raise_for_status()
    st.session_state["messages"] = response.json()


def _iter_sse(response: httpx.Response):
    event = "message"
    data_lines: list[str] = []
    for line in response.iter_lines():
        if line == "":
            if data_lines:
                yield event, json.loads("\n".join(data_lines))
            event = "message"
            data_lines = []
            continue
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())


def _ask(conversation_id: str, question: str):
    side: dict = {"sql": None, "result": None, "error": None}
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/conversations/{conversation_id}/messages",
            headers=_headers(),
            json={"content": question},
            timeout=180,
        ) as response:
            if response.status_code != 200:
                side["error"] = response.read().decode() or "A API recusou a pergunta."
                return
            for event, data in _iter_sse(response):
                if event == "token":
                    yield data.get("text", "")
                elif event == "sql":
                    side["sql"] = data.get("sql")
                elif event == "result":
                    side["result"] = data
                elif event == "error":
                    side["error"] = data.get("message")
    finally:
        st.session_state["last_side"] = side


if "token" not in st.session_state:
    _login_screen()
    st.stop()

with st.sidebar:
    st.write(f"**{st.session_state.get('name', '')}**")
    st.caption(st.session_state.get("email", ""))
    if st.button("Nova conversa"):
        created = _api("POST", "/conversations", json={"title": "Nova conversa"})
        created.raise_for_status()
        st.session_state["conversation_id"] = created.json()["id"]
        st.session_state["messages"] = []
        st.rerun()
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
    st.caption("Demonstração local: demo@aurora.local / demo1234")

try:
    conversation_id = _ensure_conversation()
    if "messages" not in st.session_state:
        _load_messages(conversation_id)
except httpx.HTTPError as exc:
    st.error(f"A API não respondeu em {API_URL}. Suba o FastAPI antes do Streamlit. ({exc})")
    st.stop()

for message in st.session_state.get("messages", []):
    with st.chat_message("user" if message["role"] == "user" else "assistant"):
        st.markdown(message["content"])
        if message.get("sql"):
            with st.expander("SQL executado"):
                st.code(message["sql"], language="sql")

question = st.chat_input("Pergunte sobre as vendas da Aurora")
if question:
    st.session_state.setdefault("messages", []).append({"role": "user", "content": question, "sql": None})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            answer = st.write_stream(_ask(conversation_id, question))
        except httpx.HTTPError as exc:
            st.error(f"A resposta foi interrompida. ({exc})")
            st.stop()
        side = st.session_state.pop("last_side", {})
        if side.get("error"):
            st.error(side["error"])
        if side.get("sql"):
            with st.expander("SQL executado"):
                st.code(side["sql"], language="sql")
        result = side.get("result")
        if result and result.get("columns"):
            rows = result["rows"]
            st.dataframe(rows, use_container_width=True)
            if result.get("truncated"):
                st.caption(f"Mostrando 50 de {result['row_count']} linhas.")
        st.session_state["messages"].append(
            {"role": "assistant", "content": answer or side.get("error") or "", "sql": side.get("sql")}
        )
