"""
Research Agent UI — Next-Gen Studio
Run: streamlit run app.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

# ── Ensure starter_v0 on sys.path ─────────────────────────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env
load_lab_env(ROOT)

from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools

# ─────────────────────────────────────────────────────────────────────────────
# Config & Paths
# ─────────────────────────────────────────────────────────────────────────────
ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_YAML_PATH = ARTIFACTS_DIR / "tools.yaml"
VERSION_LOG_PATH = ARTIFACTS_DIR / "version_log.csv"

PROVIDERS = ["gemini", "openrouter", "openai", "anthropic", "ollama"]
GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
]

TOOL_METADATA = {
    "clarify": {"icon": "❓", "label": "Clarify / Ask User", "color": "#f59e0b", "category": "Control"},
    "timeline": {"icon": "🐦", "label": "User Tweets", "color": "#0ea5e9", "category": "Social"},
    "social_search": {"icon": "🔎", "label": "Twitter Search", "color": "#0284c7", "category": "Social"},
    "lookup": {"icon": "🌐", "label": "Web Search", "color": "#10b981", "category": "Web"},
    "fetch": {"icon": "📄", "label": "Read URL", "color": "#14b8a6", "category": "Web"},
    "format": {"icon": "📊", "label": "Digest Formatter", "color": "#8b5cf6", "category": "Utility"},
    "send": {"icon": "✈️", "label": "Telegram Send", "color": "#ec4899", "category": "Action"},
    "policy": {"icon": "🏢", "label": "Company Policy", "color": "#6366f1", "category": "Knowledge"},
    "papers": {"icon": "📚", "label": "arXiv Search", "color": "#f97316", "category": "Research"},
    "paper_text": {"icon": "📑", "label": "arXiv Text Reader", "color": "#ea580c", "category": "Research"},
    "wikipedia": {"icon": "📖", "label": "Wikipedia Search", "color": "#06b6d4", "category": "Knowledge"},
}

def get_tool_meta(name: str) -> dict:
    return TOOL_METADATA.get(name, {"icon": "🔧", "label": name, "color": "#64748b", "category": "Tool"})

# ─────────────────────────────────────────────────────────────────────────────
# Page Setup & Styling
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Research Agent Studio",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Modern Theme Tweaks */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
code, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Glassmorphism Header */
.studio-header {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.studio-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.studio-subtitle {
    color: #94a3b8;
    font-size: 0.875rem;
    margin-top: 4px;
}
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34d399;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}

/* Tool execution cards */
.tool-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(30, 58, 138, 0.35);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #93c5fd;
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 6px;
}

.metric-badge {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px 14px;
    border-radius: 10px;
    text-align: center;
}
.metric-badge-num {
    font-size: 1.25rem;
    font-weight: 700;
    color: #38bdf8;
}
.metric-badge-label {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Clarify alert banner */
.clarify-banner {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 12px;
    padding: 14px 18px;
    color: #fbbf24;
    margin: 12px 0;
}

/* Telegram confirmation alert */
.confirm-banner {
    background: rgba(236, 72, 153, 0.12);
    border: 1px solid rgba(236, 72, 153, 0.4);
    border-radius: 12px;
    padding: 14px 18px;
    color: #f472b6;
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Reload Dynamic Artifacts
# ─────────────────────────────────────────────────────────────────────────────
def load_current_artifacts():
    prompt_text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
    declarations = load_tool_declarations(TOOLS_YAML_PATH) if TOOLS_YAML_PATH.exists() else []
    openai_tools = to_openai_tools(declarations)
    return prompt_text, declarations, openai_tools

SYSTEM_PROMPT, TOOL_DECLARATIONS, OPENAI_TOOLS = load_current_artifacts()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar Configuration
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔬 **Research Agent**")
    st.caption("K5-L3A Day 03 • Autonomous Tool Calling")
    st.divider()

    st.markdown("#### ⚙️ **Cấu hình Model**")
    provider_name = st.selectbox("Provider", PROVIDERS, index=0)
    if provider_name == "gemini":
        model_name = st.selectbox("Model", GEMINI_MODELS, index=0)
    else:
        model_name = st.text_input("Model Name", value="")
        model_name = model_name.strip() or None

    max_tool_rounds = st.slider("Max Tool Rounds", 1, 8, 4, help="Giới hạn số vòng gọi tool lặp")
    st.divider()

    st.markdown("#### 🛠️ **Hệ thống Tools (11 Tools)**")
    cats = {}
    for td in TOOL_DECLARATIONS:
        meta = get_tool_meta(td["name"])
        cats.setdefault(meta["category"], []).append(td["name"])

    for cat_name, tools in cats.items():
        st.markdown(f"**{cat_name}:** " + " ".join([f"`{t}`" for t in tools]))

    st.divider()
    if st.button("🗑️ Xoá lịch sử hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_events = []
        st.session_state.last_rounds = []
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_events" not in st.session_state:
    st.session_state.tool_events = []
if "last_rounds" not in st.session_state:
    st.session_state.last_rounds = []

# ─────────────────────────────────────────────────────────────────────────────
# Top Header Banner
# ─────────────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
        <span style="font-size: 2.2rem;">🔬</span>
        <div>
            <h2 style="margin: 0; font-weight: 700; color: #f8fafc;">Autonomous Research Agent Studio</h2>
            <div style="color: #94a3b8; font-size: 0.88rem;">Hệ thống AI Nghiên cứu Tự động hoá với Function Calling đa tầng & MCP-ready</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <span class="status-pill">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
            {provider_name.upper()} • {model_name or 'Default'}
        </span>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# Navigation Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_chat, tab_playground, tab_eval, tab_showcase, tab_spec = st.tabs([
    "💬 Trò chuyện & Thực thi Tool",
    "🧪 Tool Playground (Thử riêng từng Tool)",
    "📈 Báo cáo Eval & Version Log",
    "📋 Giới thiệu Agent (Phần A)",
    "⚙️ System Prompt & Tools Spec",
])

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Multi-round Agent Execution
# ─────────────────────────────────────────────────────────────────────────────
def run_agent_turn(user_text: str) -> dict[str, Any]:
    try:
        provider = make_provider(provider_name)
    except Exception as e:
        return {"assistant_text": f"❌ Lỗi khởi tạo provider: {e}", "tool_events": [], "rounds": []}

    prompt_text, _, openai_tools = load_current_artifacts()
    messages = [
        {"role": "system", "content": prompt_text},
        *st.session_state.messages,
        {"role": "user", "content": user_text},
    ]

    all_tool_events = []
    rounds = []
    start_time = time.time()

    for round_idx in range(1, max_tool_rounds + 1):
        try:
            response = provider.complete(
                messages,
                openai_tools,
                model=model_name,
                temperature=0.0,
            )
        except Exception as e:
            return {
                "assistant_text": f"❌ API Error: {e}",
                "tool_events": all_tool_events,
                "rounds": rounds,
                "elapsed": time.time() - start_time,
            }

        calls = response.tool_calls
        round_record = {
            "round": round_idx,
            "assistant_text": response.text,
            "tool_calls": [{"name": c.name, "args": c.args} for c in calls],
            "tool_results": [],
        }

        if not calls:
            rounds.append(round_record)
            return {
                "assistant_text": response.text or "(Agent không trả lời văn bản)",
                "tool_events": all_tool_events,
                "rounds": rounds,
                "elapsed": time.time() - start_time,
            }

        tool_results_for_model = []
        for call in calls:
            func = TOOL_FUNCTIONS.get(call.name)
            if not func:
                result = {"error": "unknown_tool", "tool": call.name}
            else:
                try:
                    result = func(**call.args)
                except Exception as exc:
                    result = {"error": type(exc).__name__, "message": str(exc)}

            event = {"tool": call.name, "args": call.args, "result": result}
            all_tool_events.append(event)
            round_record["tool_results"].append(event)
            tool_results_for_model.append(event)

        rounds.append(round_record)

        # Check clarify
        for ev in tool_results_for_model:
            res = ev.get("result", {})
            if isinstance(res, dict) and res.get("awaiting_user"):
                question = res.get("question") or ev["args"].get("question") or "Bạn vui lòng bổ sung thêm thông tin."
                options = res.get("options") or ev["args"].get("options") or []
                return {
                    "assistant_text": question,
                    "tool_events": all_tool_events,
                    "rounds": rounds,
                    "awaiting_user": True,
                    "options": options,
                    "elapsed": time.time() - start_time,
                }

        # Check send without confirmation
        for ev in tool_results_for_model:
            res = ev.get("result", {})
            if isinstance(res, dict) and res.get("status") == "needs_confirmation":
                return {
                    "assistant_text": "⚠️ Yêu cầu gửi bài lên Telegram cần bạn bấm xác nhận trước khi phát tán.",
                    "tool_events": all_tool_events,
                    "rounds": rounds,
                    "needs_confirmation": True,
                    "pending_send_text": ev["args"].get("text", ""),
                    "elapsed": time.time() - start_time,
                }

        # Append messages for next loop
        call_summary = json.dumps([{"name": c.name, "args": c.args} for c in calls], ensure_ascii=False, indent=2)
        messages.append({
            "role": "assistant",
            "content": (response.text or "Calling tools.") + f"\n\nTOOL_CALLS_JSON:\n{call_summary}",
        })
        results_text = json.dumps(tool_results_for_model, ensure_ascii=False, indent=2, default=str)
        messages.append({
            "role": "user",
            "content": f"TOOL_RESULTS_JSON:\n{results_text[:20000]}\n\nDựa trên kết quả công cụ trên, hãy tổng hợp và trả lời người dùng chi tiết.",
        })

    return {
        "assistant_text": "(Đã chạm ngưỡng tối đa lượt gọi tool)",
        "tool_events": all_tool_events,
        "rounds": rounds,
        "elapsed": time.time() - start_time,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Chat & Tool Calling Experience
# ─────────────────────────────────────────────────────────────────────────────
with tab_chat:
    # Action buttons bar
    c_bar1, c_bar2, c_bar3 = st.columns([2, 1, 1])
    with c_bar2:
        # Download Transcript JSON button
        if st.session_state.messages:
            transcript_data = {
                "created_at": datetime.now().isoformat(),
                "provider": provider_name,
                "model": model_name,
                "history": st.session_state.messages,
                "tool_events": st.session_state.tool_events,
            }
            st.download_button(
                "📥 Tải Transcript JSON",
                data=json.dumps(transcript_data, ensure_ascii=False, indent=2),
                file_name=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
    with c_bar3:
        if st.button("🔄 Làm mới phiên", use_container_width=True):
            st.session_state.messages = []
            st.session_state.tool_events = []
            st.rerun()

    # Chat history display
    for msg in st.session_state.messages:
        role = msg["role"]
        if role == "system":
            continue
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            st.markdown(msg["content"])

    # Detailed tool trace inspection
    if st.session_state.tool_events:
        with st.expander(f"🔍 Chi tiết {len(st.session_state.tool_events)} lần gọi Tool trong phiên này", expanded=False):
            for idx, ev in enumerate(st.session_state.tool_events, 1):
                meta = get_tool_meta(ev["tool"])
                st.markdown(f"**{idx}. {meta['icon']} `{ev['tool']}`** — `{meta['label']}`")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.caption("Input Parameters")
                    st.json(ev["args"])
                with c2:
                    st.caption("Output Result")
                    res = ev["result"]
                    if isinstance(res, dict) and "error" in res:
                        st.error(f"Lỗi: {res.get('message', res['error'])}")
                    else:
                        st.json(res)

    # Chat Input Box
    prompt = st.chat_input("Nhập câu hỏi nghiên cứu, yêu cầu tra cứu web, arXiv, Wikipedia hoặc tóm tắt...")
    if prompt:
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🧠 Agent đang tư duy & kích hoạt các Tool..."):
                res = run_agent_turn(prompt)

            # Show tool badge chips
            if res["tool_events"]:
                chips_html = "".join([
                    f'<span class="tool-chip">{get_tool_meta(ev["tool"])["icon"]} {ev["tool"]}</span>'
                    for ev in res["tool_events"]
                ])
                st.markdown(f"**Tools kích hoạt:** {chips_html}", unsafe_allow_html=True)

            st.markdown(res["assistant_text"])

            # Clarify options handler
            if res.get("awaiting_user") and res.get("options"):
                st.markdown("##### 👉 Chọn nhanh phương án bổ sung:")
                cols = st.columns(len(res["options"]))
                for i, opt in enumerate(res["options"]):
                    if cols[i].button(opt, key=f"clarify_opt_{i}"):
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        st.session_state.messages.append({"role": "assistant", "content": res["assistant_text"]})
                        st.session_state.messages.append({"role": "user", "content": opt})
                        st.rerun()

            # Confirm send button handler
            if res.get("needs_confirmation"):
                st.warning("⚠️ **Hành động nhạy cảm**: Gửi nội dung lên kênh Telegram yêu cầu xác nhận bảo mật.")
                c_conf1, c_conf2 = st.columns([1, 3])
                with c_conf1:
                    if st.button("✅ Xác nhận gửi ngay", type="primary"):
                        send_func = TOOL_FUNCTIONS.get("send")
                        if send_func:
                            with st.spinner("Đang gửi lên Telegram..."):
                                send_res = send_func(text=res.get("pending_send_text", ""), confirmed=True)
                            st.success(f"Đã gửi thành công! Kết quả: {send_res}")

            st.caption(f"⏱️ Thời gian: {res.get('elapsed', 0):.2f}s • Số vòng: {len(res.get('rounds', []))} • Số tools: {len(res.get('tool_events', []))}")

        # Save to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": res["assistant_text"]})
        st.session_state.tool_events.extend(res["tool_events"])
        st.rerun()

    # Pre-built Prompt Showcase
    if not st.session_state.messages:
        st.markdown("#### 💡 **Gợi ý kịch bản nghiên cứu mẫu**")
        st.caption("Bấm vào các thẻ dưới đây để kiểm tra khả năng tự động phân luồng (Tool Routing) của Agent:")

        demo_queries = [
            ("📖 Tra cứu Wikipedia", "Tra cứu Wikipedia định nghĩa và lịch sử phát triển của Transformers trong AI", "wikipedia"),
            ("📚 Tìm Paper arXiv", "Tìm 3 bài báo mới nhất trên arXiv về Large Language Models agent reasoning", "papers"),
            ("🌐 Tin tức Web hôm nay", "Tin tức AI thế giới trong ngày hôm nay có gì nổi bật?", "lookup"),
            ("📄 Tóm tắt URL", "Tóm tắt bài viết này: https://en.wikipedia.org/wiki/Artificial_intelligence", "fetch"),
            ("🏢 Chính sách nội bộ", "Chính sách của công ty về việc sử dụng AI trong nghiên cứu và bảo mật dữ liệu?", "policy"),
            ("🐦 Tìm kiếm Twitter", "Mọi người đang bàn gì về DeepSeek trên Twitter?", "social_search"),
        ]

        c_grid1, c_grid2 = st.columns(2)
        for i, (label, q, expected_tool) in enumerate(demo_queries):
            target_col = c_grid1 if i % 2 == 0 else c_grid2
            with target_col:
                meta = get_tool_meta(expected_tool)
                if st.button(f"{label}\n\n*{q}*", key=f"quick_prompt_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": q})
                    with st.spinner("Đang chạy agent..."):
                        res = run_agent_turn(q)
                    st.session_state.messages.append({"role": "assistant", "content": res["assistant_text"]})
                    st.session_state.tool_events.extend(res["tool_events"])
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Tool Playground (Thử riêng từng Tool)
# ─────────────────────────────────────────────────────────────────────────────
with tab_playground:
    st.markdown("### 🧪 **Tool Playground — Thử nghiệm trực tiếp từng Tool**")
    st.caption("Cho phép kiểm tra hoạt động của 11 Tool độc lập (không qua Model), hỗ trợ demo kỹ thuật & kiểm tra API:")

    tool_choice = st.selectbox(
        "Chọn Tool để chạy thử nghiệm:",
        list(TOOL_FUNCTIONS.keys()),
        format_func=lambda x: f"{get_tool_meta(x)['icon']} {x} — {get_tool_meta(x)['label']}",
    )

    meta = get_tool_meta(tool_choice)
    st.info(f"**{meta['icon']} `{tool_choice}`**: {meta['label']} • Thuộc nhóm: **{meta['category']}**")

    # Dynamic Playground UI per Tool
    if tool_choice == "wikipedia":
        col1, col2 = st.columns([3, 1])
        with col1:
            wiki_q = st.text_input("Truy vấn Wikipedia", value="Artificial neural network")
        with col2:
            wiki_lang = st.selectbox("Ngôn ngữ", ["en", "vi"], index=0)
        wiki_limit = st.slider("Số lượng kết quả", 1, 10, 3)

        if st.button("🚀 Chạy Wikipedia Search", type="primary"):
            with st.spinner("Đang tìm trên Wikipedia..."):
                res = TOOL_FUNCTIONS["wikipedia"](query=wiki_q, lang=wiki_lang, max_results=wiki_limit)
            st.json(res)
            if "items" in res:
                for item in res["items"]:
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                    st.write(item.get("summary", ""))

    elif tool_choice == "papers":
        paper_q = st.text_input("Từ khóa arXiv", value="Prompt engineering for LLMs")
        paper_limit = st.slider("Số bài báo", 1, 5, 2)
        if st.button("🚀 Tìm trên arXiv", type="primary"):
            with st.spinner("Đang kết nối arXiv API..."):
                res = TOOL_FUNCTIONS["papers"](query=paper_q, max_results=paper_limit)
            st.json(res)

    elif tool_choice == "paper_text":
        arxiv_url = st.text_input("arXiv Paper ID hoặc URL", value="1706.03762")
        max_p = st.slider("Số trang đọc tối đa", 1, 10, 2)
        if st.button("🚀 Đọc nội dung PDF arXiv", type="primary"):
            with st.spinner("Đang tải và trích xuất text..."):
                res = TOOL_FUNCTIONS["paper_text"](arxiv_url=arxiv_url, max_pages=max_p)
            st.json({k: v for k, v in res.items() if k != "text"})
            if "text" in res:
                with st.expander("Xem trích đoạn text trích xuất"):
                    st.text(res["text"][:3000])

    elif tool_choice == "lookup":
        lookup_q = st.text_input("Từ khóa Web Search (Tavily)", value="OpenAI GPT-5 updates")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            lookup_topic = st.selectbox("Topic", ["general", "news"], index=1)
        with col_t2:
            lookup_time = st.selectbox("Timeframe", ["day", "week", "month", "year"], index=1)
        if st.button("🚀 Chạy Web Search", type="primary"):
            with st.spinner("Đang tra cứu qua Tavily..."):
                res = TOOL_FUNCTIONS["lookup"](query=lookup_q, topic=lookup_topic, timeframe=lookup_time)
            st.json(res)

    elif tool_choice == "fetch":
        fetch_url = st.text_input("URL trang web cần đọc", value="https://en.wikipedia.org/wiki/Artificial_intelligence")
        if st.button("🚀 Đọc URL (Firecrawl)", type="primary"):
            with st.spinner("Đang cào dữ liệu URL..."):
                res = TOOL_FUNCTIONS["fetch"](url=fetch_url)
            st.json(res)

    elif tool_choice == "policy":
        pol_q = st.text_input("Từ khóa tra cứu chính sách công ty", value="ai research ethics and citation")
        pol_area = st.selectbox("Khu vực chính sách", ["all", "ai_research", "source_citation", "data_privacy", "external_publishing", "tool_usage"])
        if st.button("🚀 Tra cứu chính sách nội bộ", type="primary"):
            res = TOOL_FUNCTIONS["policy"](query=pol_q, policy_area=pol_area)
            st.json(res)

    elif tool_choice == "format":
        st.caption("Test khuôn định dạng Markdown Digest")
        sample_items = [
            {"title": "OpenAI ra mắt mô hình mới", "url": "https://openai.com", "source": "openai.com", "summary": "Mô hình mới cải thiện suy luận."},
            {"title": "DeepSeek phát hành nghiên cứu", "url": "https://deepseek.com", "source": "deepseek.com", "summary": "Tối ưu hóa kiến trúc MoE."},
        ]
        template = st.selectbox("Khuôn mẫu", ["sections", "brief", "bullets", "thread", "daily_ai_vn"])
        if st.button("🚀 Render Markdown Digest", type="primary"):
            res = TOOL_FUNCTIONS["format"](items=sample_items, template=template, headline="Bản Tin Công Nghệ AI")
            st.markdown(res.get("markdown", ""))
            st.code(res.get("markdown", ""), language="markdown")

    else:
        st.write(f"Nhập tham số để test `{tool_choice}`:")
        func = TOOL_FUNCTIONS[tool_choice]
        st.code(f"Signature: {func.__name__}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Evaluation & Version Log Dashboard
# ─────────────────────────────────────────────────────────────────────────────
with tab_eval:
    st.markdown("### 📈 **Bảng điều khiển Đánh giá & Phiên bản (Evaluation Tracker)**")
    st.caption("Theo dõi tiến trình tối ưu Prompt/Tools qua các vòng: Baseline v0 ➔ v1 ➔ v2 ➔ v3")

    # Render version_log.csv
    if VERSION_LOG_PATH.exists():
        st.markdown("#### 📜 **Lịch sử Phiên bản (`version_log.csv`)**")
        rows = []
        with open(VERSION_LOG_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("Chưa có bản ghi nào trong version_log.csv")

    st.divider()

    # Runs JSON Inspector
    st.markdown("#### 🔍 **Thanh tra Kết quả Chạy Eval (`runs/*.json`)**")
    run_files = sorted(list(RUNS_DIR.glob("*.json")), key=os.path.getmtime, reverse=True)
    if run_files:
        selected_run_file = st.selectbox(
            "Chọn file Run để phân tích:",
            run_files,
            format_func=lambda p: f"{p.name} ({time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))})",
        )

        try:
            with open(selected_run_file, encoding="utf-8") as f:
                run_data = json.load(f)

            summary = run_data.get("summary", {})
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="metric-badge"><div class="metric-badge-num">{summary.get("case_accuracy", 0)*100:.1f}%</div><div class="metric-badge-label">Case Accuracy</div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="metric-badge"><div class="metric-badge-num">{summary.get("tool_routing_accuracy", 0)*100:.1f}%</div><div class="metric-badge-label">Tool Routing</div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="metric-badge"><div class="metric-badge-num">{summary.get("passed_cases", 0)}/{summary.get("total_cases", 0)}</div><div class="metric-badge-label">Cases Passed</div></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="metric-badge"><div class="metric-badge-num">{summary.get("provider_error_cases", 0)}</div><div class="metric-badge-label">Provider Errors</div></div>', unsafe_allow_html=True)

            st.write("")
            results = run_data.get("results", [])
            case_records = []
            for r in results:
                res_obj = r.get("result", {})
                passed = res_obj.get("passed", False)
                case_records.append({
                    "Case ID": r.get("id"),
                    "Status": "✅ PASS" if passed else "❌ FAIL",
                    "Difficulty": r.get("metadata", {}).get("difficulty", "n/a"),
                    "Skill": r.get("metadata", {}).get("skill", "n/a"),
                    "Failures": ", ".join(res_obj.get("failures", [])) or "None",
                })

            st.dataframe(case_records, use_container_width=True)

        except Exception as e:
            st.error(f"Không thể đọc file run: {e}")
    else:
        st.info("Chưa có file kết quả run nào trong thư mục `runs/`.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Giới thiệu Agent (Phần A Demo Showdown)
# ─────────────────────────────────────────────────────────────────────────────
with tab_showcase:
    st.markdown("### 📋 **Giới thiệu Nghiệp vụ Agent (Tài liệu Demo Phần A)**")
    st.caption("Dùng trực tiếp làm tài liệu thuyết trình và demo cho các đội trong buổi Showdown 16:30:")

    st.markdown("""
    #### 🌟 A1. Agent này làm được gì?
    > **AI Research Agent** là trợ lý nghiên cứu đa phương thức tự động:
    > - Tìm kiếm và tổng hợp tri thức bách khoa qua **Wikipedia** & tin tức web thời gian thực (**Tavily**).
    > - Đọc hiểu bài báo khoa học PDF học thuật từ kho lưu trữ **arXiv**.
    > - Giám sát luồng thông tin mạng xã hội (**Twitter timeline & keyword search**).
    > - Tra cứu cẩm nang chính sách nội bộ (**Company Policy**) với ranh giới tin cậy (Trust Boundary).
    > - Tự động định dạng thành bản tin Markdown Digest và xuất bản kênh **Telegram** (có chốt an toàn xác nhận).

    ---

    #### 🛠️ A2. Danh mục 11 Công cụ Agent sở hữu
    """)

    tools_table = [
        {"Tool": "📖 wikipedia", "Chức năng": "Tra cứu khái niệm bách khoa toàn thư, định nghĩa khoa học, tiểu sử", "Loại": "🌟 Mới thêm (Custom)"},
        {"Tool": "📚 papers", "Chức năng": "Tìm kiếm bài báo học thuật mới nhất trên arXiv", "Loại": "Bonus Track"},
        {"Tool": "📑 paper_text", "Chức năng": "Tải PDF arXiv và trích xuất nội dung văn bản", "Loại": "Bonus Track"},
        {"Tool": "🌐 lookup", "Chức năng": "Tìm kiếm internet tổng quát & tin tức theo timeframe", "Loại": "Core Track"},
        {"Tool": "📄 fetch", "Chức năng": "Cào và trích xuất markdown từ một liên kết URL cụ thể", "Loại": "Core Track"},
        {"Tool": "🏢 policy", "Chức năng": "Tìm kiếm chính sách công ty nội bộ (AI ethics, citation)", "Loại": "Bonus Track"},
        {"Tool": "🐦 timeline", "Chức năng": "Lấy danh sách các bài đăng tweet gần đây của tài khoản", "Loại": "Core Track"},
        {"Tool": "🔎 social_search", "Chức năng": "Tìm kiếm tweet theo từ khóa (Latest / Top)", "Loại": "Core Track"},
        {"Tool": "❓ clarify", "Chức năng": "Hỏi lại người dùng khi yêu cầu bị thiếu thông tin cốt lõi", "Loại": "Core Track"},
        {"Tool": "📊 format", "Chức năng": "Đóng gói dữ liệu thành bản tin Markdown Digest chuyên nghiệp", "Loại": "Core Track"},
        {"Tool": "✈️ send", "Chức năng": "Gửi bản tin lên Telegram channel (kèm Guardrail xác nhận)", "Loại": "Bonus Action"},
    ]
    st.dataframe(tools_table, use_container_width=True)

    st.markdown("""
    ---
    #### 💡 A3. Các câu hỏi mẫu để Ban Giám Khảo & Đội bạn thử nghiệm:
    1. *"Tra cứu Wikipedia về kiến trúc Transformer trong xử lý ngôn ngữ tự nhiên"*
    2. *"Tìm bài báo arXiv mới nhất của năm 2024 về LLM Reasoning và tóm tắt"*
    3. *"Chính sách công ty quy định thế nào về việc trích dẫn nguồn khi dùng AI?"*
    4. *"Tin tức công nghệ nổi bật trong tuần này"*
    5. *"Lấy tweet mới nhất của Sam Altman"*
    """)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Prompts & Tools Spec Viewer
# ─────────────────────────────────────────────────────────────────────────────
with tab_spec:
    st.markdown("### ⚙️ **Đặc tả Kỹ thuật (Artifacts Live Spec)**")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.markdown("#### 📜 `artifacts/system_prompt.md`")
        if SYSTEM_PROMPT_PATH.exists():
            st.code(SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"), language="markdown")
        else:
            st.error("Không tìm thấy file system_prompt.md")

    with c_s2:
        st.markdown("#### 🛠️ `artifacts/tools.yaml`")
        if TOOLS_YAML_PATH.exists():
            st.code(TOOLS_YAML_PATH.read_text(encoding="utf-8"), language="yaml")
        else:
            st.error("Không tìm thấy file tools.yaml")
