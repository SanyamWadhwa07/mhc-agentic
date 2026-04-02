import streamlit as st
import httpx
import uuid

st.set_page_config(page_title="MHC - Mental Health Companion", page_icon="💙")
st.title("💙 Mental Health Companion")
st.caption("Ek safe space — apni baat karo, bina judge ke.")

# --- Session state initialisation ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []

# --- Proactive re-entry greeting (shown once per session) ---
if "greeted" not in st.session_state:
    st.session_state["greeted"] = True
    if st.session_state.messages:
        greeting = "hey, acha laga phir se milke 😊 kuch share karna hai?"
    else:
        greeting = "hey yaar, glad you're here 💙 kya scene hai aaj?"
    # Inject greeting into messages so it appears in the chat history
    st.session_state.messages.append({"role": "assistant", "content": greeting})

# --- Render existing messages ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Chat input ---
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

                # --- Track mood per turn ---
                turn_num = len(st.session_state.mood_history) + 1
                st.session_state.mood_history.append({
                    "turn": turn_num,
                    "risk_level": data.get("risk_level", "low"),
                    "emotions": data.get("emotions", []),
                })

                if st.session_state.get("show_metrics"):
                    metrics = data.get("metrics", {})
                    if metrics:
                        st.json(metrics)
            except Exception as e:
                reply = "Server se connect nahi ho pa raha. Backend chalu hai?"
                st.error(reply)

# --- Sidebar ---
with st.sidebar:
    st.header("Debug")
    st.session_state["show_metrics"] = st.checkbox("Show metrics", value=False)
    if st.button("New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.mood_history = []
        # Clear greeting flag so it shows again on next run
        del st.session_state["greeted"]
        st.rerun()

    # --- Mood arc ---
    if st.session_state.mood_history:
        st.markdown("---")
        st.subheader("Your mood this session:")
        _RISK_ICON = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        mood_line = " ".join(
            _RISK_ICON.get(entry["risk_level"], "⚪")
            for entry in st.session_state.mood_history
        )
        st.markdown(mood_line)
        # Show a small breakdown on hover / expand
        with st.expander("Mood details"):
            for entry in st.session_state.mood_history:
                icon = _RISK_ICON.get(entry["risk_level"], "⚪")
                emotions_str = ", ".join(entry["emotions"]) if entry["emotions"] else "—"
                st.markdown(f"Turn {entry['turn']}: {icon} `{entry['risk_level']}` — {emotions_str}")
