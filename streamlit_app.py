import streamlit as st
import httpx
import uuid

st.set_page_config(page_title="MHC - Mental Health Companion", page_icon="💙")
st.title("💙 Mental Health Companion")
st.caption("Ek safe space — apni baat karo, bina judge ke.")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())  # persists for this browser tab
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Kya chal raha hai?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Soch raha hoon..."):
            try:
                response = httpx.post(
                    "http://localhost:8000/chat",
                    json={
                        "message": prompt,
                        "user_id": st.session_state.user_id,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=30
                )
                data = response.json()
                reply = data.get("response", "Kuch issue aa gaya. Thodi der mein try karo.")

                if data.get("referral_needed"):
                    reply += "\n\n---\n💙 **Professional support:**\n- iCall: 9152987821\n- Vandrevala: 1860-2662-345"

                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                if st.session_state.get("show_metrics"):
                    metrics = data.get("metrics", {})
                    if metrics:
                        st.json(metrics)
            except Exception as e:
                reply = "Server se connect nahi ho pa raha. Backend chalu hai?"
                st.error(reply)

with st.sidebar:
    st.header("Debug")
    st.session_state["show_metrics"] = st.checkbox("Show metrics", value=False)
    if st.button("New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
