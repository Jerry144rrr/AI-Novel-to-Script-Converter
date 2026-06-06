import re
from dataclasses import dataclass, field


@dataclass
class Chapter:
    chapter_num: int
    title: str
    content: str
    word_count: int
    lines: list[str] = field(default_factory=list)


def parse_chapters(text: str) -> list[Chapter]:
    """将小说文本按章节分割，返回结构化章节列表。"""
    text = _clean_text(text)
    raw_chapters = _split_by_chapter(text)

    chapters = []
    for i, (title, content) in enumerate(raw_chapters, start=1):
        lines = content.strip().split("\n")
        chapters.append(Chapter(
            chapter_num=i,
            title=title or f"第{i}章",
            content=content.strip(),
            word_count=_count_chinese_chars(content),
            lines=lines,
        ))
    return chapters


def add_line_numbers(content: str) -> str:
    """为文本每行添加行号，用于原文追溯。"""
    lines = content.split("\n")
    return "\n".join(f"{i+1:04d}| {line}" for i, line in enumerate(lines))


def _clean_text(text: str) -> str:
    """清洗文本：去除多余空行、统一换行符。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除 3 个以上连续空行，压缩为 2 个
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _split_by_chapter(text: str) -> list[tuple[str, str]]:
    """按章节标记分割文本，返回 [(标题, 内容), ...]。"""
    patterns = [
        r"第[零一二三四五六七八九十百千\d]+章\s*[^\n]*",  # 第X章 ...
        r"Chapter\s+\d+[^\n]*",                        # Chapter X ...
        r"第[零一二三四五六七八九十百千\d]+节\s*[^\n]*",  # 第X节 ...
    ]

    combined = "|".join(f"({p})" for p in patterns)
    matches = list(re.finditer(combined, text, re.IGNORECASE))

    if not matches:
        return [("", text)]

    chapters = []
    for i, match in enumerate(matches):
        title = match.group().strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        chapters.append((title, content))

    return chapters


def _count_chinese_chars(text: str) -> int:
    """统计中文字符数（不含标点空格）。"""
    return len(re.findall(r"[一-鿿]", text))


def validate_chapter_count(chapters: list[Chapter], min_chapters: int = 3) -> bool:
    """验证是否满足最低章节数要求。"""
    return len(chapters) >= min_chapters
