"""
AI 小说转剧本工具 — Streamlit Web 界面
"""

import streamlit as st
from pathlib import Path

from config import ANTHROPIC_API_KEY
from src.novel_parser import parse_chapters, validate_chapter_count
from src.ai_analyzer import run_pipeline
from src.script_builder import build_script, validate_script
from src.yaml_generator import to_yaml, save_yaml

st.set_page_config(
    page_title="AI 小说转剧本工具",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 AI 小说转剧本工具")
st.caption("将 3 章以上小说文本自动转换为结构化 YAML 剧本初稿")

# ---- 侧边栏：配置 ----
with st.sidebar:
    st.header("⚙️ 配置")

    api_key = st.text_input(
        "Anthropic API Key",
        value=ANTHROPIC_API_KEY,
        type="password",
        help="输入你的 Claude API Key",
    )
    if not api_key:
        st.warning("请先输入 API Key")

    st.divider()
    st.caption("输出文件保存在 `output/` 目录")

# ---- 主区域：输入 ----
tab_input, tab_result = st.tabs(["📝 输入小说", "📋 转换结果"])

with tab_input:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("小说元信息")
        title = st.text_input("作品名称", placeholder="请输入小说名称")
        author = st.text_input("作者", placeholder="请输入作者名")
        genre = st.text_input("类型/题材", placeholder="如：玄幻、悬疑、言情")

    with col2:
        st.subheader("输入方式")
        input_mode = st.radio("选择输入方式", ["粘贴文本", "上传文件"], horizontal=True)

    if input_mode == "粘贴文本":
        novel_text = st.text_area(
            "请粘贴小说内容（至少 3 章）",
            height=400,
            placeholder="请将小说全文粘贴到此处...\n\n支持的章节标记：第X章、Chapter X、第X节",
        )
    else:
        uploaded_file = st.file_uploader("上传小说文件", type=["txt", "md"])
        if uploaded_file:
            novel_text = uploaded_file.read().decode("utf-8")
            st.success(f"已加载文件：{uploaded_file.name} ({len(novel_text)} 字符)")
        else:
            novel_text = ""

    # 解析章节
    if novel_text and st.button("📖 解析章节", type="primary", use_container_width=True):
        with st.spinner("正在解析章节..."):
            chapters = parse_chapters(novel_text)
            st.session_state["chapters"] = chapters
            st.session_state["chapter_parsed"] = True

    # 显示解析结果
    if st.session_state.get("chapter_parsed"):
        chapters = st.session_state["chapters"]
        st.subheader(f"📊 解析结果：共 {len(chapters)} 章")

        if not validate_chapter_count(chapters):
            st.error(f"⚠️ 至少需要 3 章，当前仅检测到 {len(chapters)} 章。请补充更多内容。")
        else:
            st.success(f"✅ 满足最低 3 章要求，共 {len(chapters)} 章，可进行转换")

        cols = st.columns(min(len(chapters), 4))
        for i, ch in enumerate(chapters):
            with cols[i % len(cols)]:
                with st.container(border=True):
                    st.metric(ch.title, f"{ch.word_count} 字", f"约 {ch.word_count // 3} tokens")

        # 开始转换按钮
        if validate_chapter_count(chapters) and api_key:
            if st.button("🚀 开始 AI 转换", type="primary", use_container_width=True):
                st.session_state["conversion_started"] = True

# ---- 转换逻辑 ----
if st.session_state.get("conversion_started"):
    chapters = st.session_state.get("chapters", [])
    if not chapters:
        st.error("请先解析章节")
        st.stop()

    # 更新配置
    import config
    config.ANTHROPIC_API_KEY = api_key

    progress_bar = st.progress(0, "准备中...")
    status_text = st.empty()

    def progress_callback(stage, message):
        status_text.text(message)
        if stage == "stage1":
            progress_bar.progress(15, "提取角色中...")
        elif stage == "stage2":
            progress_bar.progress(35, "检测场景中...")
        elif stage == "stage3":
            progress_bar.progress(60, "转换剧本中...")
        elif stage == "done":
            progress_bar.progress(100, "完成！")

    with st.spinner("AI 正在分析小说并生成剧本，请稍候..."):
        pipeline_result = run_pipeline(chapters, progress_callback)
        script = build_script(pipeline_result, title=title, author=author, genre=genre)

        # 校验
        errors = validate_script(script)
        if errors:
            st.warning(f"剧本校验发现 {len(errors)} 个问题（可忽略）")

        st.session_state["pipeline_result"] = pipeline_result
        st.session_state["script"] = script
        st.session_state["conversion_done"] = True

    progress_bar.empty()
    status_text.empty()

# ---- 结果展示 ----
if st.session_state.get("conversion_done"):
    script = st.session_state["script"]
    pipeline_result = st.session_state["pipeline_result"]

    with tab_result:
        st.success(f"✅ 剧本转换完成！共 {len(pipeline_result['characters'])} 个角色，{len(pipeline_result['scenes'])} 个场景")

        subtab_chars, subtab_scenes, subtab_yaml = st.tabs(["👤 角色表", "🎬 场景列表", "📄 YAML 剧本"])

        with subtab_chars:
            st.subheader("提取的角色")
            for c in pipeline_result["characters"]:
                with st.container(border=True):
                    char_col1, char_col2 = st.columns([1, 3])
                    with char_col1:
                        st.markdown(f"**{c['name']}**")
                        st.caption(f"{c.get('role', '')} | {c.get('identity', '')}")
                    with char_col2:
                        st.markdown(f"特征：{'、'.join(c.get('traits', []))}")
                        st.caption(c.get('description', ''))
                        if c.get("relationships"):
                            rels = ", ".join(
                                f"与 {r.get('target','?')}：{r.get('relation','')}"
                                for r in c["relationships"]
                            )
                            st.caption(f"关系：{rels}")

        with subtab_scenes:
            st.subheader("场景切分")
            for item in pipeline_result["script_content"]:
                si = item["scene_info"]
                with st.container(border=True):
                    loc = si.get("heading", {}).get("location", "未知")
                    tm = si.get("heading", {}).get("time", "")
                    interior = "内景" if si.get("heading", {}).get("interior", True) else "外景"
                    st.markdown(f"**场景 {si['scene_num']}** — {loc} · {tm} · {interior}")
                    st.caption(si.get("description", ""))
                    st.caption(f"出场：{'、'.join(si.get('characters_present', []))} | 原文行 {si.get('start_line','?')}-{si.get('end_line','?')}")

        with subtab_yaml:
            st.subheader("YAML 剧本输出")
            yaml_str = to_yaml(script)

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "⬇️ 下载 YAML 文件",
                    data=yaml_str,
                    file_name=f"{title or 'script'}_剧本.yaml",
                    mime="text/yaml",
                    type="primary",
                )
            with col_dl2:
                if st.button("💾 保存到 output 目录"):
                    filepath = save_yaml(script)
                    st.success(f"已保存到 {filepath}")

            st.code(yaml_str, language="yaml", line_numbers=True)
