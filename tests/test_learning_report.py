from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "ai-shifu-learning-report"
EVALS_PATH = SKILL_DIR / "evals" / "evals.json"
RENDERER_PATH = SKILL_DIR / "scripts" / "render_report.py"
SCHEMA_PATH = SKILL_DIR / "references" / "report-data.schema.json"
SKILL_PATH = SKILL_DIR / "SKILL.md"
DATA_COLLECTION_PATH = SKILL_DIR / "references" / "data-collection-and-privacy.md"
ANALYSIS_GUIDELINES_PATH = SKILL_DIR / "references" / "analysis-guidelines.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cumulative_period() -> dict:
    return {
        "mode": "cumulative_to_date",
        "label": "累计至 2026-07-31",
        "start": None,
        "end": "2026-07-31",
    }


def report_metric(
    *,
    key: str = "learners_started",
    label: str = "开始学习人数",
    value: int | float | str | None = 120,
    unit: str = "人",
    data_quality: str = "observed",
    definition: str = "累计开始课程的去重学习者数。",
    source_notes: list[str] | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "definition": definition,
        "time_scope": cumulative_period(),
        "data_quality": data_quality,
        "is_approximate": False,
        "source_notes": source_notes or ["合成数据，仅用于测试。"],
    }


def minimal_valid_report() -> dict:
    recommendations = []
    for index in range(1, 4):
        recommendations.append(
            {
                "title": f"建议 {index}",
                "priority": "medium",
                "observation": "累计有 120 名学习者开始课程。",
                "interpretation": "当前覆盖面可作为下一轮教学验证的基线。",
                "confidence": "medium",
                "action": "保持当前课程入口，并观察下一批学习者的变化。",
                "validation": "新增 30 名学习者后比较开始学习人数和课节触达。",
                "evidence": ["learners_started"],
            }
        )

    return {
        "schema_version": "1.0",
        "meta": {
            "course_title": "新经理的高质量一对一",
            "generated_at": "2026-08-04T10:00:00+08:00",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "source_kind": "synthetic",
            "period": cumulative_period(),
            "brand": {
                "organization_name": "示例学习中心",
                "accent_color": "#5B5CE2",
                "logo_text": "AI 师傅",
            },
        },
        "metric_definitions": {
            "learners_started": {
                "label": "开始学习人数",
                "definition": "累计开始课程的去重学习者数。",
                "unit": "人",
                "source_notes": ["合成数据，仅用于测试。"],
            },
            "course_completion_proxy": {
                "label": "课程完成率",
                "definition": "同一批开始学习者中完成全部必修路径的去重学习者比例。",
                "unit": "%",
                "source_notes": ["必修路径尚不可靠，因此本指标不可用。"],
            }
        },
        "overview": {
            "executive_summary": {
                "overall_health": "样本完整，可作为教学迭代基线。",
                "conclusions": ["累计有 120 名学习者开始课程。"],
                "critical_limitations": ["该报告使用合成数据。"],
            },
            "kpis": [
                report_metric(),
                report_metric(
                    key="course_completion_proxy",
                    label="课程完成率",
                    value=None,
                    unit="%",
                    data_quality="unavailable",
                    definition="同一批开始学习者中完成全部必修路径的去重学习者比例。",
                    source_notes=["必修路径尚不可靠，因此本指标不可用。"],
                ),
            ],
            "learning_path": [],
        },
        "lesson_health": [],
        "engagement": {
            "follow_up_analysis": {
                "status": "available",
                "sample_size": 0,
                "sample_limit": 100,
                "audited_access": True,
                "sampling_rule": "截至报告时间的最近受审计追问",
                "effective_span": None,
                "themes": [],
            },
            "ratings": [],
            "learning_modes": [],
            "activity": [],
        },
        "audience": {
            "status": "unavailable",
            "dimensions": [],
            "note": "没有可用的变量名称映射。",
        },
        "recommendations": recommendations,
        "data_quality": {
            "overall_status": "partial",
            "coverage_notes": ["核心开始学习人数可用。"],
            "unavailable_metrics": [
                {
                    "key": "course_completion_proxy",
                    "label": "课程完成率",
                    "reason": "必修路径尚不可靠。",
                }
            ],
            "limitations": ["该报告使用合成数据。"],
            "privacy_notes": ["最终报告只包含聚合数据。"],
        },
    }


