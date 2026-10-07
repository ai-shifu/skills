# AI 师傅 Skills（中文说明）

[English README](./README.md)

本仓库包含可复用的 AI 师傅 skills，覆盖课程选题、制作部署和学习效果改进。

## 包含的 Skills

- **AI-Shifu Course Creator（AI 师傅课程创作器）**：通过五阶段流水线（分段、编排、生成、优化、部署）将原始课程素材转换为优化后的可运行 MarkdownFlow 授课脚本，并部署为 AI 师傅平台上的在线课程。
- **AI-Shifu Learning Report（AI 师傅学习报告）**：分析单门 AI 师傅课程，为教学管理者和老师生成脱敏的 `course-learning-report.json`，以及美观、自包含、可打印的 `course-learning-report.html`。
- **Course Direction Advisor（课程选题顾问）**：将素材转化为基于证据的、市场适配的课程选题决策，包含竞品分析、定价建议和 GO/HOLD/REWORK/NO-GO 推荐。

## 仓库结构

```text
skills/
  ai-shifu-course-creator/
  ai-shifu-learning-report/
  course-direction-advisor/
tools/
  ai-shifu-skill-release/
```

## 构建与发布工具

[AI-Shifu Skill Release 工具](tools/ai-shifu-skill-release/README.md) 用于构建和校验 ClawHub、腾讯 SkillHub、WorkBuddy、QClaw 与豆包渠道包，并提供已有的发布流程。实现已从 `ai-shifu/ai-shifu-skill-release`（本地 `ai-shifu-skill-build` 项目）迁入本仓库维护。

构建需要 Python 3.11+ 和 Git。源码仍取自 GitHub `ai-shifu/skills` 远端 `main` 的已提交内容，本地 Skill 修改不会进入产物。从仓库根目录执行：

```bash
cd tools/ai-shifu-skill-release
python3 scripts/release.py build --skill-name ai-shifu-course-creator
python3 scripts/release.py verify dist/<release-id>
```

校验时使用 `build` 实际输出的发布目录。构建与校验不会上传；发布者配置、各渠道依赖和发布命令见工具目录的英文 README。维护者可读取[发布 Skill](tools/ai-shifu-skill-release/SKILL.md)，它与上方三个业务 Skill 分开维护。工程说明使用英文，渠道包内的中文提示词与展示文案保持原样。

## 学习报告路径

课程产生学习数据后，如需复盘单门课程并形成改进动作，使用 **AI-Shifu Learning Report**。它复用课程制作 skill 已认证的分析流程，再将汇总后的学习进度、课节健康度、参与信号、学员画像和受审计追问转化为：

- 带版本、指标口径和数据质量说明的脱敏 JSON 数据文件；
- 首屏先呈现管理结论、无需外部资源且可直接打印为 PDF 的 HTML 报告；
- 三至五条带证据、置信度和验证方法的教学建议。

报告不会暴露学员身份、原始课程标识或追问原文。经营与积分数据默认不进入报告，只有用户明确要求时才加入可选附录。
报告默认使用简体中文；只有用户明确要求英文时才切换为英文。

## 使用说明

skill 以 `SKILL.md` 作为行为定义。按照 [Agent Skills](https://agentskills.io/specification) 标准，`name` frontmatter 字段必须与目录名一致，只允许小写字母、数字和连字符。该格式最初由 Anthropic 开发并作为开放标准发布，[Claude Code 官方文档](https://code.claude.com/docs/en/skills)声明其 skill 遵循这一标准。Claude Code 自身的实现更宽松，把 `name` 当作可选的展示标签；本仓库采用标准中更严格的规则，以保证 skill 在所有兼容 Agent Skills 的 agent 中都能正常使用。面向人的展示名维护在上方的 skill 列表中。

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

### 路径 B：单项创作步骤

适合只需要某一个创作步骤、而不是完整做课的场景：

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

## AI 师傅

本技能套件是 AI 师傅课程创作工作流的一部分：<https://ai-shifu.cn>
