# 剧本 YAML Schema 设计文档

## 概述

本文档定义了 AI 小说转剧本工具输出的 YAML 剧本格式。该 Schema 旨在桥接小说叙事与影视剧本两种文本形态，既保留剧本行业标准结构，又为 AI 辅助创作场景做了针对性优化。

---

## 完整 Schema 定义

```
script:
  meta:                          # 元信息（必填）
    title: string                # 作品名称
    author: string               # 原作者
    total_chapters: integer      # 转换的章节总数
    genre: string                # 类型/题材
    converted_at: string         # 转换时间 (ISO 8601)

  characters:                    # 全局角色表（必填）
    - id: string                 # 唯一标识，格式 char_NNN
      name: string               # 角色姓名
      role: string               # 主角 | 配角 | 龙套
      identity: string           # 身份/职业
      traits: [string]           # 性格特征关键词
      description: string        # 角色简介
      relationships:             # 角色关系（可选）
        - target: string         # 关联角色 id
          relation: string       # 关系描述（父子/夫妻/仇敌...）

  chapters:                      # 章节列表（必填）
    - chapter_num: integer       # 章节序号
      title: string              # 章节标题
      scenes:                    # 场次列表
        - scene_num: integer     # 全局场次编号
          heading:               # 场景标题（剧本行业标准）
            location: string     # 场景地点
            time: string         # 日 | 夜 | 晨 | 昏
            interior: boolean    # true=内景, false=外景
          description: string    # 场景一句话概述
          characters_present: [string]  # 本场出场角色名
          content:               # 剧本内容（有序列表）
            - type: action       # 动作/场景描述
              text: string       # 描述文本

            - type: dialogue     # 对话
              character: string  # 说话人
              line: string       # 台词
              parenthetical: string  # 括号动作指示（可选）
              emotion: string    # 情绪标注（可选）
              source_line: integer   # 原文行号（可选）

            - type: transition   # 转场
              effect: string     # 转场效果（切至/淡入/淡出...）
```

---

## 设计决策说明

### 1. 三层顶层结构：`meta` / `characters` / `chapters`

**设计原因：**

- **关注点分离**：元信息、角色、内容三者的生命周期和使用场景完全不同。导演关注角色表，编剧关注章节内容，制作人关注元信息。分开存放避免信息检索时的交叉干扰。
- **角色表全局前置**：剧本制作中，角色表（Character Bible）是独立文档。将其置于顶层而非散落在各章节中，方便导演/选角导演直接检索完整角色画像，也便于后续生成角色对照表。
- **对标行业惯例**：好莱坞剧本通常包含独立的 Character List 和 Scene List，本 Schema 在数字格式中保留了这一传统。

### 2. `content` 使用 type 多态而非固定字段

**设计原因：**

剧本由三种基本元素构成：动作描述（Action）、对话（Dialogue）、转场（Transition）。这三者的字段结构差异很大：

- **action** 只需要 `text`（描述文本）
- **dialogue** 需要 `character`、`line`、`parenthetical`、`emotion` 等多个字段
- **transition** 只需要 `effect`

如果使用固定 schema（所有字段平铺，用空值表示不适用），会导致大量冗余空字段，且无法在 Schema 层面约束"dialogue 必有 character"等规则。采用 `type` 字段做多态分发，每种类型只携带必要的字段，语义清晰，校验方便。

### 3. `characters_present` 置于场景级别

**设计原因：**

在影视制作中，每场戏开拍前副导演需要确认本场演员是否到位。将出场角色直接标注在场景标题下方，是对标标准剧本格式中 "CHARACTERS" 行的做法。同时，这个字段也方便计算每个角色的总出场次数和戏份分布。

### 4. `heading` 三段式：location / time / interior

**设计原因：**

这是国际剧本格式的事实标准（Master Scene Script 格式）。场景标题统一为 `[内/外]景. 地点 - 时间` 的格式（如 "内景. 书房 - 夜"）。拆分为结构化字段而非简单字符串，是为了：

- **程序化处理**：可按时间（全部夜戏一起拍）或地点（同场景集中拍）排序，辅助拍摄计划
- **国际化**：不同语言的剧本可单独翻译各字段后重新组装

### 5. `emotion` 情绪标注

**设计原因：**

传统剧本不直接标注情绪，演员通过台词和括号指示自行理解。但 AI 辅助创作场景下，情绪标注有特殊价值：

- **降低理解门槛**：非专业编剧（小说作者）可能不擅长写表演指导，AI 标注的情绪提供参考
- **可选字段**：标注为可选，专业编剧可以忽略或修改
- **辅助配音/动画制作**：如果剧本用于有声书或动画，情绪标注可直接驱动语音合成参数

### 6. `source_line` 原文行号追溯

**设计原因：**

这是 AI 辅助创作工具的核心创新之一。传统改编中，从剧本回到原文校对需要大量检索工作。通过为每个剧本元素标注原文行号：

- 作者可一键定位原文，核验 AI 是否误改了关键情节
- 发现剧本某处有问题时，可快速找到对应原文进行修改
- 支持"原文-剧本"双向对照视图，未来可扩展为 diff 比对

### 7. `parenthetical` 括号动作指示

**设计原因：**

括号指示（如 "(低声)"、"(站起)"）是标准剧本格式中对话的一部分，用于指导演员的动作和语气。AI 从小说叙述中提取隐含的动作指示（如 "他低声说道" → `parenthetical: "(低声)"`），是对原文字面之外的语义理解，也是改编价值的体现。

### 8. `transition` 作为独立 content 类型

**设计原因：**

小说中场景切换通常以空行、分隔符或叙事转折表示，而剧本中必须明确标注转场方式。将其作为独立类型（而非场景的元数据字段），是因为：

- 转场可能出现在场景内（同一场戏中跳切）
- 保持 content 列表的线性时间顺序
- 为后续扩展转场类型（叠化/闪回/蒙太奇）留出空间

---

## 扩展性考虑

当前 Schema 是 1.0 版本，预留了以下扩展方向：

| 扩展方向 | 预留方式 |
|----------|----------|
| 分镜头标注 | `content` 中新增 `type: shot` |
| 音效/配乐 | `content` 中新增 `type: sound` |
| 角色弧线追踪 | `characters` 中新增 `arc` 字段 |
| 多版本剧本 | `meta` 中新增 `version` 字段 |
| 时间轴信息 | `scenes` 中新增 `duration_estimate` 字段 |

---

## 与行业标准的关系

本 Schema 参考了以下行业标准：

- **Final Draft (.fdx)**：好莱坞标准剧本软件的 XML 格式
- **Fountain**：纯文本剧本标记语言
- **Screenplay JSON**：开源社区的 JSON 剧本格式

选择 YAML 而非 XML 或 JSON 的原因：
- **可读性**：YAML 比 XML/JSON 更适合人类直接阅读和编辑，符合"可编辑初稿"的产品定位
- **注释支持**：YAML 原生支持注释，方便作者在剧本中做标注
- **多行文本**：YAML 的 literal block scalar (`|`) 天然适合剧本中的大段描述
