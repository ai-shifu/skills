# AI 师傅 Skills（中文说明）

[English README](./README.md)

本仓库包含可复用的 AI 师傅 skills，覆盖从课程选题到部署的全流程。

## 包含的 Skills

- `ai-shifu-course-creator`：通过五阶段流水线（分段、编排、生成、优化、部署）将原始课程素材转换为优化后的可运行 MarkdownFlow 授课脚本，并部署为 AI 师傅平台上的在线课程。
- `course-direction-advisor`：将素材转化为基于证据的、市场适配的课程选题决策，包含竞品分析、定价建议和 GO/HOLD/REWORK/NO-GO 推荐。

course-creator skill 有可运行示例，位于 `skills/ai-shifu-course-creator/examples/`。

## 仓库结构

```text
skills/
  ai-shifu-course-creator/
  course-direction-advisor/
```

## 使用说明

skill 以 `SKILL.md` 作为行为定义。
机器可读元数据位于 `skills/ai-shifu-course-creator/skill.yaml`。

## 课程生产与部署路径

按控制粒度选择其一：

### 路径 A：端到端（推荐）

适合希望从原始素材快速得到在线课程的场景。

1. 准备素材（逐字稿或课程文档）。
2. 运行 Phase 1–4 生成优化后的 MarkdownFlow 课节脚本。
3. 运行 Phase 5 构建、导入并发布到 AI 师傅平台。

预期产物：

- 结构化分段
- 分课节 MarkdownFlow 脚本
- 课程索引与全局变量表
- 优化后脚本与风险报告
- AI 师傅平台上的在线课程

### 路径 B：仅创作

适合只需要优化后 MarkdownFlow 脚本而不部署的场景。子路径：

- **仅分段**：Phase 1 生成语义分段供人工审核。
- **仅生成**：Phase 3 基于已有分段生成课节脚本。
- **仅优化**：Phase 4 审计并改进现有脚本。

### 路径 C：仅部署

适合已有 MarkdownFlow 文件需要部署的场景：

1. 将 MarkdownFlow 文件组织到课程目录中。
2. 运行 `build --course-dir ./course-a/` 生成导入文件。
3. 运行 `import --new --json-file ./course-a/shifu-import.json` 创建课程。
4. 运行 `publish <shifu_bid>` 发布上线。

### 路径 D：管理已有课程

使用管理命令（list/show/update/rename/reorder/delete/publish/archive）操作平台上已有的课程。

## 元数据校验

```bash
python3 scripts/validate_skill_quality.py
```

## 语言策略（面向使用者）

这些 skills 支持多语言课程生成，语言决策规则如下：

- 你明确指定输出语言时，优先使用该语言。
- 你提供 `target_language` 时，在没有更强显式指令的情况下按其输出。
- 若未提供上述信息，系统会参考会话偏好和提问语言信号。
- 若仍无法判定，回退到 `en-US`。
- 需要双语输出时，设置 `bilingual_output: true`。

建议使用以下控制项提升可预期性：

- `target_language`（例如 `zh-CN`、`fr-FR`、`ja-JP`）
- `bilingual_output`（`true|false`）
- `term_policy`（`preserve|translate|mixed`）
- `quote_policy`（`translate_only|original_plus_translation`）

## AI 师傅

本技能套件是 AI 师傅课程创作工作流的一部分：<https://ai-shifu.com>
