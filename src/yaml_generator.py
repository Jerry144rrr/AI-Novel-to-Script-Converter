"""YAML 生成与输出模块。"""

from pathlib import Path

import yaml


class _LiteralString(str):
    """标记多行字符串用 YAML literal block (|) 输出。"""
    pass


def _literal_presenter(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_LiteralString, _literal_presenter)


def to_yaml(script: dict, use_literal_blocks: bool = True) -> str:
    """将剧本 dict 序列化为 YAML 字符串。

    对长的 text/line 字段使用 literal block scalar (|) 保持可读性。
    """
    s = _preprocess_for_yaml(script, use_literal_blocks)

    return yaml.dump(
        s,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        width=120,
    )


def save_yaml(script: dict, output_dir: str = "output") -> Path:
    """保存 YAML 文件到 output 目录。"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    title = script.get("script", script).get("meta", {}).get("title", "script")
    filename = f"{title}_剧本.yaml"
    filepath = output_path / filename

    yaml_str = to_yaml(script)
    filepath.write_text(yaml_str, encoding="utf-8")
    return filepath


def _preprocess_for_yaml(script: dict, use_literal: bool) -> dict:
    """预处理：将长文本字段标记为 literal block。"""
    if not use_literal:
        return script

    def _walk(obj):
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_walk(item) for item in obj]
        elif isinstance(obj, str) and len(obj) > 60:
            return _LiteralString(obj)
        return obj

    return _walk(script)
