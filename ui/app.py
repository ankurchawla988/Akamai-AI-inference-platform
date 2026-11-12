"""Streamlit demo UI — streams tokens from the gateway and shows live per-request stats."""
import os, json, time
import requests
import streamlit as st

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway.ai-platform.svc.cluster.local:8080")
GRAFANA_URL = os.getenv("GRAFANA_URL", "")

st.set_page_config(page_title="Enterprise AI Inference Platform", page_icon="⚡", layout="wide")
st.title("⚡ Enterprise AI Inference Platform")
st.caption("Mistral-7B-Instruct · vLLM · NVIDIA RTX 4000 Ada · Akamai LKE")

with st.sidebar:
    st.header("Generation settings")
    max_tokens = st.slider("Max tokens", 32, 1024, 256, 32)
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.05)
    system_prompt = st.text_area("System prompt", "You are a concise, helpful assistant.", height=90)
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    try:
        h = requests.get(f"{GATEWAY_URL}/health", timeout=3)
        st.success("Gateway + vLLM healthy" if h.ok else "vLLM not ready")
    except requests.RequestException:
        st.error("Gateway unreachable")
    if GRAFANA_URL:
        st.link_button("Open Grafana dashboard", GRAFANA_URL)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("stats"):
            st.caption(m["stats"])

if prompt := st.chat_input("Ask the model anything…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [{"role": "system", "content": system_prompt}] + [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    with st.chat_message("assistant"):
        box, text = st.empty(), ""
        t0, ttft, chunks = time.perf_counter(), None, 0
        try:
            with requests.post(f"{GATEWAY_URL}/stream", stream=True, timeout=300,
                               json={"messages": history, "max_tokens": max_tokens,
                                     "temperature": temperature}) as r:
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    obj = json.loads(data)
                    if "error" in obj:
                        st.error(obj["error"]); break
                    delta = obj["choices"][0]["delta"].get("content", "")
                    if delta:
                        if ttft is None:
                            ttft = time.perf_counter() - t0
                        chunks += 1
                        text += delta
                        box.markdown(text + "▌")
            box.markdown(text)
            total = time.perf_counter() - t0
            tps = chunks / max(total - (ttft or 0), 1e-6)
            stats = f"⏱ TTFT {ttft or 0:.2f}s · total {total:.2f}s · ~{tps:.1f} tokens/s · {chunks} chunks"
            st.caption(stats)
            st.session_state.messages.append({"role": "assistant", "content": text, "stats": stats})
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
