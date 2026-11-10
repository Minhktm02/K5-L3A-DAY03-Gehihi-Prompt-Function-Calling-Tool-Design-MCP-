"""Streamlit UI cho Research Agent.

Chạy:  streamlit run streamlit_app.py
Đặt file này cùng thư mục với chat.py (file code gốc, không cần sửa).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

import chat as agent_chat  # file code gốc; đổi tên nếu file của bạn không phải chat.py
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = agent_chat.ROOT
ARTIFACTS_DIR = agent_chat.ARTIFACTS_DIR
PROVIDERS = ["openrouter", "openai", "anthropic", "gemini", "ollama"]
STATUS_LABEL = {
    "answered": ("✅", "Đã trả lời"),
    "waiting_for_user": ("❓", "Agent đang chờ bạn bổ sung"),
    "max_tool_rounds": ("⚠️", "Dừng do hết số vòng gọi tool"),
    "provider_error": ("❌", "Lỗi provider"),
}

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")


# ───────────────────────── helpers ─────────────────────────
def clean(value: Any) -> Any:
    """Chuyển về dạng JSON an toàn để st.json hiển thị được."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


@st.cache_resource(show_spinner=False)
def get_provider(name: str):
    return make_provider(name)


def new_session(cfg: dict[str, Any]) -> None:
    """Tạo phiên mới (transcript + history rỗng), giống phần khởi tạo trong main() của chat.py."""
    system_prompt_path = Path(cfg["system_prompt"])
    tools_path = Path(cfg["tools"])
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tools = to_openai_tools(load_tool_declarations(tools_path))
    provider = get_provider(cfg["provider"])
    selected_model = cfg["model"] or getattr(provider, "default_model", None)
    version = build_artifact_version(cfg["version"], system_prompt_path, tools_path)

    transcript_id = "_".join([
        agent_chat.safe_slug(cfg["version"]),
        agent_chat.safe_slug(cfg["provider"]),
        datetime.now().strftime("%Y%m%dT%H%M%S%f"),
    ])
    transcript_dir = Path(cfg["transcripts_dir"])
    st.session_state.update(
        cfg=cfg,
        provider=provider,
        system_prompt=system_prompt,
        tools=tools,
        history=[],
        artifact_version=version.artifact_version,
        transcript_path=transcript_dir / f"{transcript_id}.transcript.json",
        transcript={
            "transcript_id": transcript_id,
            **artifact_version_dict(version),
            "provider": cfg["provider"],
            "model": selected_model,
            "system_prompt": str(system_prompt_path),
            "tools": str(tools_path),
            "history_window": cfg["history_window"],
            "max_tool_rounds": cfg["max_tool_rounds"],
            "created_at": agent_chat.now_iso(),
            "updated_at": agent_chat.now_iso(),
            "turns": [],
        },
    )


def render_tool_trace(turn: dict[str, Any]) -> None:
    """Hiển thị các vòng gọi tool của một lượt: tên tool, tham số, kết quả."""
    events = turn.get("tool_events") or []
    rounds = turn.get("rounds") or []
    if not events:
        return
    with st.expander(f"🔧 {len(events)} lần gọi tool · {len(rounds)} vòng", expanded=False):
        for rnd in rounds:
            if not rnd.get("tool_results"):
                continue
            st.markdown(f"**Vòng {rnd['round']}**")
            if rnd.get("assistant_text"):
                st.caption(rnd["assistant_text"])
            for ev in rnd["tool_results"]:
                result = ev.get("result", {})
                failed = isinstance(result, dict) and "error" in result
                st.markdown(f"{'🔴' if failed else '🟢'} `{ev['tool']}`")
                left, right = st.columns(2)
                with left:
                    st.caption("Tham số")
                    st.json(clean(ev.get("args", {})), expanded=False)
                with right:
                    st.caption("Kết quả")
                    st.json(clean(result), expanded=False)


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        status = turn.get("status", "started")
        icon, label = STATUS_LABEL.get(status, ("•", status))
        if status == "provider_error":
            st.error(turn.get("error", "Lỗi không rõ"))
        else:
            if status != "answered":
                st.caption(f"{icon} {label}")
            st.markdown(turn.get("assistant_text") or "")
        render_tool_trace(turn)
        if turn.get("started_at") and turn.get("ended_at"):
            t0 = datetime.fromisoformat(turn["started_at"])
            t1 = datetime.fromisoformat(turn["ended_at"])
            st.caption(f"⏱ {(t1 - t0).total_seconds():.1f}s")


