import json
import json5
import re
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, MODEL_NAME, MAX_TOKENS_PER_REQUEST, BASE_URL
from src.novel_parser import Chapter, add_line_numbers

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        kwargs = {"api_key": ANTHROPIC_API_KEY}
        if BASE_URL:
            kwargs["base_url"] = BASE_URL
        _client = anthropic.Anthropic(**kwargs)
    return _client


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def _call_claude(system_prompt: str, user_message: str) -> str:
    """调用 Claude API，返回文本响应。"""
    client = _get_client()
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS_PER_REQUEST,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def _extract_json(text: str) -> dict | list:
    """从 AI 响应中提取 JSON 对象，使用 json5 宽容解析，失败时自动修复。"""
    raw = text

    # 匹配 ```json ... ``` 代码块
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_match:
        text = json_match.group(1)
    else:
        # 匹配最外层 JSON
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            m = re.search(pattern, text)
            if m:
                text = m.group()
                break

    # 尝试 json5 解析
    try:
        result = json5.loads(text)
        return _normalize_json_types(result)
    except ValueError as e5:
        pass

    # json5 失败，应用修复后重试
    for attempt in range(4):
        try:
            result = json5.loads(text)
            return _normalize_json_types(result)
        except ValueError:
            if attempt == 0:
                # 修复1: 去除尾部逗号
                text = re.sub(r",\s*(\}|\])", r"\1", text)
            elif attempt == 1:
                # 修复2: 中文引号替换为 ASCII
                text = text.replace("“", '"').replace("”", '"')
                text = text.replace("‘", "'").replace("’", "'")
            elif attempt == 2:
                # 修复3: 将字符串值内的 ASCII 双引号替换为单引号
                text = re.sub(r':\s*"([^"]*)"([^"]*)"', lambda m: f': "{m.group(1)}\'{m.group(2)}"', text)
            elif attempt == 3:
                _save_debug_file(text, raw, str(e5))
                raise ValueError(f"JSON 解析多次失败，详情见 output/debug_json_error.txt\n原始错误: {e5}")

    raise ValueError("无法解析 AI 返回的 JSON")


def _save_debug_file(text: str, raw: str, err_msg: str) -> None:
    """保存调试信息。"""
    p = Path(__file__).parent.parent / "output" / "debug_json_error.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"Error: {err_msg}\n\n=== Extracted (first 2000) ===\n{text[:2000]}\n\n=== Raw (first 1000) ===\n{raw[:1000]}")


def _normalize_json_types(obj):
    """将 json5 返回的特殊类型转为标准 JSON 兼容类型。"""
    if isinstance(obj, dict):
        return {k: _normalize_json_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_json_types(item) for item in obj]
    elif isinstance(obj, float):
        if obj == int(obj) and not str(obj).lower().endswith(("e+", "e-")):
            return int(obj)
        return obj
    return obj


def extract_characters(full_text: str) -> list[dict]:
    """阶段一：从全文提取角色信息。"""
    prompt = _load_prompt("character_extraction")
    prompt = prompt.replace("{novel_text}", full_text)

    result = _call_claude(
        "你是一位专业的文学分析师。请严格按照 JSON 格式输出，不要输出任何非 JSON 文本。",
        prompt,
    )
    data = _extract_json(result)
    return data.get("characters", [])


def detect_scenes(chapters: list[Chapter], characters: list[dict]) -> list[dict]:
    """阶段二：检测所有章节的场景切分。"""
    prompt_template = _load_prompt("scene_detection")

    # 构建角色上下文
    chars_context = json.dumps(
        [{"name": c["name"], "id": c["id"], "role": c["role"]} for c in characters],
        ensure_ascii=False,
    )
    prompt_template = prompt_template.replace("{characters_context}", chars_context)

    all_scenes = []
    global_scene_num = 0

    for chapter in chapters:
        content_with_lines = add_line_numbers(chapter.content)
        prompt = prompt_template.replace("{chapter_text_with_lines}", content_with_lines)

        system = f"你正在处理第{chapter.chapter_num}章「{chapter.title}」。请严格按照 JSON 格式输出。"
        result = _call_claude(system, prompt)
        scenes_data = _extract_json(result)
        scenes = scenes_data.get("scenes", [])

        for scene in scenes:
            global_scene_num += 1
            scene["scene_num"] = global_scene_num
            scene["chapter_num"] = chapter.chapter_num
            scene["chapter_title"] = chapter.title

        all_scenes.extend(scenes)

    return all_scenes


def convert_scene_to_script(
    scene: dict,
    chapter_content: str,
    characters: list[dict],
) -> list[dict]:
    """阶段三：将单个场景转换为剧本格式。"""
    prompt_template = _load_prompt("script_conversion")

    # 提取场景对应的原文片段
    lines = chapter_content.split("\n")
    start = max(0, scene.get("start_line", 1) - 1)
    end = min(len(lines), scene.get("end_line", len(lines)))
    passage = "\n".join(lines[start:end])

    chars_context = json.dumps(characters, ensure_ascii=False, indent=2)

    prompt = (prompt_template
        .replace("{characters_context}", chars_context)
        .replace("{location}", scene.get("heading", {}).get("location", "未知"))
        .replace("{time}", scene.get("heading", {}).get("time", "日"))
        .replace("{interior}", "内景" if scene.get("heading", {}).get("interior", True) else "外景")
        .replace("{characters_present}", ", ".join(scene.get("characters_present", [])))
        .replace("{novel_passage}", passage))

    system = "你是一位资深影视编剧。请严格按照 JSON 格式输出剧本内容。"
    result = _call_claude(system, prompt)
    data = _extract_json(result)
    return data.get("content", [])


def run_pipeline(chapters: list[Chapter], progress_callback=None) -> dict:
    """执行完整的三段式转换 Pipeline。

    Args:
        chapters: 解析后的章节列表
        progress_callback: 可选回调，用于 Streamlit 进度更新。签名为 callback(stage, message)

    Returns:
        完整剧本 dict（尚未组装 meta，由 script_builder 完成）
    """
    full_text = "\n\n".join(ch.title + "\n" + ch.content for ch in chapters)

    # 阶段一：角色提取
    if progress_callback:
        progress_callback("stage1", "正在提取角色信息...")
    characters = extract_characters(full_text)

    # 阶段二：场景检测
    if progress_callback:
        progress_callback("stage2", f"已提取 {len(characters)} 个角色，正在检测场景切分...")
    scenes = detect_scenes(chapters, characters)

    # 阶段三：逐场景转换剧本
    script_content = []
    total_scenes = len(scenes)
    for i, scene in enumerate(scenes):
        chapter_num = scene.get("chapter_num", 1)
        chapter = next((ch for ch in chapters if ch.chapter_num == chapter_num), chapters[0])

        if progress_callback:
            progress_callback("stage3", f"正在转换剧本 ({i+1}/{total_scenes}): 第{chapter_num}章 场景{scene['scene_num']}")

        content = convert_scene_to_script(scene, chapter.content, characters)
        script_content.append({
            "scene_info": scene,
            "content": content,
        })

    if progress_callback:
        progress_callback("done", "剧本转换完成！")

    return {
        "characters": characters,
        "scenes": scenes,
        "script_content": script_content,
    }
