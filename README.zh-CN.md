# AI 师傅 CLI 与 Skills（中文说明）

[English README](./README.md)

安装 `shifu` CLI，即可获得 AI 师傅课程操作命令及配套的智能体 Skills，覆盖课程选题、制作部署和学习效果改进。

## 安装与更新

需要 Node.js 22.20.0+、带 `venv` 的 Python 3.11+，以及下载 npm 与 Python 依赖所需的网络。安装入口参考 [lark-cli 的做法](https://github.com/larksuite/cli)：先安装 CLI，再同步安装配套 Skills。

```bash
npx @ai-shifu/cli@latest install
shifu --version
shifu skills list
```

安装过程会配置全局 `shifu` 命令、准备隔离的 Python 运行环境，并把全部三个业务 Skills 安装到共享的 `~/.agents/skills` 及检测到的常见智能体目录。Skills 与 CLI 来自同一个 npm 安装包。推荐的 `npx … install` 入口会显式完成配置。直接运行 `npm install --global @ai-shifu/cli` 时，只有启用生命周期脚本才会自动配置；包管理器跳过脚本时，执行 `shifu setup` 即可。安装后重启或刷新智能体以加载新 Skills。

```bash
shifu update
shifu setup
shifu skills install
shifu skills install --agent codex
```

`update` 一起升级 CLI 和配套 Skills。`setup` 完整配置运行环境和 Skills；只需修复 Skill 安装或为后来新增的智能体安装时，运行 `skills install`。省略 `--agent` 时使用共享目录及检测到的常见智能体。安装 Skills 不会登录 AI 师傅账号。

当前 npm 包尚未发布；首次发布后，上面的 `npx` 入口才可使用。维护者可以从当前源码测试安装包：

```bash
npm install --ignore-scripts
npm test
npm pack
npm install --global ./ai-shifu-cli-VERSION.tgz
shifu setup --agent codex
```

把 `VERSION` 替换为 `npm pack` 输出的文件名中的版本号。本地依赖安装不会安装用户 Skills；显式执行 `setup` 也适用于 npm 跳过安装脚本的情况。[CLI 发布工作流](.github/workflows/cli-publish.yml) 在显式触发并提供所需 npm 发布凭证后，将经过校验的 Release 标签发布到 npm。

## 开始使用 CLI

```bash
shifu --help
shifu site --set cn
shifu login
shifu verify
shifu list
```

按实际账号选择 `cn`、`com` 或自有服务地址；多账号配置和命令详见 [CLI 参考](skills/ai-shifu-course-creator/references/cli/cli-reference.md)。配置与浏览器授权凭证继续保存在 AI 师傅用户配置目录中。npm 入口从该目录的 `cli.env` 读取可选环境配置；旧 Skill 的 Python 入口仍兼容自己的 `.env`。

同步 Skills 时，旧 `.env` 会备份到用户配置目录的 `legacy-env/`，配置一致时迁移到 `cli.env`；已有 `cli.env` 会保留。若多份旧配置不同且尚无 `cli.env`，配置过程会停止，待选择其中一份后再重试。

## 包含的 Skills

- **AI-Shifu Course Creator（AI 师傅课程创作器）**：按教学设计、MarkdownFlow 表达、CLI 操作三类提供课程创作、编辑、审查、发布、管理和分析能力，由智能体按任务自主选择与组合。
- **AI-Shifu Learning Report（AI 师傅学习报告）**：分析单门 AI 师傅课程，为教学管理者和老师生成脱敏的 `course-learning-report.json`，以及美观、自包含、可打印的 `course-learning-report.html`。
- **Course Direction Advisor（课程选题顾问）**：将素材转化为基于证据的、市场适配的课程选题决策，包含竞品分析、定价建议和 GO/HOLD/REWORK/NO-GO 推荐。

## 仓库结构

```text
cli/
skills/
  ai-shifu-course-creator/
  ai-shifu-learning-report/
  course-direction-advisor/
tools/
  ai-shifu-skill-release/
  ai-shifu-workbuddy-publisher/
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

[WorkBuddy 上传 Skill](tools/ai-shifu-workbuddy-publisher/SKILL.md) 用于下载并校验已发布的 WorkBuddy 安装包，通过已登录的浏览器更新现有 AI师傅专家，并核实提交审核的结果。默认获取最新正式 Release；同版本已发布或正在审核时，跳过重复提交。

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
| 创建一门完整课程 | 自主组合设计、表达与 CLI 构建、导入、发布能力 | 自动上传，默认交付经核验的已发布课程 |
| 部署已有课程目录 | CLI 构建、payload 检查、导入及所需发布操作 | 用户要求的平台结果及核验 |
| 修改或管理已有课程 | CLI 同步或指定管理操作 | 对已有课程的经核验改动 |
| 分析学习、订单或积分数据 | CLI 分析及隐私、可读性处理 | 基于实际课程数据的答案 |

只交付任务需要的产物。分段记录、课程索引、全局变量表和固定风险报告都不是所有任务的必需结果。完整创作的课程包含课节内容、Course Prompt、简介和结构。单项请求只修改指定产物；涉及新建或已有平台课程的变化仍会自动同步。

新建课程和已有课程的修改都遵循[自动更新到平台的规则](skills/ai-shifu-course-creator/SKILL.md#automatic-platform-updates)，不等待本地确认或单独的上传指令。完整建课仍[默认发布](skills/ai-shifu-course-creator/SKILL.md#full-course-creation-outcome)。用户明确要求本地交付或不发布的草稿时，按该范围完成。已有成果可以直接使用对应的[构建与导入](skills/ai-shifu-course-creator/references/build-and-import.md)、[同步](skills/ai-shifu-course-creator/references/course-sync.md)或[管理](skills/ai-shifu-course-creator/references/course-management.md)能力。

课程创作器 CLI 的使用统计可能关联当前账号。设置 `SHIFU_DISABLE_ANALYTICS=1` 可关闭；详见[配置说明](skills/ai-shifu-course-creator/.env.example)。

## 校验

```bash
python3 scripts/validate_skill_quality.py
npm test
npm run check-version
```

## AI 师傅

本技能套件是 AI 师傅课程创作工作流的一部分：<https://ai-shifu.cn>
