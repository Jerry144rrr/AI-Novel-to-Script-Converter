"""剧本结构化组装与校验模块。"""

from datetime import datetime

REQUIRED_CHARACTER_FIELDS = ["id", "name"]
REQUIRED_SCENE_FIELDS = ["scene_num", "heading", "characters_present"]
REQUIRED_CONTENT_FIELDS = {"action": ["text"], "dialogue": ["character", "line"], "transition": ["effect"]}


def build_script(
    pipeline_result: dict,
    title: str = "未命名作品",
    author: str = "未知",
    genre: str = "",
) -> dict:
    """将 AI Pipeline 输出组装为完整的剧本 dict。"""
    characters = pipeline_result["characters"]
    script_content = pipeline_result["script_content"]

    # 按章节分组场景
    chapters_map: dict[int, list[dict]] = {}
    for item in script_content:
        scene_info = item["scene_info"]
        ch_num = scene_info.get("chapter_num", 1)
        if ch_num not in chapters_map:
            chapters_map[ch_num] = []
        chapters_map[ch_num].append(item)

    # 组装章节
    chapters = []
    for ch_num in sorted(chapters_map.keys()):
        items = chapters_map[ch_num]
        first_scene = items[0]["scene_info"]
        scenes = []
        for item in items:
            si = item["scene_info"]
            scenes.append({
                "scene_num": si["scene_num"],
                "heading": {
                    "location": si.get("heading", {}).get("location", ""),
                    "time": si.get("heading", {}).get("time", "日"),
                    "interior": si.get("heading", {}).get("interior", True),
                },
                "description": si.get("description", ""),
                "characters_present": si.get("characters_present", []),
                "content": _clean_content(item["content"]),
            })

        chapters.append({
            "chapter_num": ch_num,
            "title": first_scene.get("chapter_title", f"第{ch_num}章"),
            "scenes": scenes,
        })

    return {
        "script": {
            "meta": {
                "title": title,
                "author": author,
                "total_chapters": len(chapters),
                "genre": genre,
                "converted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "characters": _normalize_characters(characters),
            "chapters": chapters,
        }
    }


def validate_script(script: dict) -> list[str]:
    """校验剧本结构完整性，返回错误列表。"""
    errors = []
    s = script.get("script", script)

    if "meta" not in s:
        errors.append("缺少 meta 元信息")
    if "characters" not in s:
        errors.append("缺少 characters 角色表")
    if "chapters" not in s:
        errors.append("缺少 chapters 章节列表")

    for ch in s.get("chapters", []):
        for scene in ch.get("scenes", []):
            for field in REQUIRED_SCENE_FIELDS:
                if field not in scene:
                    errors.append(f"第{ch['chapter_num']}章场景{scene.get('scene_num','?')}缺少字段: {field}")
            for item in scene.get("content", []):
                if item["type"] not in REQUIRED_CONTENT_FIELDS:
                    errors.append(f"未知 content 类型: {item['type']}")
                else:
                    for field in REQUIRED_CONTENT_FIELDS[item["type"]]:
                        if field not in item:
                            errors.append(f"content({item['type']}) 缺少字段: {field}")
    return errors


def _normalize_characters(characters: list[dict]) -> list[dict]:
    """规范化角色数据，只保留必要字段。"""
    result = []
    for c in characters:
        result.append({
            "id": c.get("id", ""),
            "name": c.get("name", ""),
            "role": c.get("role", ""),
            "identity": c.get("identity", ""),
            "traits": c.get("traits", []),
            "description": c.get("description", ""),
            "relationships": c.get("relationships", []),
        })
    return result


def _clean_content(content: list[dict]) -> list[dict]:
    """清理 content 列表，移除空字段。"""
    cleaned = []
    for item in content:
        item = {k: v for k, v in item.items() if v not in (None, "", [])}
        cleaned.append(item)
    return cleaned