class LearningReportCatalogTests(unittest.TestCase):
    def test_catalogs_register_three_skills_and_human_display_name(self):
        index = (REPO_ROOT / "INDEX.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        display_name = "AI-Shifu Learning Report（AI 师傅学习报告）"

        self.assertIn("Total skills: **3**", index)
        self.assertIn(display_name, index)
        self.assertIn(display_name, readme)
        self.assertIn(display_name, readme_zh)

    def test_learning_report_docs_do_not_use_forbidden_abbreviation(self):
        paths = [
            REPO_ROOT / "INDEX.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "README.zh-CN.md",
            EVALS_PATH,
            *sorted((SKILL_DIR / "evals" / "files").glob("*.json")),
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(
                    re.search(r"\bMDF\b", path.read_text(encoding="utf-8"))
                )

    def test_skill_requires_current_published_visible_lesson_scope(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        collection = DATA_COLLECTION_PATH.read_text(encoding="utf-8")
        analysis = ANALYSIS_GUIDELINES_PATH.read_text(encoding="utf-8")

        self.assertIn("current published outline", skill)
        self.assertIn("published, visible teaching leaf lessons", skill)
        self.assertIn("Published Visible Lesson Gate", collection)
        self.assertIn("Exclude hidden lessons", collection)
        self.assertIn("Learners observed only on excluded lessons", collection)
        self.assertIn("Do not replace it with final-lesson reach", collection)
        self.assertIn("Omit hidden, unpublished, draft-only", analysis)

    def test_completion_rate_uses_same_cohort_without_fixed_maturation_window(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        collection = DATA_COLLECTION_PATH.read_text(encoding="utf-8")
        analysis = ANALYSIS_GUIDELINES_PATH.read_text(encoding="utf-8")

        self.assertIn("one consistent learner cohort", skill)
        self.assertIn("Do not impose a fixed 30-day", skill)
        self.assertIn("same-cohort distinct learners", collection)
        self.assertIn("first entered during that period", collection)
        self.assertIn("Learners who start near the cutoff remain", collection)
        self.assertIn("every required lesson or one valid required branch path", analysis)
        self.assertIn("keep late starters in the denominator", analysis)


class LearningReportEvaluationFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_json(EVALS_PATH)
        cls.evals = cls.manifest["evals"]
        cls.fixtures = {
            Path(eval_case["files"][0]).stem: load_json(
                SKILL_DIR / eval_case["files"][0]
            )
            for eval_case in cls.evals
        }

    def test_eval_manifest_covers_three_required_scenarios(self):
        self.assertEqual("ai-shifu-learning-report", self.manifest["skill_name"])
        self.assertEqual(
            {
                "healthy-complete-course",
                "conflicting-bottleneck-signals",
                "sparse-new-course-with-privacy-traps",
            },
            {Path(eval_case["files"][0]).stem for eval_case in self.evals},
        )

        for eval_case in self.evals:
            with self.subTest(eval_case=eval_case["id"]):
                self.assertEqual(
                    {"id", "prompt", "expected_output", "files", "expectations"},
                    set(eval_case),
                )
                self.assertIn("course-learning-report.json", eval_case["prompt"])
                self.assertIn("course-learning-report.html", eval_case["prompt"])
                self.assertGreaterEqual(len(eval_case["expectations"]), 7)
                self.assertEqual(1, len(eval_case["files"]))
                self.assertTrue((SKILL_DIR / eval_case["files"][0]).is_file())

    def test_all_fixtures_are_single_course_cumulative_synthetic_inputs(self):
        for name, fixture in self.fixtures.items():
            with self.subTest(fixture=name):
                self.assertTrue(fixture["synthetic"])
                self.assertEqual(
                    "cumulative_to_date",
                    fixture["request_context"]["report_period"]["mode"],
                )
                self.assertFalse(fixture["request_context"]["include_operations"])
                self.assertLessEqual(
                    fixture["analytics"]["audited_follow_ups"]["requested_limit"],
                    100,
                )
                self.assertIsInstance(fixture["course"]["title"], str)

    def test_healthy_fixture_has_exact_same_cohort_completion_rate(self):
        fixture = self.fixtures["healthy-complete-course"]
        progress = fixture["analytics"]["progress"]
        lesson_scope = fixture["course"]["lesson_scope"]

        self.assertTrue(fixture["course"]["completion_rule"]["eligible"])
        self.assertEqual(120, progress["learners_started"])
        self.assertEqual(100, progress["last_required_lesson_reached"])
        self.assertEqual(96, progress["last_required_lesson_completed"])
        self.assertEqual(96, progress["required_path_completed"])
        completion = fixture["course"]["completion_rule"]
        self.assertEqual(
            "all_published_visible_required_lessons",
            completion["completion_requirement"],
        )
        self.assertIsNone(completion["fixed_maturation_window_days"])
        self.assertIn("同一批学员", completion["numerator_definition"])
        self.assertEqual(
            [120, 114, 108, 100],
            [item["learners_reached"] for item in progress["lesson_reach"]],
        )
        self.assertEqual(
            ["L1", "L2", "L3", "L4"], lesson_scope["eligible_lesson_keys"]
        )
        excluded = {item["lesson_key"]: item for item in lesson_scope["excluded_lessons"]}
        self.assertTrue(excluded["LH"]["hidden"])
        self.assertEqual("draft", excluded["LD"]["publication_status"])
        self.assertEqual(
            {"LH", "LD"},
            {item["lesson_key"] for item in progress["excluded_lesson_records"]},
        )
        self.assertGreater(
            max(item["learners_reached"] for item in progress["excluded_lesson_records"]),
            progress["learners_started"],
        )

    def test_conflicting_fixture_preserves_positive_and_negative_signals(self):
        fixture = self.fixtures["conflicting-bottleneck-signals"]
        analytics = fixture["analytics"]
        reach = {
            item["lesson_key"]: item["learners_reached"]
            for item in analytics["progress"]["lesson_reach"]
        }
        ratings = {
            item["lesson_key"]: item["average"]
            for item in analytics["lesson_ratings"]["items"]
        }

        self.assertEqual(83, reach["L2"])
        self.assertEqual(47, reach["L3"])
        self.assertEqual(45, reach["L4"])
        self.assertEqual(3.0, ratings["L3"])
        self.assertEqual(4.7, ratings["L4"])
        l3_mode = next(
            item
            for item in analytics["learning_mode"]["lesson_feedback_mode"]["items"]
            if item["lesson_key"] == "L3"
        )
        self.assertEqual(15, l3_mode["listening"])
        self.assertEqual(19, l3_mode["response_count"])

    def test_sparse_fixture_contains_deliberate_source_only_privacy_traps(self):
        fixture = self.fixtures["sparse-new-course-with-privacy-traps"]
        analytics = fixture["analytics"]
        follow_ups = analytics["audited_follow_ups"]
        source_text = json.dumps(fixture, ensure_ascii=False)

        self.assertFalse(fixture["course"]["completion_rule"]["eligible"])
        self.assertIsNone(analytics["progress"]["last_required_lesson_reached"])
        self.assertFalse(
            analytics["audience_variables"]["variable_name_mapping_available"]
        )
        self.assertIn("operations_source_available_but_not_requested", analytics)
        self.assertGreaterEqual(len(follow_ups["forbidden_output_literals"]), 10)
        for literal in follow_ups["forbidden_output_literals"]:
            with self.subTest(literal=literal):
                self.assertIn(literal, source_text)


class LearningReportSchemaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)

    def test_schema_locks_required_top_level_sections_and_version(self):
        self.assertEqual("1.0", self.schema["properties"]["schema_version"]["const"])
        self.assertEqual(
            {
                "schema_version",
                "meta",
                "metric_definitions",
                "overview",
                "lesson_health",
                "engagement",
                "audience",
                "recommendations",
                "data_quality",
            },
            set(self.schema["required"]),
        )
        self.assertFalse(self.schema["additionalProperties"])

    def test_metric_contract_requires_provenance_scope_and_quality(self):
        metric = self.schema["$defs"]["metric"]
        required = set(metric["required"])

        self.assertTrue(
            {
                "value",
                "unit",
                "definition",
                "time_scope",
                "data_quality",
                "is_approximate",
                "source_notes",
            }.issubset(required)
        )
        self.assertNotIn("note", required)
        self.assertIn("null", metric["properties"]["value"]["type"])
        self.assertIn(
            "unavailable", metric["properties"]["data_quality"]["enum"]
        )

    def test_schema_enforces_recommendation_and_operations_boundaries(self):
        recommendations = self.schema["properties"]["recommendations"]
        recommendation = self.schema["$defs"]["recommendation"]

        self.assertEqual(3, recommendations["minItems"])
        self.assertEqual(5, recommendations["maxItems"])
        self.assertTrue(
            {
                "observation",
                "interpretation",
                "confidence",
                "action",
                "validation",
                "evidence",
            }.issubset(recommendation["required"])
        )
        self.assertTrue(
            self.schema["$defs"]["operations"]["properties"][
                "requested_by_user"
            ]["const"]
        )


class LearningReportRendererTests(unittest.TestCase):
    def invoke_renderer(
        self, report: dict, *, validate_only: bool = False
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "course-learning-report.json"
            output_path = Path(tmpdir) / "course-learning-report.html"
            input_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            command = [
                sys.executable,
                str(RENDERER_PATH),
                "--input",
                str(input_path),
            ]
            if validate_only:
                command.append("--validate-only")
            else:
                command.extend(["--output", str(output_path)])

            result = subprocess.run(
                command,
                cwd=SKILL_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            html = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            return result, html

    def assert_renderer_succeeds(
        self, report: dict, *, validate_only: bool = False
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        result, html = self.invoke_renderer(report, validate_only=validate_only)
        self.assertEqual(
            0,
            result.returncode,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result, html

    def test_validate_only_accepts_minimal_schema_version_1_report(self):
        result, html = self.assert_renderer_succeeds(
            minimal_valid_report(), validate_only=True
        )

        self.assertIn("Valid report data", result.stdout)
        self.assertEqual("", html)

    def test_validation_rejects_missing_required_section(self):
        report = minimal_valid_report()
        del report["audience"]

        result, html = self.invoke_renderer(report, validate_only=True)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("audience", result.stderr)
        self.assertEqual("", html)

    def test_renderer_outputs_self_contained_responsive_printable_accessible_html(self):
        report = minimal_valid_report()
        _, html = self.assert_renderer_succeeds(report)

        self.assertIn('<html lang="zh-CN">', html)
        self.assertIn('name="viewport"', html)
        self.assertIn("<style>", html)
        self.assertIn("@media print", html)
        self.assertRegex(html, r"@media\s*\([^)]*max-width")
        self.assertIn("<main", html)
        self.assertRegex(html, r"aria-(?:label|labelledby)=")
        self.assertNotRegex(
            html,
            r"<(?:link|script|img)\b[^>]*(?:src|href)=[\"']https?://",
        )
        self.assertNotIn("经营与积分附录", html)
        self.assertIn("新经理的高质量一对一", html)
        self.assertIn("120", html)
        self.assertNotIn("learners_started", html)
        self.assertIn("开始学习人数：120人", html)
        self.assertNotIn("2026-08-04T10:00:00+08:00", html)
        self.assertIn("2026年8月4日 10:00", html)
        self.assertRegex(
            html,
            r'<section class="section" aria-labelledby="path-heading">.*?<h2 id="path-heading">',
        )

    def test_renderer_uses_swiss_international_visual_system(self):
        _, html = self.assert_renderer_succeeds(minimal_valid_report())

        self.assertIn('name="design-system" content="Swiss International Style"', html)
        self.assertIn('grid-template-columns: repeat(12, minmax(0, 1fr))', html)
        self.assertIn('font-family: "Helvetica Neue", Helvetica, Arial', html)
        self.assertIn('--accent: #5B5CE2', html)
        self.assertNotIn('border-radius:', html)
        self.assertNotIn('box-shadow:', html)
        self.assertNotIn('linear-gradient', html)

    def test_renderer_escapes_report_text_before_interpolation(self):
        report = minimal_valid_report()
        report["meta"]["course_title"] = '<b>管理复盘</b> & "试验"'

        _, html = self.assert_renderer_succeeds(report)

        self.assertNotIn("<b>管理复盘</b>", html)
        self.assertIn("&lt;b&gt;管理复盘&lt;/b&gt;", html)
        self.assertIn("&amp;", html)

    def test_template_placeholders_in_report_data_are_not_recursively_expanded(self):
        report = minimal_valid_report()
        report["meta"]["course_title"] = "{{REPORT_BODY}}"

        _, html = self.assert_renderer_succeeds(report)

        self.assertEqual(1, html.count('class="section summary-band"'))
        self.assertIn("<h1 id=\"report-title\">{{REPORT_BODY}}</h1>", html)

    def test_optional_or_low_contrast_brand_uses_safe_defaults(self):
        without_brand = minimal_valid_report()
        del without_brand["meta"]["brand"]
        _, default_html = self.assert_renderer_succeeds(without_brand)
        self.assertIn("AI 师傅", default_html)

        low_contrast = minimal_valid_report()
        low_contrast["meta"]["brand"]["accent_color"] = "#FFFFFF"
        _, fallback_html = self.assert_renderer_succeeds(low_contrast)
        self.assertIn("--accent: #D6001C", fallback_html)
        self.assertNotIn("--accent: #FFFFFF", fallback_html)

    def test_completion_rate_uses_direct_reader_facing_name_and_exact_fraction(self):
        report = minimal_valid_report()
        metric = report["overview"]["kpis"][1]
        metric.update(
            {
                "value": 80,
                "data_quality": "approximate",
                "is_approximate": True,
                "numerator": 96,
                "denominator": 120,
                "source_notes": ["按同一批学员完成全部必修路径的状态计算。"],
            }
        )
        report["data_quality"]["unavailable_metrics"] = []

        _, html = self.assert_renderer_succeeds(report)

        self.assertIn("96 / 120", html)
        self.assertIn("完成人数 / 开始学习人数", html)
        self.assertIn("课程完成率", html)
        self.assertIn("按必修课完成状态计算", html)
        self.assertIn("按同一批学员完成全部必修路径的状态计算", html)
        self.assertNotIn("课程完成率代理", html)
        self.assertNotIn("课程完成率（近似）", html)
        self.assertNotRegex(html, r"80%\s*<span class=\"approx-tag\"")

        activity_metric = report_metric(
            key="active_share",
            label="活跃占比",
            value=85,
            unit="%",
            data_quality="derived",
        )
        activity_metric.update({"numerator": 102, "denominator": 120})
        report["metric_definitions"]["active_share"] = {
            "label": activity_metric["label"],
            "definition": activity_metric["definition"],
            "unit": activity_metric["unit"],
            "source_notes": activity_metric["source_notes"],
        }
        report["overview"]["kpis"].append(activity_metric)
        _, html = self.assert_renderer_succeeds(report)
        self.assertIn("计算分子 / 分母：102 / 120", html)

    def test_legacy_completion_label_is_normalized_when_rendered(self):
        report = minimal_valid_report()
        report["metric_definitions"]["course_completion_proxy"]["label"] = (
            "课程完成率代理"
        )
        report["overview"]["kpis"][1]["label"] = "课程完成率代理"
        report["data_quality"]["unavailable_metrics"][0]["label"] = (
            "课程完成率代理"
        )

        _, html = self.assert_renderer_succeeds(report)

        self.assertIn("课程完成率", html)
        self.assertNotIn("课程完成率代理", html)

    def test_successful_zero_follow_up_query_has_observed_zero_state(self):
        _, html = self.assert_renderer_succeeds(minimal_valid_report())

        self.assertIn("查询成功：最近受审计样本中没有追问", html)

    def test_renderer_shows_null_metric_as_unavailable_not_zero(self):
        report = minimal_valid_report()
        report["metric_definitions"]["learning_duration"] = {
            "label": "学习时长",
            "definition": "可靠的累计学习时长。",
            "unit": "分钟",
            "source_notes": ["当前分析源不提供可靠时长。"],
        }
        report["overview"]["kpis"].append(
            report_metric(
                key="learning_duration",
                label="学习时长",
                value=None,
                unit="分钟",
                data_quality="unavailable",
                definition="可靠的累计学习时长。",
                source_notes=["当前分析源不提供可靠时长。"],
            )
        )
        report["data_quality"]["unavailable_metrics"].append(
            {
                "key": "learning_duration",
                "label": "学习时长",
                "reason": "当前分析源不提供可靠时长。",
            }
        )

        _, html = self.assert_renderer_succeeds(report)

        self.assertIn("学习时长", html)
        self.assertRegex(html, r"(?:数据不可用|不可用|暂无数据|未提供)")
        self.assertNotRegex(html, r"学习时长[^<]{0,40}>?\s*0(?:\.0+)?\s*分钟")

    def test_validator_rejects_inconsistent_theme_and_audience_shares(self):
        report = minimal_valid_report()
        report["engagement"]["follow_up_analysis"].update(
            {
                "sample_size": 10,
                "themes": [
                    {
                        "theme": "实践示例",
                        "count": 1,
                        "share": 0.9,
                        "intent_summary": "希望看到更多方法示例。",
                        "lesson_labels": ["课节 1"],
                    }
                ],
            }
        )
        result, _ = self.invoke_renderer(report, validate_only=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("count/sample_size", result.stderr)

        report = minimal_valid_report()
        report["audience"] = {
            "status": "available",
            "dimensions": [
                {
                    "name": "学习目标",
                    "segments": [
                        {"label": "掌握方法", "count": 1, "share": 0.9},
                        {"label": "完成实践", "count": 1, "share": 0.1},
                    ],
                    "teaching_implication": "保留方法与实践两类入口。",
                }
            ],
            "note": "仅展示聚合分布。",
        }
        result, _ = self.invoke_renderer(report, validate_only=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("count/dimension total", result.stderr)

    def test_learning_path_rejects_mixed_units_or_scopes(self):
        report = minimal_valid_report()
        report["metric_definitions"].update(
            {
                "path_started": {
                    "label": "开始学习",
                    "definition": "累计开始课程的去重学习者数。",
                    "unit": "人",
                    "source_notes": ["合成测试。"],
                },
                "path_rate": {
                    "label": "触达比例",
                    "definition": "触达某课节的学习者比例。",
                    "unit": "%",
                    "source_notes": ["合成测试。"],
                },
            }
        )
        report["overview"]["learning_path"] = [
            {
                "stage": "开始学习",
                "metric": report_metric(
                    key="path_started",
                    label="开始学习",
                    source_notes=["合成测试。"],
                ),
                "note": "路径起点。",
            },
            {
                "stage": "课节 2",
                "metric": report_metric(
                    key="path_rate",
                    label="触达比例",
                    value=80,
                    unit="%",
                    definition="触达某课节的学习者比例。",
                    source_notes=["合成测试。"],
                ),
                "note": "不同单位，不可同图比较。",
            },
        ]

        result, _ = self.invoke_renderer(report, validate_only=True)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("same unit and time scope", result.stderr)

    def test_operations_metrics_cannot_support_teaching_recommendations(self):
        report = minimal_valid_report()
        definition = "累计消耗的 AI 师傅积分。"
        report["metric_definitions"]["credit_cost"] = {
            "label": "积分消耗",
            "definition": definition,
            "unit": "积分",
            "source_notes": ["仅用于经营附录。"],
        }
        report["operations"] = {
            "requested_by_user": True,
            "metrics": [
                report_metric(
                    key="credit_cost",
                    label="积分消耗",
                    value=42.75,
                    unit="积分",
                    definition=definition,
                    source_notes=["仅用于经营附录。"],
                )
            ],
            "note": "用户明确要求加入积分附录。",
        }
        report["recommendations"][0]["evidence"] = ["credit_cost"]

        result, _ = self.invoke_renderer(report, validate_only=True)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("non-teaching metric", result.stderr)

    def test_schema_rejects_unsupported_report_language(self):
        report = minimal_valid_report()
        report["meta"]["language"] = "ja-JP"

        result, _ = self.invoke_renderer(report, validate_only=True)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("language", result.stderr)

    def test_privacy_scan_rejects_identity_and_raw_id_literals(self):
        unsafe_values = (
            "请联系 learner@example.test 继续学习。",
            "请联系 +86 138 0000 1357 继续学习。",
            "脱敏号码是 138*****000。",
            "脱敏邮箱是 te*****@example.com。",
            "身份字段为 [REDACTED-PHONE]。",
            "内部课程标识为 shifu_bid_eval_do_not_copy。",
            "内部课节标识 outline_item_bid=2a8e9f。",
            "内部短标识 u-bid-1。",
            "内部对象值 0123456789abcdef0123456789abcdef。",
            "平台原始状态 status = 602。",
            "平台原始类型 type=321。",
            "变量代码 var_01。",
            "内部学员编号为 T-009753。",
        )

        for unsafe_value in unsafe_values:
            with self.subTest(unsafe_value=unsafe_value):
                report = copy.deepcopy(minimal_valid_report())
                report["overview"]["executive_summary"]["conclusions"][0] = (
                    unsafe_value
                )

                result, html = self.invoke_renderer(report, validate_only=True)

                self.assertNotEqual(0, result.returncode)
                self.assertEqual("", html)


if __name__ == "__main__":
    unittest.main()
