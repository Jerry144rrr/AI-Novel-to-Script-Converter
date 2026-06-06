# Pull Request 描述文档

本文档记录了 AI 小说转剧本工具的完整开发过程，按功能模块拆分为 9 个 PR，遵循"每个 PR 只做一件事"的原则。

---

## PR #1: chore: 初始化项目结构与依赖配置

**标题:** `chore: 初始化项目结构与依赖配置`

**功能描述:**
搭建 Python + Streamlit + Claude API 项目骨架，包含依赖声明、配置管理和安全措施。

**实现思路:**
- 使用 `requirements.txt` 声明所有第三方依赖（streamlit, anthropic, pyyaml, python-dotenv, json5），遵循最小依赖原则
- 通过 `python-dotenv` 加载 `.env` 文件中的敏感配置（API Key、模型名、API 地址），不硬编码任何密钥
- `.env.example` 作为配置模板提供给用户，`.gitignore` 排除真实的 `.env` 文件和构建产物
- `config.py` 集中管理全局常量（MAX_TOKENS_PER_REQUEST=16000），提供合理的默认值

**测试方式:**
```bash
pip install -r requirements.txt
python -c "from config import ANTHROPIC_API_KEY, MODEL_NAME; print('配置加载成功')"
```

---

## PR #2: feat: 实现小说章节解析模块

**标题:** `feat: 实现小说章节解析模块`

**功能描述:**
从纯文本小说中自动识别章节标记，将全文拆分为结构化的 `Chapter` 对象列表，为后续 AI 分析提供标准化的输入格式。

**实现思路:**
- 使用 `dataclass` 定义 `Chapter`，存储章节号、标题、正文、字数、行号列表
- 正则表达式匹配三类章节标记：`第X章`（支持中文数字）、`Chapter X`（英文）、`第X节`
- 文本预处理：统一换行符（`\r\n` → `\n`）、压缩 3 个以上连续空行
- `add_line_numbers()` 为每行添加 4 位行号前缀（如 `0001|`），实现原文→剧本的可追溯映射
- `_count_chinese_chars()` 统计中文字符数（排除标点空格），用于准确评估 token 消耗
- `validate_chapter_count()` 确保至少 3 章才可进行转换

**测试方式:**
```python
from src.novel_parser import parse_chapters, validate_chapter_count
text = "第一章 初遇\n张三走进了房间。\n\n第二章 离别\n张三转身离去。"
chapters = parse_chapters(text)
assert len(chapters) == 2
assert chapters[0].title == "第一章 初遇"
assert chapters[0].word_count > 0
```

---

## PR #3: feat: 新增 AI 三阶段分析 Pipeline

**标题:** `feat: 新增 AI 三阶段分析 Pipeline`

**功能描述:**
实现小说→剧本的核心转换引擎，通过三个顺序阶段调用 Claude API 完成角色提取、场景检测和剧本转换。

**实现思路:**

1. **阶段一 - 角色提取** (`extract_characters`)：将全文一次性传入，提取所有角色及其属性、关系
2. **阶段二 - 场景检测** (`detect_scenes`)：逐章处理，利用行号信息精确定位场景起止边界
3. **阶段三 - 剧本转换** (`convert_scene_to_script`)：逐场景调用，根据原文片段和角色表生成剧本格式

关键技术点：
- **Anthropic client 单例**：全局复用连接，避免重复初始化
- **json5 宽容解析** + 四层自动修复：去尾逗号 → 中文引号替换 → 未转义引号修复 → debug 文件输出
- **Prompt 模板替换**：使用 `str.replace()` 而非 `str.format()`，避免与 Prompt 中的 JSON 样例 `{}` 冲突
- **行号体系**：场景起止行号由场景检测阶段标注，剧本转换时按行号提取原文片段，确保内容可溯源
- **进度回调**：`run_pipeline()` 接受 `progress_callback(stage, message)` 实现实时进度反馈

**测试方式:**
- 使用教父前五章文本作为输入，验证三阶段依次执行
- 检查每个阶段的 AI 返回是否为合法 JSON
- 验证场景编号全局唯一且连续
- 验证角色 ID 引用一致性（character.id ↔ relationship.target ↔ characters_present）

---

## PR #4: feat: 新增剧本结构化组装与校验模块

**标题:** `feat: 新增剧本结构化组装与校验模块`

**功能描述:**
将 AI Pipeline 输出的碎片化内容（角色列表、场景列表、逐场景剧本片段）组装为完整的标准化剧本 dict，并提供结构完整性校验。

**实现思路:**
- `build_script()` 按 **meta → characters → chapters → scenes → content** 五级嵌套结构组装
- 按章节号分组场景，保持原文顺序
- `_normalize_characters()` 过滤冗余字段，只保留 YAML Schema 定义的必要属性
- `_clean_content()` 移除空值字段，保持 YAML 输出整洁
- `validate_script()` 遍历检查所有必填字段，对三种 content 类型（action/dialogue/transition）分别验证

**测试方式:**
```python
mock_result = {"characters": [...], "script_content": [...]}
script = build_script(mock_result, title="测试作品")
errors = validate_script(script)
assert len(errors) == 0
assert script["script"]["meta"]["title"] == "测试作品"
```

---

## PR #5: feat: 新增 YAML 生成与输出模块

**标题:** `feat: 新增 YAML 生成与输出模块`

**功能描述:**
将组装好的剧本 dict 序列化为可读性强的 YAML 格式，支持文件保存和下载。

