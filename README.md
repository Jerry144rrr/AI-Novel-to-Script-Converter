# AI Novel-to-Script Converter

> AI 小说转剧本工具 — 基于 Claude 三段式 AI 工作流，可将小说高效转化为规范可编辑的影视剧本，大幅降低改编门槛。

> **Demo 视频**：[▶️ 点击观看 B 站演示视频]（https://www.bilibili.com/video/BV1BJEh6vE8V/?spm_id_from=333.1387.homepage.video_card.click&vd_source=f7a52addeb105d0210b3b6008c1d10d5）

将 3 章以上小说文本自动转换为结构化 YAML 剧本初稿。工具通过三步完成改编：全文提取角色身份、性格与人物关系；依据时空与叙事变化精准拆分场景，绑定原文行号实现溯源；自动生成标准剧本，区分动作、带情绪对白及镜头转场。全程保障人物设定统一，解决 AI 创作中常见的人设错乱、设定前后矛盾问题。

## 项目结构

```
novel-to-script/
├── app.py                  # Streamlit Web 交互界面
├── config.py               # 全局配置（API Key / 模型 / Base URL）
├── requirements.txt        # Python 依赖清单
├── .env.example            # 环境变量模板
├── .gitignore              # 排除敏感文件和构建产物
├── src/
│   ├── __init__.py
│   ├── novel_parser.py     # 章节解析与校验
│   ├── ai_analyzer.py      # AI 三阶段 Pipeline（角色→场景→剧本）
│   ├── script_builder.py   # 剧本组装与结构校验
│   └── yaml_generator.py   # YAML 序列化与输出
├── prompts/
│   ├── character_extraction.txt  # 角色提取 Prompt
│   ├── scene_detection.txt       # 场景检测 Prompt
│   └── script_conversion.txt     # 剧本转换 Prompt
├── docs/
│   ├── YAML_SCHEMA.md       # YAML Schema 定义与设计原因
│   ├── 界面操作流程.md       # 图文操作指南
│   ├── PR_DESCRIPTIONS.md   # 开发过程 PR 描述
│   └── DEMO_SCRIPT.md       # Demo 视频演讲稿
├── output/                  # 生成的 YAML 剧本输出目录
└── screenshots/             # 运行截图
```

## 第三方依赖说明

| 依赖 | 用途 | 为何选择 |
|------|------|----------|
| **streamlit** | Web 交互界面 | 纯 Python，无需前端代码，适合快速构建工具型应用 |
| **anthropic** | Claude API 调用 | 官方 SDK，支持消息流和多模型切换 |
| **pyyaml** | YAML 序列化 | Python 生态标准 YAML 库，支持自定义 representer |
| **python-dotenv** | 环境变量管理 | 安全存储 API Key，不硬编码密钥 |
| **json5** | 宽容 JSON 解析 | 容忍尾逗号、注释等 AI 输出中常见的不规范 JSON |

所有依赖均为开源库，`requirements.txt` 中已声明完整版本约束。

## 原创声明

本项目所有代码（`src/`、`app.py`、`config.py`、`prompts/`）均为原创开发。使用 Claude API 作为 AI 引擎，通过灵眸中转服务调用。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```
ANTHROPIC_API_KEY=your-api-key-here
MODEL_NAME=claude-sonnet-4-6
BASE_URL=https://api.lmuai.com
```

- **使用灵眸中转**（默认）：保持 `BASE_URL` 为 `https://api.lmuai.com`
- **直连 Anthropic**：将 `BASE_URL` 设为空字符串，API Key 填 Anthropic 官方 Key
- **其他中转服务**：修改 `BASE_URL` 和 `MODEL_NAME` 为对应服务的地址和模型名

> 灵眸文档见 [docs.lmuai.com](https://docs.lmuai.com)，Anthropic 官方 Key 在 [console.anthropic.com](https://console.anthropic.com) 获取。

### 3. 启动

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 使用步骤

### 第一步：输入小说

1. 在左侧填写**作品元信息**（名称、作者、题材，可选）
2. 选择输入方式：**粘贴文本** 或 **上传文件**（支持 `.txt` / `.md`）
3. 点击 **"解析章节"**

> 系统会自动识别"第X章"、"Chapter X"等章节标记。至少需要 **3 章** 才能进行转换。

### 第二步：确认解析结果

解析完成后会显示检测到的章节数量、每章字数统计和预估 Token 消耗。满足 3 章以上条件时，**"开始 AI 转换"** 按钮会亮起。

### 第三步：AI 转换

点击 **"开始 AI 转换"**，系统自动执行三个阶段：

| 阶段 | 说明 | 耗时 |
|------|------|------|
| 角色提取 | 扫描全文，提取所有角色及属性 | 10-30 秒 |
| 场景检测 | 按情节识别场景切换点 | 10-30 秒 |
| 剧本转换 | 逐场景转为剧本格式 | 30-120 秒 |

转换过程会显示实时进度。

### 第四步：查看与下载

转换完成后，在 **"转换结果"** 标签页可查看角色表、场景列表、YAML 剧本。点击 **"下载 YAML 文件"** 保存到本地，或点击 **"保存到 output 目录"**。

## YAML 剧本格式说明

生成的 YAML 文件结构如下：

```yaml
script:
  meta:              # 作品元信息
  characters:        # 全局角色表
  chapters:          # 章节列表
    - scenes:        # 场次列表
        - heading:   # 场景标题（地点/时间/内外景）
        - content:   # 剧本内容
            - type: action     # 动作描述
            - type: dialogue   # 对话（含情绪标注）
            - type: transition # 转场
```

详细的 Schema 定义和设计原因见 [`docs/YAML_SCHEMA.md`](docs/YAML_SCHEMA.md)。

## 支持的章节格式

| 格式 | 示例 |
|------|------|
| 中文序号 | 第一章 初遇、第三章 离别 |
| 中文数字 | 第一百二十章 决战 |
| 阿拉伯数字 | Chapter 1、第1章 |
| 节标记 | 第一节、第二节 |

## 常见问题

**Q: 支持英文小说吗？**
A: 当前 Prompt 主要针对中文小说优化，英文小说可能会影响角色提取和场景分割的准确性。

**Q: 最多支持多少章？**
A: Claude API 单次请求上下文为 200K tokens（约 10-15 万字），超出会自动截断。建议控制在 10 万字以内。

**Q: 转换结果不满意怎么办？**
A: 生成的 YAML 文件是可直接编辑的初稿。你可以手动修改后再运行转换，或调整 `prompts/` 目录下的 Prompt 模板。

**Q: 如何修改模型？**
A: 编辑 `.env` 中的 `MODEL_NAME`，可选 `claude-opus-4-7`（更强但更贵）或 `claude-sonnet-4-6`（默认，性价比高）。使用灵眸中转时，模型名不需要 `anthropic/` 前缀。