def run_turn(user_text: str) -> None:
    """Chạy một lượt hội thoại, y hệt vòng lặp trong main() của chat.py."""
    ss = st.session_state
    cfg = ss.cfg
    transcript = ss.transcript
    turn_index = len(transcript["turns"]) + 1
    messages = [
        {"role": "system", "content": ss.system_prompt},
        *agent_chat.trim_history(ss.history, cfg["history_window"]),
        {"role": "user", "content": user_text},
    ]
    turn: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": agent_chat.now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    try:
        result = agent_chat.run_model_tool_loop(
            provider=ss.provider,
            messages=messages,
            tools=ss.tools,
            model=cfg["model"] or None,
            max_tool_rounds=cfg["max_tool_rounds"],
        )
        turn.update(result)
        ss.history.append({"role": "user", "content": user_text})
        ss.history.append({"role": "assistant", "content": result["assistant_text"]})
    except Exception as exc:  # noqa: BLE001
        turn.update({"status": "provider_error", "error": f"{type(exc).__name__}: {exc}"})
    turn["ended_at"] = agent_chat.now_iso()
    transcript["turns"].append(turn)
    agent_chat.write_transcript(ss.transcript_path, transcript)


# ───────────────────────── sidebar ─────────────────────────
with st.sidebar:
    st.header("⚙️ Cấu hình")
    provider_name = st.selectbox("Provider", PROVIDERS)
    model = st.text_input("Model (để trống = mặc định của provider)", value="")
    version = st.text_input("Artifact version", value="v0", help="Ví dụ v0, v1, v2")
    system_prompt_path = st.text_input("System prompt", value=str(ARTIFACTS_DIR / "system_prompt.md"))
    tools_path = st.text_input("Tools (yaml)", value=str(ARTIFACTS_DIR / "tools.yaml"))
    transcripts_dir = st.text_input("Thư mục transcript", value=str(ROOT / "transcripts"))
    history_window = st.slider("History window (số cặp user/assistant)", 0, 20, 5)
    max_tool_rounds = st.slider("Max tool rounds", 1, 10, 4)

    cfg = {
        "provider": provider_name,
        "model": model.strip(),
        "version": version.strip() or "v0",
        "system_prompt": system_prompt_path,
        "tools": tools_path,
        "transcripts_dir": transcripts_dir,
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
    }

    if st.button("🆕 Bắt đầu phiên mới", use_container_width=True, type="primary") or "transcript" not in st.session_state:
        try:
            new_session(cfg)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Không khởi tạo được phiên: {type(exc).__name__}: {exc}")
            st.stop()
    st.caption("Đổi cấu hình xong thì bấm “Bắt đầu phiên mới” để áp dụng.")

    st.divider()
    turns = st.session_state.transcript["turns"]
    n_tools = sum(len(t.get("tool_events") or []) for t in turns)
    st.metric("Số lượt", len(turns))
    st.metric("Số lần gọi tool", n_tools)
    st.caption(f"artifact_version: `{st.session_state.artifact_version}`")
    st.caption(f"model: `{st.session_state.transcript['model']}`")
    st.caption(f"transcript: `{st.session_state.transcript_path.name}`")

# ───────────────────────── main ─────────────────────────
st.title("🔎 Research Agent")
tab_chat, tab_transcript, tab_past = st.tabs(["💬 Chat", "📄 Transcript", "🗂 Transcript cũ"])

with tab_chat:
    for t in st.session_state.transcript["turns"]:
        render_turn(t)

    prompt = st.chat_input("Nhập câu hỏi…")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Agent đang suy nghĩ và gọi tool…"):
                run_turn(prompt)
        st.rerun()  # vẽ lại toàn bộ lượt vừa xong, kèm bảng tool trace

with tab_transcript:
    transcript = st.session_state.transcript
    st.download_button(
        "⬇️ Tải transcript (.json)",
        data=json.dumps(transcript, ensure_ascii=False, indent=2, default=str),
        file_name=st.session_state.transcript_path.name,
        mime="application/json",
    )
    st.json(clean(transcript), expanded=1)

with tab_past:
    files = sorted(Path(cfg["transcripts_dir"]).glob("*.transcript.json"), reverse=True)
    if not files:
        st.info("Chưa có transcript nào trong thư mục.")
    else:
        chosen = st.selectbox("Chọn transcript", files, format_func=lambda p: p.name)
        data = json.loads(chosen.read_text(encoding="utf-8"))
        st.caption(
            f"provider: `{data.get('provider')}` · model: `{data.get('model')}` · "
            f"version: `{data.get('artifact_version', data.get('version', '?'))}` · {len(data.get('turns', []))} lượt"
        )
        for t in data.get("turns", []):
            render_turn(t)