**实现思路:**
- 使用 PyYAML 的 `dump()` 序列化，设置 `allow_unicode=True` 保留中文，`sort_keys=False` 保持字段逻辑顺序
- 自定义 `_LiteralString` 类型 + representer，使长文本（>60 字符）自动使用 YAML 的 `|` block scalar，大幅提升可读性
- `save_yaml()` 将文件保存到 `output/` 目录，文件名取作品名 + `_剧本.yaml`
- 递归预处理 `_preprocess_for_yaml()` 遍历整个 dict 树，识别长文本并标记

**测试方式:**
- 运行 `to_yaml()` 检查输出中是否包含 `|` block scalar
- 验证中文内容不出现 `\uXXXX` 转义
- `save_yaml()` 后检查文件是否存在且内容可合法解析

---

## PR #6: feat: 新增三阶段 Prompt 模板

**标题:** `feat: 新增三阶段 Prompt 模板`

**功能描述:**
为三段式 AI Pipeline 提供结构化的 Prompt 模板，分别用于角色提取、场景检测和剧本转换。

**实现思路:**

- `character_extraction.txt`：要求 AI 按 `char_001` 格式分配 ID，提取 traits、relationships，输出固定 JSON Schema
- `scene_detection.txt`：传入角色上下文 + 带行号的章节文本，要求标注 heading（location/time/interior）、characters_present、起止行号
- `script_conversion.txt`：传入角色表 + 场景信息 + 原文片段，要求输出 action/dialogue/transition 三种类型，dialogue 必须标注 emotion

设计要点：
- 所有 Prompt 使用 `{placeholder}` 占位符而非 Python `{}`，避免 `str.format()` 与 Prompt 内 JSON 样例冲突
- 每个模板末尾强调双引号转义规则：`JSON 字符串值中的双引号必须用反斜杠转义`
- 对话内容建议使用中文引号 `「」`，降低转义出错概率

**测试方式:**
- 逐模板传入教父第一章片段，验证 AI 返回符合预期 JSON Schema
- 检查返回 JSON 中字符串值是否包含未转义双引号（常见失败模式）

---

## PR #7: feat: 构建 Streamlit Web 交互界面

**标题:** `feat: 构建 Streamlit Web 交互界面`

**功能描述:**
构建完整的 Web 交互界面，让用户无需命令行即可完成小说→剧本的全流程转换。

**实现思路:**
- **布局**：`wide` 模式，左侧边栏放配置（API Key），主区域分两个 tab（📝 输入小说 / 📋 转换结果）
- **输入方式**：支持粘贴文本和上传 .txt/.md 文件两种模式
- **解析章节**：点击按钮后实时显示章节列表、字数统计、token 预估，3 章以上才激活"开始 AI 转换"按钮
- **AI 转换**：实时进度条 + 状态文字，反映当前所处的 Pipeline 阶段（15%/35%/60%/100%）
- **结果展示**：三个子 tab — 角色表（属性、关系）、场景列表（地点、时间、出场角色）、YAML 剧本（代码高亮 + 下载按钮 + 本地保存）
- **状态管理**：使用 `st.session_state` 保持跨步骤数据（chapters、pipeline_result、script）

**测试方式:**
```bash
streamlit run app.py
# 浏览器打开 http://localhost:8501
# 1. 粘贴教父前五章
# 2. 点击"解析章节" → 验证 5 章被识别
# 3. 点击"开始 AI 转换" → 验证进度条推进
# 4. 切换结果 tab → 验证角色表/场景/YAML 有内容
# 5. 点击"下载 YAML 文件" → 验证文件下载成功
```

---

## PR #8: docs: 添加 YAML Schema 设计文档与界面操作指南

**标题:** `docs: 添加 YAML Schema 设计文档与界面操作指南`

**功能描述:**
这是比赛题目要求的核心交付物：定义剧本 YAML Schema 并解释设计原因。

**实现思路:**

**YAML_SCHEMA.md** 从五个维度定义 Schema：
1. **meta** — 作品元信息（title, author, genre, total_chapters, converted_at）
2. **characters** — 全局角色表（id, name, role, identity, traits, description, relationships）
3. **chapters** — 章节列表，每个 chapter 包含 scenes 列表
4. **scene** — 场景定义（scene_num, heading, description, characters_present, content）
5. **content** — 剧本内容元素（action/dialogue/transition 三种 polymorphic type）

每个字段说明类型、必填性、含义。文档最后专门一节解释 Schema 的设计原因：
- 为什么用 polymorphic content type 而非统一格式？
- 为什么每场戏独立标注 characters_present？
- 为什么保留行号溯源信息？
- 为什么 dialogue 要标注 emotion？

**界面操作流程.md** 以截图标注的方式展示用户从打开界面到下载剧本的完整路径。

**测试方式:**
对照 `output/教父_剧本.yaml` 验证 Schema 定义与实际输出一致，检查每个字段是否存在且类型正确。

---

## PR #9: docs: 添加项目 README 与英文说明

**标题:** `docs: 添加项目 README 与英文说明`

**功能描述:**
完善项目文档，确保评委和用户能够快速了解项目、搭建环境、运行使用。

**实现思路:**
- **README.md（中文）**：快速开始 → 四步使用流程 → YAML 格式说明 → 章节格式支持表 → 常见问题 FAQ
- 明确列出所有第三方依赖及其用途，满足比赛合规要求
- 说明 API 配置的三种模式（灵眸中转/直连 Anthropic/其他中转），降低用户使用门槛
- 预留 Demo 视频链接位置（README 最开头）
- **DESCRIPTION.md（英文）**：技术架构概述，面向国际评审

**测试方式:**
在 GitHub 上查看 Markdown 渲染效果，确认所有链接可点击、代码块高亮正常、层级结构清晰。
