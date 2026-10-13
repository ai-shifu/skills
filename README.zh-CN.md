# AI 师傅 Skills（中文说明）

[English README](./README.md)

本仓库包含可复用的 AI 师傅 skills，覆盖课程选题、制作部署和学习效果改进。

## 包含的 Skills

- **AI-Shifu Course Creator（AI 师傅课程创作器）**：按教学设计、MarkdownFlow 表达、CLI 操作三类提供课程创作、编辑、审查、发布、管理和分析能力，由智能体按任务自主选择与组合。
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

[AI-Shifu Skill Release 工具](tools/ai-shifu-skill-release/README.md) 用于构建和校验 ClawHub、腾讯 SkillHub、WorkBuddy 与豆包渠道包，并提供已有的发布流程。实现已从 `ai-shifu/ai-shifu-skill-release`（本地 `ai-shifu-skill-build` 项目）迁入本仓库维护。

构建需要 Python 3.11+ 和 Git。源码仍取自 GitHub `ai-shifu/skills` 远端 `main` 的已提交内容，本地 Skill 修改不会进入产物。从仓库根目录执行：

```bash
cd tools/ai-shifu-skill-release
python3 scripts/release.py build --skill-name ai-shifu-course-creator
python3 scripts/release.py verify dist/<release-id>
```

校验时使用 `build` 实际输出的发布目录。构建与校验不会上传；`release.toml` 发布配置、各渠道依赖和发布命令见工具目录的英文 README。维护者可读取[发布 Skill](tools/ai-shifu-skill-release/SKILL.md)，它与上方三个业务 Skill 分开维护。工程说明使用英文，渠道包内的中文提示词与展示文案保持原样。

## 学习报告路径

课程产生学习数据后，如需复盘单门课程并形成改进动作，使用 **AI-Shifu Learning Report**。它复用课程制作 skill 已认证的分析能力，再将汇总后的学习进度、课节健康度、参与信号、学员画像和受审计追问转化为：

- 带版本、指标口径和数据质量说明的脱敏 JSON 数据文件；
- 首屏先呈现管理结论、无需外部资源且可直接打印为 PDF 的 HTML 报告；
- 三至五条带证据、置信度和验证方法的教学建议。

报告不会暴露学员身份、原始课程标识或追问原文。经营与积分数据默认不进入报告，只有用户明确要求时才加入可选附录。报告默认使用简体中文；只有用户明确要求英文时才切换为英文。

## 使用说明

skill 以 `SKILL.md` 作为行为定义。按照 [Agent Skills](https://agentskills.io/specification) 标准，`name` frontmatter 字段必须与目录名一致，只允许小写字母、数字和连字符。该格式最初由 Anthropic 开发并作为开放标准发布，[Claude Code 官方文档](https://code.claude.com/docs/en/skills)声明其 skill 遵循这一标准。Claude Code 自身的实现更宽松，把 `name` 当作可选的展示标签；本仓库采用标准中更严格的规则，以保证 skill 在所有兼容 Agent Skills 的 agent 中都能正常使用。面向人的展示名维护在上方的 skill 列表中。

## 课程能力与指令示例

[课程创作器](skills/ai-shifu-course-creator/SKILL.md#capabilities) 按教学设计、MarkdownFlow 表达、CLI 操作三类提供可独立使用的能力。智能体根据请求和已有素材选择组合与顺序；主题、现成 Prompt 或课程目录都可以作为相关工作的起点。

| 用户请求 | 可用能力 | 交付结果 |
| --- | --- | --- |
| 设计一节课或规划课程结构 | 教学设计与来源分析 | 教学方案或章节、课节结构 |
| 根据素材写一节课 | MarkdownFlow 表达，按需补充教学选择 | 可运行的 Teaching Prompt |
| 先写课程简介 | 课程定位与简介撰写 | 面向学员的课程简介 |
| 审查现成 Prompt | 指定范围内的教学质量或 MarkdownFlow 检查 | 问题与用户要求的修复 |
| 创建一门完整课程 | 自主组合设计、表达与 CLI 构建、导入、发布能力 | 确认完成稿后，默认交付经核验的已发布课程 |
| 部署已有课程目录 | CLI 构建、payload 检查、导入及所需发布操作 | 用户要求的平台结果及核验 |
| 修改或管理已有课程 | CLI 同步或指定管理操作 | 对已有课程的经核验改动 |
| 分析学习、订单或积分数据 | CLI 分析及隐私、可读性处理 | 基于实际课程数据的答案 |

只交付任务需要的产物。分段记录、课程索引、全局变量表和固定风险报告都不是所有任务的必需结果。完整创作的课程包含课节内容、Course Prompt、简介和结构；单项请求可以在完成所需产物后结束。

完整建课遵循[默认发布及完成稿确认规则](skills/ai-shifu-course-creator/SKILL.md#full-course-creation-outcome)。用户明确要求本地交付或不发布的草稿时，按该范围完成。已有成果可以直接使用对应的[构建与导入](skills/ai-shifu-course-creator/references/course-build-and-import.md)、[同步](skills/ai-shifu-course-creator/references/course-sync.md)或[管理](skills/ai-shifu-course-creator/references/course-management.md)能力。

## 元数据校验

```bash
python3 scripts/validate_skill_quality.py
```

## AI 师傅

本技能套件是 AI 师傅课程创作工作流的一部分：<https://ai-shifu.cn>
