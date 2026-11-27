#!/usr/bin/env python3
"""Validate and render an AI-Shifu single-course learning report.

This module intentionally uses only the Python standard library. The JSON is
the factual artifact; the generated HTML is an escaped, self-contained view of
that exact data.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import re
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_DIR / "references" / "report-data.schema.json"
TEMPLATE_PATH = SKILL_DIR / "assets" / "report-template.html"
BRAND_DIR = SKILL_DIR / "assets" / "brand"

VALID_ACCENT = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Each preset names the accent and surface the template pairs with it, so a
# requested brand accent can be contrast-checked before it is used.
THEMES = {
    "shifu": {"accent": "#0F63EE", "surface": "#FFFFFF", "scheme": "light"},
    "paper": {"accent": "#2F4FC7", "surface": "#FFFFFF", "scheme": "light"},
    "swiss": {"accent": "#D6001C", "surface": "#FFFFFF", "scheme": "light"},
    "forest": {"accent": "#1F7A4D", "surface": "#FFFFFF", "scheme": "light"},
    "night": {"accent": "#8FB0FF", "surface": "#181B21", "scheme": "dark"},
}
DEFAULT_THEME = "shifu"
BUILTIN_SECTIONS = (
    "summary",
    "kpis",
    "learning_path",
    "lessons",
    "followups",
    "engagement",
    "audience",
    "recommendations",
    "methods",
    "operations",
)
ASSET_ATTRIBUTE = re.compile(
    r"""\b(?:src|href|srcset|poster)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE,
)
CSS_URL = re.compile(r"""url\(\s*["']?\s*([^"')\s]*)""", re.IGNORECASE)
UNSAFE_CSS = re.compile(
    r"<|\\|@import|url\s*\(|image-set\s*\(|(?<![\w-])image\s*\(|expression\s*\(|javascript:|://",
    re.IGNORECASE,
)
TEMPLATE_PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE = re.compile(r"(?<!\d)(?:\+?86[\s-]*)?1[3-9](?:[\s-]*\d){9}(?!\d)")
MASKED_PHONE = re.compile(r"(?<!\d)(?:\+?86[\s-]*)?1[3-9]\d(?:[\s*-]*[\d*]){8,}(?!\d)")
MASKED_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]*\*{2,}[\w.+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_CARD = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")
INTERNAL_ID = re.compile(r"\b[A-Z]{1,4}-\d{4,}\b")
REDACTED_IDENTITY = re.compile(
    r"\[(?:REDACTED|MASKED)[-_ ]?(?:PHONE|EMAIL|NAME|IDENTITY|ID)\]",
    re.IGNORECASE,
)
AUTH_SECRET = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|\bsk-[A-Za-z0-9_-]{12,}|"
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,})",
    re.IGNORECASE,
)
RAW_BID = re.compile(
    r"\b(?:[a-z][a-z0-9_-]*[-_]?bid\s*[:=_-]\s*[A-Za-z0-9_-]{1,}|"
    r"BID_[A-Za-z0-9_-]{6,})\b",
    re.IGNORECASE,
)
OPAQUE_ID = re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{24,64}(?![A-Fa-f0-9])")
RAW_ENUM_CODE = re.compile(r"\b(?:status|type)\s*[:=]\s*\d{3,}\b", re.IGNORECASE)
RAW_ENUM = re.compile(
    r"\b(?:var(?:iable)?|option)_[A-Za-z0-9][A-Za-z0-9_-]*\b",
    re.IGNORECASE,
)
FORBIDDEN_KEY = re.compile(
    r"(?:"
    r"(?:^|_)(?:course|lesson|learner|student|user|variable|progress|order|feedback|shifu)_?bid$|"
    r"_bid$|^raw(?:_|$)|^generated_content$|^question_text$|^answer_text$|"
    r"^follow_?up_text$|^learner_name$|^student_name$|^nickname$|^email$|"
    r"^phone(?:_number)?$|^mobile$|^id_card$|^token$|^authorization$|"
    r"^(?:course|lesson|learner|student|user|variable|progress|order|feedback)_id$"
    r")",
    re.IGNORECASE,
)

DATA_QUALITY_LABELS = {
    "observed": ("已观测", "Observed"),
    "derived": ("已计算", "Derived"),
    "approximate": ("近似", "Approximate"),
    "partial": ("覆盖有限", "Partial"),
    "unavailable": ("不可用", "Unavailable"),
    "not_collected": ("未采集", "Not collected"),
}
HEALTH_LABELS = {
    "healthy": ("健康", "Healthy"),
    "watch": ("观察", "Watch"),
    "attention": ("优先关注", "Attention"),
    "insufficient_data": ("证据不足", "Insufficient data"),
}
PRIORITY_LABELS = {
    "high": ("高优先级", "High priority"),
    "medium": ("中优先级", "Medium priority"),
    "low": ("低优先级", "Low priority"),
}
CONFIDENCE_LABELS = {
    "high": ("高置信度", "High confidence"),
    "medium": ("中置信度", "Medium confidence"),
    "low": ("低置信度", "Low confidence"),
}

TEXT = {
    "zh": {
        "title_suffix": "课程学情报告",
        "skip": "跳到报告正文",
        "toc": "目录",
        "meta_label": "报告信息",
        "subtitle": "用学习数据看清这门课：学员学到了哪里、在问什么、下一步可以改什么。",
        "footer": "本报告由 AI 师傅学情报告根据脱敏聚合数据生成。数据只说明发生了什么，请结合课程设计与教学现场作判断。",
        "period": "报告范围",
        "generated": "生成时间",
        "timezone": "时区",
        "source": "数据来源",
        "sections": {
            "summary": ("核心结论", "这门课现在怎么样", "先看结论：整体状态、最值得关注的地方，以及下一步。"),
            "kpis": ("核心指标", "几个关键数字", "每个数字都可以展开查看口径与来源。"),
            "learning_path": ("学习路径", "学员学到了哪里", "按课程顺序看触达人数。记录中的“进行中”不等于学员卡住了。"),
            "lessons": ("课节表现", "每节课的表现如何", "把各节课放在一起比较，找出最值得回看的课节。"),
            "followups": ("追问主题", "学员在问什么", "只展示最近受审计样本的聚合主题和概括后的学习意图，不保留原文。"),
            "engagement": ("评分与学习方式", "学员怎么评价、怎么学", "评分、听读偏好和活跃状态是不同的信号，分开呈现。"),
            "audience": ("学员画像", "学员是谁", "只展示含义明确的聚合分布。"),
            "recommendations": ("教学建议", "下一步可以试什么", "每条建议都写明依据、把握程度，以及如何验证是否有效。"),
            "methods": ("口径与数据说明", "这些数字是怎么来的", "指标如何定义、哪些数据暂时没有，以及应当如何解读。"),
            "operations": ("经营与积分附录", "经营与积分", "仅因明确要求而包含，不作为教学效果的证据。"),
        },
        "custom_eyebrow": "补充分析",
        "overall_health": "总体判断",
        "conclusion": "结论",
        "critical_limits": "解读前请留意",
        "lesson": "课节",
        "status": "状态",
        "lesson_table": "课节对比",
        "lesson_findings": "逐节发现",
        "evidence": "依据",
        "sample": "抽样说明",
        "theme": "主题",
        "question_unit": "条",
        "learner_unit": "人",
        "ratings": "评分",
        "modes": "听读偏好",
        "activity": "活跃状态",
        "teaching_implication": "教学含义",
        "observation": "观察",
        "interpretation": "解释",
        "action": "建议行动",
        "validation": "验证方法",
        "coverage": "数据覆盖",
        "limitations": "限制",
        "privacy": "隐私处理",
        "teacher_adjustments": "按老师要求所做的调整",
        "teacher_defined": "自定义口径",
        "unavailable_metrics": "暂时没有的指标",
        "metric": "指标",
        "reason": "原因",
        "definitions": "指标口径",
        "definition": "定义",
        "unit": "单位",
        "source_notes": "来源与注意事项",
        "metric_details": "口径与来源",
        "proxy_fraction": "完成人数 / 开始学习人数",
        "fraction": "计算分子 / 分母",
        "completion_rate": "课程完成率",
        "completion_calculation": "按必修课完成状态计算",
        "of_previous": "为上一步的 {share}",
        "change": "变化",
        "percentage_points": "个百分点",
        "zero_followups": "查询成功：最近受审计样本中没有追问。",
        "no_data": "暂无可靠数据",
        "no_data_short": "暂无",
        "not_collected": "本次未采集",
        "source_names": {"live": "AI 师傅平台", "supplied": "用户提供", "synthetic": "合成数据"},
    },
    "en": {
        "title_suffix": "Course Learning Report",
        "skip": "Skip to report",
        "toc": "Contents",
        "meta_label": "Report details",
        "subtitle": "What the learning data says about this course: where learners get to, what they ask, and what to try next.",
        "footer": "Generated by AI-Shifu Learning Report from privacy-safe aggregate data. Data shows what happened; interpret it alongside course design and teaching context.",
        "period": "Reporting period",
        "generated": "Generated",
        "timezone": "Timezone",
        "source": "Source",
        "sections": {
            "summary": ("Key conclusions", "How is this course doing?", "Start here: overall state, what deserves attention, and the next step."),
            "kpis": ("Core metrics", "The numbers that matter", "Expand any number to see its definition and source."),
            "learning_path": ("Learning path", "How far do learners get?", "Reach in course order. A recorded in-progress state is not proof that learners are stuck."),
            "lessons": ("Lesson performance", "How is each lesson doing?", "Compare lessons side by side to find the ones worth revisiting."),
            "followups": ("Follow-up themes", "What are learners asking?", "Only aggregate themes and generalized intents from the latest audited sample; no original text is kept."),
            "engagement": ("Ratings and learning mode", "How do learners rate and study?", "Ratings, read/listen preference, and activity are separate signals."),
            "audience": ("Audience", "Who are the learners?", "Only aggregate distributions with a known meaning are shown."),
            "recommendations": ("Teaching recommendations", "What to try next", "Each recommendation states its evidence, confidence, and how to check whether it worked."),
            "methods": ("Definitions and data notes", "Where these numbers come from", "How metrics are defined, what is unavailable, and how to read the findings."),
            "operations": ("Operations and credits appendix", "Operations and credits", "Included only on explicit request; not evidence of teaching effectiveness."),
        },
        "custom_eyebrow": "Additional analysis",
        "overall_health": "Overall assessment",
        "conclusion": "Conclusions",
        "critical_limits": "Before you interpret",
        "lesson": "Lesson",
        "status": "Status",
        "lesson_table": "Lesson comparison",
        "lesson_findings": "Lesson by lesson",
        "evidence": "Evidence",
        "sample": "Sample",
        "theme": "Themes",
        "question_unit": "",
        "learner_unit": "",
        "ratings": "Ratings",
        "modes": "Read/listen preference",
        "activity": "Activity state",
        "teaching_implication": "Teaching implication",
        "observation": "Observation",
        "interpretation": "Interpretation",
        "action": "Action",
        "validation": "Validation method",
        "coverage": "Coverage",
        "limitations": "Limitations",
        "privacy": "Privacy handling",
        "teacher_adjustments": "Adjustments requested by the teacher",
        "teacher_defined": "Custom definition",
        "unavailable_metrics": "Unavailable metrics",
        "metric": "Metric",
        "reason": "Reason",
        "definitions": "Metric definitions",
        "definition": "Definition",
        "unit": "Unit",
        "source_notes": "Source notes",
        "metric_details": "Definition and source",
        "proxy_fraction": "Completed / started learners",
        "fraction": "Numerator / denominator",
        "completion_rate": "Course completion rate",
        "completion_calculation": "Calculated from required-lesson completion",
        "of_previous": "{share} of the previous step",
        "change": "change",
        "percentage_points": "pts",
        "zero_followups": "Query succeeded: no follow-up questions were observed in the latest audited sample.",
        "no_data": "No reliable data",
        "no_data_short": "n/a",
        "not_collected": "Not collected in this report",
        "source_names": {"live": "AI-Shifu platform", "supplied": "Supplied data", "synthetic": "Synthetic data"},
    },
}


class ReportError(ValueError):
    """Raised when report data is unsafe or violates the contract."""


class DuplicateKeyError(ReportError):
    """Raised when a JSON object repeats a key."""


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_pairs_without_duplicates)
    except OSError as exc:
        raise ReportError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _resolve_ref(root: Mapping[str, Any], reference: str) -> Mapping[str, Any]:
    if not reference.startswith("#/"):
        raise ReportError(f"unsupported schema reference: {reference}")
    current: Any = root
    for part in reference[2:].split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, Mapping) or token not in current:
            raise ReportError(f"broken schema reference: {reference}")
        current = current[token]
    if not isinstance(current, Mapping):
        raise ReportError(f"schema reference does not point to an object: {reference}")
    return current


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    raise ReportError(f"unsupported schema type: {type_name}")


def _type_description(expected: str | Sequence[str]) -> str:
    if isinstance(expected, str):
        return expected
    return " or ".join(expected)


def validate_against_schema(
    value: Any,
    schema: Mapping[str, Any],
    root: Mapping[str, Any],
    path: str = "$",
) -> None:
    if "$ref" in schema:
        validate_against_schema(value, _resolve_ref(root, schema["$ref"]), root, path)
        return

    if "const" in schema and value != schema["const"]:
        raise ReportError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ReportError(f"{path}: expected one of {schema['enum']!r}, got {value!r}")

    expected = schema.get("type")
    if expected is not None:
        type_names = [expected] if isinstance(expected, str) else list(expected)
        if not any(_matches_type(value, type_name) for type_name in type_names):
            raise ReportError(
                f"{path}: expected {_type_description(expected)}, got {type(value).__name__}"
            )

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ReportError(f"{path}: string is shorter than allowed")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ReportError(f"{path}: string is longer than allowed")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ReportError(f"{path}: value does not match required pattern")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ReportError(f"{path}: value is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ReportError(f"{path}: value is above {schema['maximum']}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ReportError(f"{path}: array has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ReportError(f"{path}: array has too many items")
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                validate_against_schema(item, item_schema, root, f"{path}[{index}]")

    if isinstance(value, dict):
        if len(value) < schema.get("minProperties", 0):
            raise ReportError(f"{path}: object has too few properties")
        for key in schema.get("required", []):
            if key not in value:
                raise ReportError(f"{path}: missing required property {key!r}")

        property_names = schema.get("propertyNames")
        if isinstance(property_names, Mapping):
            for key in value:
                validate_against_schema(key, property_names, root, f"{path}.<key>")

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                validate_against_schema(item, properties[key], root, child_path)
            elif additional is False:
                raise ReportError(f"{path}: unexpected property {key!r}")
            elif isinstance(additional, Mapping):
                validate_against_schema(item, additional, root, child_path)


def _walk(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def privacy_scan(report: Mapping[str, Any]) -> None:
    for path, value in _walk(report):
        if isinstance(value, dict):
            for key in value:
                if FORBIDDEN_KEY.search(key):
                    raise ReportError(f"{path}.{key}: forbidden raw or identifying field")
        elif isinstance(value, str):
            checks = (
                (EMAIL, "email address"),
                (PHONE, "phone number"),
                (MASKED_PHONE, "masked phone number"),
                (MASKED_EMAIL, "masked email address"),
                (ID_CARD, "identity-card number"),
                (INTERNAL_ID, "learner-level internal identifier"),
                (REDACTED_IDENTITY, "masked identity placeholder"),
                (AUTH_SECRET, "authentication secret"),
                (RAW_BID, "raw BID"),
                (OPAQUE_ID, "opaque internal identifier"),
                (RAW_ENUM_CODE, "raw platform enum code"),
                (RAW_ENUM, "raw identifier or enum code"),
            )
            for pattern, label in checks:
                if pattern.search(value):
                    raise ReportError(f"{path}: contains a forbidden {label}")


def iter_metrics(report: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    overview = report["overview"]
    for index, metric in enumerate(overview["kpis"]):
        yield f"$.overview.kpis[{index}]", metric
    for index, stage in enumerate(overview["learning_path"]):
        yield f"$.overview.learning_path[{index}].metric", stage["metric"]
    for lesson_index, lesson in enumerate(report["lesson_health"]):
        for metric_index, metric in enumerate(lesson["metrics"]):
            yield f"$.lesson_health[{lesson_index}].metrics[{metric_index}]", metric
    for group in ("ratings", "learning_modes", "activity"):
        for index, metric in enumerate(report["engagement"][group]):
            yield f"$.engagement.{group}[{index}]", metric
    if "operations" in report:
        for index, metric in enumerate(report["operations"]["metrics"]):
            yield f"$.operations.metrics[{index}]", metric
    for section_index, section in enumerate(report.get("custom_sections", [])):
        for block_index, block in enumerate(section["blocks"]):
            for index, metric in enumerate(block.get("metrics", [])):
                yield (
                    f"$.custom_sections[{section_index}].blocks[{block_index}].metrics[{index}]",
                    metric,
                )


def resolve_sections(report: Mapping[str, Any]) -> list[str]:
    """Visible section ids in render order: the teacher's list, or the default."""
    requested = report.get("presentation", {}).get("sections")
    if requested is None:
        custom = [f'custom:{section["id"]}' for section in report.get("custom_sections", [])]
        requested = [
            "summary",
            "kpis",
            "learning_path",
            "lessons",
            "followups",
            "engagement",
            "audience",
            *custom,
            "recommendations",
            "methods",
            "operations",
        ]
    return [item for item in requested if item != "operations" or "operations" in report]


def validate_presentation(report: Mapping[str, Any]) -> None:
    """Check teacher-requested layout, custom sections and style overrides."""
    custom_sections = report.get("custom_sections", [])
    custom_ids = [section["id"] for section in custom_sections]
    if len(custom_ids) != len(set(custom_ids)):
        raise ReportError("$.custom_sections: section ids must be unique")
    known = set(BUILTIN_SECTIONS) | {f"custom:{item}" for item in custom_ids}

    presentation = report.get("presentation", {})
    sections = presentation.get("sections")
    if sections is not None:
        if len(sections) != len(set(sections)):
            raise ReportError("$.presentation.sections: a section can be listed only once")
        for item in sections:
            if item not in known:
                raise ReportError(f"$.presentation.sections: unknown section {item!r}")
        if "methods" not in sections:
            raise ReportError(
                "$.presentation.sections: 'methods' cannot be hidden; readers need metric "
                "definitions and data limitations"
            )
    for item in presentation.get("section_titles", {}):
        if item not in known:
            raise ReportError(f"$.presentation.section_titles: unknown section {item!r}")
    if UNSAFE_CSS.search(presentation.get("custom_css", "")):
        raise ReportError(
            "$.presentation.custom_css: markup, escapes, @import, url(), image-set(), "
            "links and script expressions are not allowed"
        )

    required_fields = {
        "text": ("body",),
        "callout": ("body",),
        "metrics": ("metrics",),
        "bars": ("metrics",),
        "table": ("columns", "rows", "source_note"),
    }
    for section_index, section in enumerate(custom_sections):
        for block_index, block in enumerate(section["blocks"]):
            path = f"$.custom_sections[{section_index}].blocks[{block_index}]"
            kind = block["type"]
            for field in required_fields[kind]:
                if field not in block:
                    raise ReportError(f"{path}: a {kind} block requires {field!r}")
            if kind == "bars":
                if len({metric["unit"] for metric in block["metrics"]}) != 1:
                    raise ReportError(f"{path}: bars in one chart must share a unit")
                for metric in block["metrics"]:
                    value = metric["value"]
                    if value is not None and (
                        not isinstance(value, (int, float)) or isinstance(value, bool)
                    ):
                        raise ReportError(f"{path}: bar values must be numeric or null")
                    if value is not None and value < 0:
                        raise ReportError(
                            f"{path}: bar charts need non-negative values; "
                            "show signed changes in a table"
                        )
            if kind == "table":
                width = len(block["columns"])
                if any(len(row) != width for row in block["rows"]):
                    raise ReportError(f"{path}: every table row must match the column count")


def validate_semantics(report: Mapping[str, Any]) -> None:
    definitions = report["metric_definitions"]
    if report["schema_version"] == "1.0":
        newer = [name for name in ("presentation", "custom_sections") if name in report]
        if "teacher_adjustments" in report["data_quality"]:
            newer.append("data_quality.teacher_adjustments")
        if any("origin" in definition for definition in definitions.values()):
            newer.append("metric_definitions origin")
        if any("comparison" in metric for _, metric in iter_metrics(report)):
            newer.append("metric comparison")
        if newer:
            raise ReportError(
                f'$.schema_version: {", ".join(newer)} require schema_version "1.1"'
            )
    for key in definitions:
        if FORBIDDEN_KEY.search(key):
            raise ReportError(f"$.metric_definitions: forbidden identifier-like key {key!r}")
    metric_paths: dict[str, str] = {}
    metrics: dict[str, Mapping[str, Any]] = {}
    operation_keys = {
        metric["key"] for metric in report.get("operations", {}).get("metrics", [])
    }

    for path, metric in iter_metrics(report):
        key = metric["key"]
        if FORBIDDEN_KEY.search(key):
            raise ReportError(f"{path}.key: forbidden identifier-like metric key {key!r}")
        if key in metrics:
            raise ReportError(f"{path}.key: duplicate metric key {key!r}; first seen at {metric_paths[key]}")
        metrics[key] = metric
        metric_paths[key] = path
        if key not in definitions:
            raise ReportError(f"{path}.key: metric {key!r} is missing from metric_definitions")
        definition = definitions[key]
        for field in ("label", "definition", "unit"):
            if metric[field] != definition[field]:
                raise ReportError(
                    f"{path}.{field}: does not match metric_definitions[{key!r}]"
                )

        quality = metric["data_quality"]
        value = metric["value"]
        if value is None and quality not in {"partial", "unavailable", "not_collected"}:
            raise ReportError(f"{path}: null value requires partial, unavailable, or not_collected quality")
        if value is not None and quality in {"unavailable", "not_collected"}:
            raise ReportError(f"{path}: unavailable/not_collected metric must have a null value")
        if metric["is_approximate"] and quality != "approximate":
            raise ReportError(f"{path}: an approximate metric must use data_quality='approximate'")
        if quality == "approximate" and not metric["is_approximate"]:
            raise ReportError(f"{path}: approximate data quality requires is_approximate=true")
        if metric["unit"] == "%" and value is not None:
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
                or value > 100
            ):
                raise ReportError(f"{path}: percentage metric value must be numeric from 0 to 100")
            numerator = metric.get("numerator")
            denominator = metric.get("denominator")
            if numerator is not None and denominator is not None:
                if denominator <= 0 or numerator < 0 or numerator > denominator:
                    raise ReportError(
                        f"{path}: numerator must be between zero and a positive denominator"
                    )
                if not math.isclose(
                    float(value), numerator / denominator * 100, rel_tol=0.002, abs_tol=0.11
                ):
                    raise ReportError(f"{path}: value does not match numerator/denominator")

    completion_metrics = [
        (key, metric) for key, metric in metrics.items() if key.endswith("completion_proxy")
    ]
    if len(completion_metrics) > 1:
        raise ReportError(
            "report must contain at most one metric whose key ends with 'completion_proxy'"
        )
    completion_key, completion = completion_metrics[0] if completion_metrics else ("", None)
    if completion is not None and completion["value"] is not None:
        numerator = completion.get("numerator")
        denominator = completion.get("denominator")
        if not completion["is_approximate"]:
            raise ReportError(f"metric {completion_key!r}: completion proxy must be approximate")
        if not isinstance(numerator, (int, float)) or isinstance(numerator, bool):
            raise ReportError(f"metric {completion_key!r}: numerator is required")
        if not isinstance(denominator, (int, float)) or isinstance(denominator, bool) or denominator <= 0:
            raise ReportError(f"metric {completion_key!r}: positive denominator is required")
        if numerator < 0 or numerator > denominator:
            raise ReportError(f"metric {completion_key!r}: numerator must be between zero and denominator")
        expected = numerator / denominator
        if completion["unit"] == "%":
            expected *= 100
        if not isinstance(completion["value"], (int, float)) or isinstance(completion["value"], bool):
            raise ReportError(f"metric {completion_key!r}: proxy value must be numeric")
        if not math.isclose(float(completion["value"]), expected, rel_tol=0.002, abs_tol=0.11):
            raise ReportError(
                f"metric {completion_key!r}: value does not match numerator/denominator"
            )

    for lesson_index, lesson in enumerate(report["lesson_health"]):
        # The comparison table keys a lesson's metrics by label, so a repeat would be dropped.
        labels = [metric["label"] for metric in lesson["metrics"]]
        repeated = sorted({label for label in labels if labels.count(label) > 1})
        if repeated:
            raise ReportError(
                f"$.lesson_health[{lesson_index}].metrics: label {repeated[0]!r} appears more "
                "than once in one lesson; give each metric a distinct label or use 'comparison'"
            )
        for reference in lesson["evidence"]:
            if reference not in metrics or reference in operation_keys:
                raise ReportError(
                    f"$.lesson_health[{lesson_index}].evidence: unknown or non-teaching metric {reference!r}"
                )

    for recommendation_index, recommendation in enumerate(report["recommendations"]):
        for reference in recommendation["evidence"]:
            if reference not in metrics or reference in operation_keys:
                raise ReportError(
                    f"$.recommendations[{recommendation_index}].evidence: unknown or non-teaching metric {reference!r}"
                )

    followups = report["engagement"]["follow_up_analysis"]
    status = followups["status"]
    if status == "available":
        if followups["sample_size"] is None or followups["audited_access"] is not True:
            raise ReportError(
                "$.engagement.follow_up_analysis: available themes require an audited sample size"
            )
        if followups["sample_size"] == 0 and followups["themes"]:
            raise ReportError(
                "$.engagement.follow_up_analysis.themes: zero-sized sample cannot have themes"
            )
        for index, theme in enumerate(followups["themes"]):
            if theme["count"] > followups["sample_size"]:
                raise ReportError(
                    f"$.engagement.follow_up_analysis.themes[{index}].count exceeds sample size"
                )
            if followups["sample_size"] > 0:
                expected_share = theme["count"] / followups["sample_size"]
                if theme["share"] is None or not math.isclose(
                    theme["share"], expected_share, rel_tol=0.001, abs_tol=0.001
                ):
                    raise ReportError(
                        f"$.engagement.follow_up_analysis.themes[{index}].share "
                        "does not match count/sample_size"
                    )
    else:
        if followups["sample_size"] is not None or followups["themes"]:
            raise ReportError(
                "$.engagement.follow_up_analysis: unavailable/not_collected state must not contain a sample or themes"
            )
        if status == "not_collected" and followups["audited_access"]:
            raise ReportError(
                "$.engagement.follow_up_analysis: not_collected state cannot claim audited access"
            )

    audience = report["audience"]
    if audience["status"] == "unavailable" and audience["dimensions"]:
        raise ReportError("$.audience.dimensions: unavailable audience must not invent dimensions")
    if audience["status"] == "available" and not audience["dimensions"]:
        raise ReportError("$.audience.dimensions: available audience requires at least one dimension")
    for dimension_index, dimension in enumerate(audience["dimensions"]):
        total = sum(segment["count"] for segment in dimension["segments"])
        for segment_index, segment in enumerate(dimension["segments"]):
            expected_share = segment["count"] / total if total else None
            if expected_share is None:
                if segment["share"] not in {None, 0}:
                    raise ReportError(
                        f"$.audience.dimensions[{dimension_index}].segments[{segment_index}].share "
                        "must be null or zero when the dimension has no observations"
                    )
            elif segment["share"] is None or not math.isclose(
                segment["share"], expected_share, rel_tol=0.001, abs_tol=0.001
            ):
                raise ReportError(
                    f"$.audience.dimensions[{dimension_index}].segments[{segment_index}].share "
                    "does not match count/dimension total"
                )

    lesson_positions = [lesson["position"] for lesson in report["lesson_health"]]
    if lesson_positions != sorted(set(lesson_positions)):
        raise ReportError("$.lesson_health: positions must be unique and ordered")

    path_metrics = [stage["metric"] for stage in report["overview"]["learning_path"]]
    if path_metrics:
        path_unit = path_metrics[0]["unit"]
        path_scope = path_metrics[0]["time_scope"]
        for index, metric in enumerate(path_metrics):
            if metric["unit"] != path_unit or metric["time_scope"] != path_scope:
                raise ReportError(
                    f"$.overview.learning_path[{index}].metric: all path stages must use "
                    "the same unit and time scope"
                )
            if metric["value"] is not None and (
                not isinstance(metric["value"], (int, float))
                or isinstance(metric["value"], bool)
            ):
                raise ReportError(
                    f"$.overview.learning_path[{index}].metric.value: path charts require numeric or null values"
                )
            if metric["value"] is not None and metric["value"] < 0:
                raise ReportError(
                    f"$.overview.learning_path[{index}].metric.value: path charts need non-negative values"
                )

    try:
        datetime.fromisoformat(report["meta"]["generated_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportError("$.meta.generated_at: expected an ISO 8601 date-time") from exc

    validate_presentation(report)
    privacy_scan(report)


def validate_report(report: Any) -> Mapping[str, Any]:
    if not isinstance(report, dict):
        raise ReportError("$: report must be a JSON object")
    schema = load_json(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise ReportError(f"schema is not an object: {SCHEMA_PATH}")
    validate_against_schema(report, schema, schema)
    validate_semantics(report)
    return report


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _language(meta: Mapping[str, Any]) -> tuple[bool, Mapping[str, Any]]:
    is_zh = meta["language"].lower().startswith("zh")
    return is_zh, TEXT["zh" if is_zh else "en"]


class RenderContext:
    """Read-only lookups shared by every section renderer."""

    def __init__(self, report: Mapping[str, Any]) -> None:
        self.report = report
        self.is_zh, self.strings = _language(report["meta"])
        self.definitions: Mapping[str, Any] = report["metric_definitions"]
        self.metrics = {metric["key"]: metric for _, metric in iter_metrics(report)}
        self.presentation: Mapping[str, Any] = report.get("presentation", {})
        self.lesson_of = {
            metric["key"]: lesson["position"]
            for lesson in report["lesson_health"]
            for metric in lesson["metrics"]
        }

    def t(self, key: str) -> str:
        return str(self.strings[key])

    def enum(self, mapping: Mapping[str, tuple[str, str]], value: str) -> str:
        labels = mapping.get(value)
        return labels[0 if self.is_zh else 1] if labels else value


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _safe_accent(value: Any, theme: str) -> str:
    """Use a requested accent only when it stays readable on the theme surface."""
    preset = THEMES[theme]
    if not isinstance(value, str) or VALID_ACCENT.fullmatch(value) is None:
        return preset["accent"]
    return value if _contrast(value, preset["surface"]) >= 4.5 else preset["accent"]


def _brand_logo(ctx: RenderContext) -> str:
    """Embed the AI-Shifu logo for light and dark backgrounds as data URIs."""
    language = "zh" if ctx.is_zh else "en"
    name = "AI 师傅" if ctx.is_zh else "AI-Shifu"
    images = ""
    for variant, suffix in (("on-light", ""), ("on-dark", "-reverse")):
        path = BRAND_DIR / f"logo-{language}{suffix}.png"
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise ReportError(f"cannot read brand logo {path}: {exc}") from exc
        images += (
            f'<img class="brand-logo {variant}" alt="{esc(name)}" '
            f'src="data:image/png;base64,{encoded}">'
        )
    return images


def _format_generated_at(value: str, is_zh: bool) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if is_zh:
        return f"{parsed.year}年{parsed.month}月{parsed.day}日 {parsed.hour:02d}:{parsed.minute:02d}"
    month = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )[parsed.month - 1]
    return f"{month} {parsed.day}, {parsed.year} {parsed.hour:02d}:{parsed.minute:02d}"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _format_number(value: int | float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _with_unit(rendered: str, unit: str) -> str:
    if not unit:
        return rendered
    separator = "" if unit == "%" or ord(unit[0]) > 0x2E7F else " "
    return rendered + separator + unit


def _format_share(value: int | float | None, ctx: RenderContext) -> str:
    if value is None:
        return ctx.t("no_data")
    return f"{value:.1%}"


def _is_completion(metric: Mapping[str, Any]) -> bool:
    return str(metric["key"]).endswith("completion_proxy")


def metric_text(metric: Mapping[str, Any], ctx: RenderContext, *, short: bool = False) -> str:
    """Return the unescaped reader-facing value; a missing value is never zero."""
    value = metric["value"]
    if value is None:
        return ctx.t("no_data_short" if short else "no_data")
    rendered = _format_number(value) if _is_number(value) else str(value)
    return _with_unit(rendered, metric["unit"])


def display_metric_label(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    if _is_completion(metric) and not _is_teacher_defined(metric["key"], ctx):
        return ctx.t("completion_rate")
    return str(metric["label"])


def _is_teacher_defined(key: str, ctx: RenderContext) -> bool:
    return ctx.definitions.get(key, {}).get("origin") == "teacher"


def metric_tags(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    tags = ""
    if _is_teacher_defined(metric["key"], ctx):
        tags += f'<span class="tag is-teacher">{esc(ctx.t("teacher_defined"))}</span>'
    if metric["is_approximate"] and not _is_completion(metric):
        tags += f'<span class="tag approx-tag">{esc(ctx.enum(DATA_QUALITY_LABELS, "approximate"))}</span>'
    return tags


def quality_label(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    if (
        _is_completion(metric)
        and metric["value"] is not None
        and not _is_teacher_defined(metric["key"], ctx)
    ):
        return ctx.t("completion_calculation")
    return ctx.enum(DATA_QUALITY_LABELS, metric["data_quality"])


def metric_context(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    return f'{metric["time_scope"]["label"]} · {quality_label(metric, ctx)}'


def comparison_text(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    comparison = metric.get("comparison")
    value = metric["value"]
    if not comparison or not _is_number(value):
        return ""
    unit = metric["unit"]
    previous = _with_unit(_format_number(comparison["value"]), unit)
    delta = value - comparison["value"]
    sign = "+" if delta > 0 else ("−" if delta < 0 else "±")
    delta_unit = ctx.t("percentage_points") if unit == "%" else unit
    change = _with_unit(sign + _format_number(abs(round(delta, 2))), delta_unit)
    return f'{comparison["label"]} {previous} · {ctx.t("change")} {change}'


def comparison_html(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    """Before/after line for metric views outside the KPI tiles."""
    comparison = comparison_text(metric, ctx)
    return f'<span class="cell-sub">{esc(comparison)}</span>' if comparison else ""


def definitions_details(
    metrics: Sequence[Mapping[str, Any]], ctx: RenderContext, *, show_label: bool = True
) -> str:
    """Collapsible definition, scope and source for the metrics shown nearby."""
    if not metrics:
        return ""
    separator = "；" if ctx.is_zh else "; "
    rows: list[str] = []
    for metric in metrics:
        notes = separator.join(esc(note) for note in metric["source_notes"])
        body = f'<p>{esc(metric["definition"])}</p><p>{notes}</p>'
        if show_label:
            rows.append(
                f'<div><dt>{esc(display_metric_label(metric, ctx))}'
                f'（{esc(metric_context(metric, ctx))}）</dt><dd>{body}</dd></div>'
            )
        else:
            rows.append(body)
    content = f'<dl class="definition-list">{"".join(rows)}</dl>' if show_label else "".join(rows)
    return (
        f'<details class="metric-details"><summary>{esc(ctx.t("metric_details"))}</summary>'
        f'<div class="details-body">{content}</div></details>'
    )


def _empty(text: str) -> str:
    return f'<p class="callout empty-state">{esc(text)}</p>'


def _list_html(items: Iterable[str], empty_text: str) -> str:
    values = list(items)
    if not values:
        return f'<p class="empty-state">{esc(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in values) + "</ul>"


def _meter(fraction: float, label: str) -> str:
    width = max(0.0, min(100.0, fraction * 100))
    return f'<div class="meter" title="{esc(label)}"><span style="width:{width:.2f}%"></span></div>'


def _bar(fraction: float | None, label: str) -> str:
    """A bar from zero; a missing value (None) keeps the baseline but draws no mark."""
    if fraction is None:
        return f'<div class="bar is-empty" title="{esc(label)}"></div>'
    width = max(0.0, min(100.0, fraction * 100))
    return f'<div class="bar" title="{esc(label)}"><span style="width:{width:.2f}%"></span></div>'


def render_kpi(metric: Mapping[str, Any], ctx: RenderContext) -> str:
    value = metric["value"]
    unit = metric["unit"]
    if value is None:
        value_html = f'<div class="kpi-value is-empty">{esc(ctx.t("no_data"))}</div>'
    elif _is_number(value):
        unit_html = f'<span class="unit">{esc(unit)}</span>' if unit else ""
        value_html = (
            f'<div class="kpi-value"><span class="num">{esc(_format_number(value))}</span>'
            f"{unit_html}</div>"
        )
    else:
        value_html = f'<div class="kpi-value">{esc(_with_unit(str(value), unit))}</div>'

    extras = ""
    if _is_number(value) and unit == "%":
        extras += _meter(float(value) / 100, metric_text(metric, ctx))
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    if numerator is not None and denominator is not None:
        standard_completion = _is_completion(metric) and not _is_teacher_defined(metric["key"], ctx)
        fraction_label = ctx.t("proxy_fraction" if standard_completion else "fraction")
        extras += (
            f'<div class="kpi-fraction">{esc(fraction_label)}：'
            f"{esc(_format_number(numerator))} / {esc(_format_number(denominator))}</div>"
        )
    comparison = comparison_text(metric, ctx)
    if comparison:
        extras += f'<div class="kpi-delta">{esc(comparison)}</div>'
    return (
        '<article class="kpi">'
        f'<div class="kpi-label">{esc(display_metric_label(metric, ctx))}{metric_tags(metric, ctx)}</div>'
        + value_html
        + extras
        + f'<div class="kpi-meta">{esc(metric_context(metric, ctx))}</div>'
        + definitions_details([metric], ctx, show_label=False)
        + "</article>"
    )


def render_evidence(
    references: Sequence[str], ctx: RenderContext, *, within_lesson: int | None = None
) -> str:
    """Evidence chips; a lesson metric cited elsewhere names its lesson."""
    if not references:
        return ""
    chips = ""
    for reference in references:
        metric = ctx.metrics[reference]
        label = display_metric_label(metric, ctx)
        position = ctx.lesson_of.get(reference)
        if position is not None and position != within_lesson:
            label = f'{ctx.t("lesson")} {position} · {label}'
        chips += (
            f'<span class="evidence-ref">{esc(label)}：{esc(metric_text(metric, ctx))}</span>'
        )
    return (
        f'<div class="evidence" aria-label="{esc(ctx.t("evidence"))}">'
        f'<span>{esc(ctx.t("evidence"))}</span>{chips}</div>'
    )


def render_summary(report: Mapping[str, Any], ctx: RenderContext) -> str:
    summary = report["overview"]["executive_summary"]
    conclusions = "".join(
        f'<li class="conclusion"><span class="badge-index" aria-hidden="true">{index}</span>'
        f"<p>{esc(item)}</p></li>"
        for index, item in enumerate(summary["conclusions"], start=1)
    )
    limitations = summary["critical_limitations"]
    limitation_html = ""
    if limitations:
        limitation_html = (
            f'<aside class="callout is-limit" aria-label="{esc(ctx.t("critical_limits"))}">'
            f'<strong>{esc(ctx.t("critical_limits"))}</strong>'
            + _list_html(limitations, "")
            + "</aside>"
        )
    return (
        f'<p class="verdict"><span class="verdict-label">{esc(ctx.t("overall_health"))}</span>'
        f'{esc(summary["overall_health"])}</p>'
        f'<ol class="conclusions" aria-label="{esc(ctx.t("conclusion"))}">{conclusions}</ol>'
        + limitation_html
    )


def render_kpis(report: Mapping[str, Any], ctx: RenderContext) -> str:
    return (
        '<div class="kpi-grid">'
        + "".join(render_kpi(metric, ctx) for metric in report["overview"]["kpis"])
        + "</div>"
    )


def render_learning_path(report: Mapping[str, Any], ctx: RenderContext) -> str:
    stages = report["overview"]["learning_path"]
    if not stages:
        return _empty(ctx.t("no_data"))
    metrics = [stage["metric"] for stage in stages]
    numeric = [float(metric["value"]) for metric in metrics if _is_number(metric["value"])]
    unit = metrics[0]["unit"]
    # A percentage is drawn against 100, as in every other section; counts against the largest.
    maximum = 100.0 if unit == "%" else max(numeric, default=0.0)
    uniform_quality = len({quality_label(metric, ctx) for metric in metrics}) == 1
    rows: list[str] = []
    previous: float | None = None
    for position, stage in enumerate(stages, start=1):
        metric = stage["metric"]
        value = metric["value"]
        value_label = metric_text(metric, ctx)
        notes = [stage["note"]] if stage["note"] else []
        if not uniform_quality:
            notes.append(quality_label(metric, ctx))
        if _is_number(value):
            fraction = float(value) / maximum if maximum > 0 else 0.0
            if previous and unit != "%":
                notes.append(ctx.t("of_previous").format(share=f"{float(value) / previous:.0%}"))
            previous = float(value)
        else:
            fraction = None
            previous = None
        comparison = comparison_text(metric, ctx)
        if comparison:
            notes.append(comparison)
        note_html = (
            f'<div class="path-note">{esc(" · ".join(notes))}</div>' if notes else ""
        )
        rows.append(
            '<li class="path-row">'
            f'<div class="path-stage"><span class="path-index" aria-hidden="true">{position}</span>'
            f'<span>{esc(stage["stage"])}</span></div>'
            + _bar(fraction, f'{stage["stage"]}: {value_label}')
            + f'<div class="path-value">{esc(value_label)}</div>'
            + note_html
            + "</li>"
        )
    context = (
        metric_context(metrics[0], ctx) if uniform_quality else metrics[0]["time_scope"]["label"]
    )
    caption = f'{ctx.t("unit")}：{unit} · {context}' if unit else context
    return (
        '<figure class="chart">'
        f'<figcaption class="chart-caption">{esc(caption)}</figcaption>'
        f'<ol class="path">{"".join(rows)}</ol></figure>'
        + definitions_details(metrics, ctx)
    )


def _lesson_table_columns(lessons: Sequence[Mapping[str, Any]], ctx: RenderContext) -> list[str]:
    """Metrics that share a display label across lessons share a table column."""
    available: list[str] = []
    for lesson in lessons:
        for metric in lesson["metrics"]:
            label = display_metric_label(metric, ctx)
            if label not in available:
                available.append(label)
    requested = ctx.presentation.get("lesson_table_columns")
    columns = [label for label in requested if label in available] if requested else available[:6]
    return columns if len(lessons) >= 2 else []


def _lesson_table(
    lessons: Sequence[Mapping[str, Any]], columns: Sequence[str], ctx: RenderContext
) -> str:
    if not columns:
        return ""
    head = "".join(f'<th scope="col" class="num">{esc(label)}</th>' for label in columns)
    rows: list[str] = []
    for lesson in lessons:
        by_label = {display_metric_label(metric, ctx): metric for metric in lesson["metrics"]}
        cells = ""
        for label in columns:
            metric = by_label.get(label)
            if metric is None or metric["value"] is None:
                cells += f'<td class="num is-missing">{esc(ctx.t("no_data_short"))}</td>'
            else:
                cells += (
                    f'<td class="num">{esc(metric_text(metric, ctx))}'
                    f"{comparison_html(metric, ctx)}</td>"
                )
        status = lesson["health_status"]
        rows.append(
            f'<tr><th scope="row"><span class="cell-sub">{esc(ctx.t("lesson"))} {lesson["position"]:02d}</span>'
            f'{esc(lesson["title"])}</th>'
            f'<td><span class="pill is-{esc(status)}">{esc(ctx.enum(HEALTH_LABELS, status))}</span></td>'
            f"{cells}</tr>"
        )
    return (
        '<div class="table-wrap"><table class="lesson-table">'
        f'<caption>{esc(ctx.t("lesson_table"))}</caption><thead><tr>'
        f'<th scope="col">{esc(ctx.t("lesson"))}</th><th scope="col">{esc(ctx.t("status"))}</th>{head}'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_lessons(report: Mapping[str, Any], ctx: RenderContext) -> str:
    lessons = report["lesson_health"]
    if not lessons:
        return _empty(ctx.t("no_data"))
    columns = _lesson_table_columns(lessons, ctx)
    cards: list[str] = []
    for lesson in lessons:
        status = lesson["health_status"]
        # The comparison table already shows these; cards repeat only what it omits.
        stats = "".join(
            f'<div class="stat"><dt>{esc(display_metric_label(metric, ctx))}{metric_tags(metric, ctx)}</dt>'
            f'<dd>{esc(metric_text(metric, ctx, short=True))}{comparison_html(metric, ctx)}</dd></div>'
            for metric in lesson["metrics"]
            if display_metric_label(metric, ctx) not in columns
        )
        stats_html = f'<dl class="stats">{stats}</dl>' if stats else ""
        cards.append(
            '<article class="lesson">'
            '<div class="lesson-header"><div>'
            f'<span class="lesson-order">{esc(ctx.t("lesson"))} {lesson["position"]:02d}</span>'
            f'<h3>{esc(lesson["title"])}</h3></div>'
            f'<span class="pill is-{esc(status)}">{esc(ctx.enum(HEALTH_LABELS, status))}</span></div>'
            f'<p class="lesson-finding">{esc(lesson["finding"])}</p>'
            + stats_html
            + render_evidence(lesson["evidence"], ctx, within_lesson=lesson["position"])
            + definitions_details(lesson["metrics"], ctx)
            + "</article>"
        )
    table = _lesson_table(lessons, columns, ctx)
    heading = (
        f'<h3 class="subsection-heading">{esc(ctx.t("lesson_findings"))}</h3>' if table else ""
    )
    return table + heading + f'<div class="lesson-list">{"".join(cards)}</div>'


def render_followups(report: Mapping[str, Any], ctx: RenderContext) -> str:
    followups = report["engagement"]["follow_up_analysis"]
    status = followups["status"]
    if status != "available":
        state_text = ctx.t("not_collected" if status == "not_collected" else "no_data")
        return (
            f'<p class="chart-caption">{esc(followups["sampling_rule"])}</p>' + _empty(state_text)
        )
    sample_size = followups["sample_size"]
    span = followups["effective_span"] or ctx.t("no_data")
    sample_note = (
        f'{ctx.t("sample")}：{followups["sampling_rule"]} · '
        f'{sample_size}/{followups["sample_limit"]} · {span}'
    )
    if sample_size == 0:
        body = _empty(ctx.t("zero_followups"))
    else:
        themes: list[str] = []
        for theme in followups["themes"]:
            share = _format_share(theme["share"], ctx)
            count = _with_unit(str(theme["count"]), ctx.t("question_unit"))
            lessons = "".join(
                f'<span class="evidence-ref">{esc(label)}</span>' for label in theme["lesson_labels"]
            )
            lessons_html = f'<div class="theme-lessons">{lessons}</div>' if lessons else ""
            meter = _meter(theme["share"] or 0.0, f'{theme["theme"]}: {share}')
            themes.append(
                '<li class="theme"><div>'
                f'<h3>{esc(theme["theme"])}</h3>'
                f'<p class="theme-intent">{esc(theme["intent_summary"])}</p>{lessons_html}</div>'
                f'<div class="theme-share"><span class="theme-count">{esc(count)} · {esc(share)}</span>'
                f"{meter}</div></li>"
            )
        body = (
            f'<ol class="theme-list" aria-label="{esc(ctx.t("theme"))}">{"".join(themes)}</ol>'
            if themes
            else _empty(ctx.t("no_data"))
        )
    return f'<p class="chart-caption">{esc(sample_note)}</p>{body}'


def _metric_rows(metrics: Sequence[Mapping[str, Any]], ctx: RenderContext) -> str:
    if not metrics:
        return f'<p class="empty-state">{esc(ctx.t("no_data"))}</p>'
    values = [metric["value"] for metric in metrics]
    units = {metric["unit"] for metric in metrics}
    numeric = [float(value) for value in values if _is_number(value)]
    comparable = len(units) == 1 and len(numeric) >= 2
    unit = next(iter(units)) if len(units) == 1 else ""
    whole_counts = comparable and all(float(value).is_integer() for value in numeric)
    maximum = max(numeric, default=0.0)
    contexts = {metric_context(metric, ctx) for metric in metrics}
    shared_context = (
        f'<p class="chart-caption">{esc(next(iter(contexts)))}</p>' if len(contexts) == 1 else ""
    )
    rows: list[str] = []
    for metric in metrics:
        value = metric["value"]
        mark = ""
        if _is_number(value) and comparable:
            label = f'{display_metric_label(metric, ctx)}: {metric_text(metric, ctx)}'
            if unit == "%":
                mark = _meter(float(value) / 100, label)
            elif whole_counts and maximum > 0:
                mark = _bar(float(value) / maximum, label)
        rows.append(
            '<div class="metric-row"><dt>'
            + esc(display_metric_label(metric, ctx))
            + metric_tags(metric, ctx)
            + (
                ""
                if shared_context
                else f'<span class="metric-context">{esc(metric_context(metric, ctx))}</span>'
            )
            + "</dt>"
            + f'<dd class="{"is-missing" if value is None else ""}">{esc(metric_text(metric, ctx))}'
            + f"{comparison_html(metric, ctx)}</dd>"
            + mark
            + "</div>"
        )
    return (
        shared_context
        + f'<dl class="metric-list">{"".join(rows)}</dl>'
        + definitions_details(metrics, ctx)
    )


def render_engagement(report: Mapping[str, Any], ctx: RenderContext) -> str:
    engagement = report["engagement"]
    groups = (
        (ctx.t("ratings"), engagement["ratings"]),
        (ctx.t("modes"), engagement["learning_modes"]),
        (ctx.t("activity"), engagement["activity"]),
    )
    cards = "".join(
        f'<article class="note-card"><h3>{esc(title)}</h3>{_metric_rows(metrics, ctx)}</article>'
        for title, metrics in groups
    )
    return f'<div class="note-grid">{cards}</div>'


def render_audience(report: Mapping[str, Any], ctx: RenderContext) -> str:
    audience = report["audience"]
    if not audience["dimensions"]:
        return _empty(audience["note"])
    dimensions: list[str] = []
    for dimension in audience["dimensions"]:
        rows = ""
        for segment in dimension["segments"]:
            share = _format_share(segment["share"], ctx)
            count = _with_unit(f'{segment["count"]:,}', ctx.t("learner_unit"))
            rows += (
                f'<li class="seg-row"><span>{esc(segment["label"])}</span>'
                + _meter(segment["share"] or 0.0, f'{segment["label"]}: {share}')
                + f'<span class="seg-value">{esc(count)} · {esc(share)}</span></li>'
            )
        dimensions.append(
            '<article class="dimension">'
            f'<h3>{esc(dimension["name"])}</h3><ul class="seg-list">{rows}</ul>'
            f'<p class="implication"><strong>{esc(ctx.t("teaching_implication"))}：</strong>'
            f'{esc(dimension["teaching_implication"])}</p></article>'
        )
    return "".join(dimensions) + f'<p class="callout is-privacy">{esc(audience["note"])}</p>'


def render_recommendations(report: Mapping[str, Any], ctx: RenderContext) -> str:
    cards: list[str] = []
    for index, recommendation in enumerate(report["recommendations"], start=1):
        priority = recommendation["priority"]
        confidence = recommendation["confidence"]
        cards.append(
            '<article class="rec">'
            '<div class="rec-header">'
            f'<span class="badge-index" aria-hidden="true">{index}</span>'
            f'<h3>{esc(recommendation["title"])}</h3>'
            '<div class="rec-pills">'
            f'<span class="pill is-plain prio-{esc(priority)}">{esc(ctx.enum(PRIORITY_LABELS, priority))}</span>'
            f'<span class="pill is-plain conf-{esc(confidence)}">{esc(ctx.enum(CONFIDENCE_LABELS, confidence))}</span>'
            "</div></div>"
            f'<div class="rec-action"><span class="rec-label">{esc(ctx.t("action"))}</span>'
            f'<p>{esc(recommendation["action"])}</p></div>'
            '<dl class="rec-body">'
            f'<div><dt class="rec-label">{esc(ctx.t("observation"))}</dt><dd>{esc(recommendation["observation"])}</dd></div>'
            f'<div><dt class="rec-label">{esc(ctx.t("interpretation"))}</dt><dd>{esc(recommendation["interpretation"])}</dd></div>'
            f'<div><dt class="rec-label">{esc(ctx.t("validation"))}</dt><dd>{esc(recommendation["validation"])}</dd></div>'
            "</dl>"
            + render_evidence(recommendation["evidence"], ctx)
            + "</article>"
        )
    return f'<div class="rec-list">{"".join(cards)}</div>'


def render_methods(report: Mapping[str, Any], ctx: RenderContext) -> str:
    quality = report["data_quality"]
    limitations = list(quality["limitations"])
    if "summary" not in resolve_sections(report):
        # Caveats shown with the summary must survive when a teacher hides it.
        limitations += [
            item
            for item in report["overview"]["executive_summary"]["critical_limitations"]
            if item not in limitations
        ]
    groups = [
        (ctx.t("coverage"), quality["coverage_notes"]),
        (ctx.t("limitations"), limitations),
        (ctx.t("privacy"), quality["privacy_notes"]),
    ]
    adjustments = quality.get("teacher_adjustments", [])
    if adjustments:
        groups.insert(0, (ctx.t("teacher_adjustments"), adjustments))
    cards = "".join(
        f'<article class="note-card"><h3>{esc(title)}</h3>{_list_html(items, ctx.t("no_data"))}</article>'
        for title, items in groups
    )

    unavailable_html = ""
    if quality["unavailable_metrics"]:
        rows = "".join(
            "<tr><th scope=\"row\">"
            + esc(
                ctx.t("completion_rate")
                if item["key"].endswith("completion_proxy")
                and not _is_teacher_defined(item["key"], ctx)
                else item["label"]
            )
            + f'</th><td>{esc(item["reason"])}</td></tr>'
            for item in quality["unavailable_metrics"]
        )
        unavailable_html = (
            f'<h3 class="subsection-heading">{esc(ctx.t("unavailable_metrics"))}</h3>'
            '<div class="table-wrap"><table><thead><tr>'
            f'<th scope="col">{esc(ctx.t("metric"))}</th><th scope="col">{esc(ctx.t("reason"))}</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    ordered = [key for key in ctx.metrics if key in ctx.definitions]
    ordered += [key for key in sorted(ctx.definitions) if key not in ctx.metrics]
    separator = "；" if ctx.is_zh else "; "
    definition_rows = ""
    for key in ordered:
        item = ctx.definitions[key]
        probe = {**item, "key": key, "is_approximate": False}
        definition_rows += (
            f'<tr><th scope="row">{esc(display_metric_label(probe, ctx))}{metric_tags(probe, ctx)}</th>'
            f'<td>{esc(item["definition"])}</td><td>{esc(item["unit"])}</td>'
            f'<td>{separator.join(esc(note) for note in item["source_notes"])}</td></tr>'
        )
    definitions = (
        f'<h3 class="subsection-heading">{esc(ctx.t("definitions"))}</h3>'
        '<div class="table-wrap"><table><thead><tr>'
        f'<th scope="col">{esc(ctx.t("metric"))}</th><th scope="col">{esc(ctx.t("definition"))}</th>'
        f'<th scope="col">{esc(ctx.t("unit"))}</th><th scope="col">{esc(ctx.t("source_notes"))}</th>'
        f"</tr></thead><tbody>{definition_rows}</tbody></table></div>"
    )
    return f'<div class="note-grid">{cards}</div>{unavailable_html}{definitions}'


def render_operations(report: Mapping[str, Any], ctx: RenderContext) -> str:
    operations = report["operations"]
    return (
        f'<p class="callout is-privacy">{esc(operations["note"])}</p>'
        '<div class="kpi-grid" style="margin-top:1.25rem">'
        + "".join(render_kpi(metric, ctx) for metric in operations["metrics"])
        + "</div>"
    )


def _render_bars_block(block: Mapping[str, Any], ctx: RenderContext) -> str:
    metrics = block["metrics"]
    numeric = [float(metric["value"]) for metric in metrics if _is_number(metric["value"])]
    unit = metrics[0]["unit"]
    scale = 100.0 if unit == "%" else max(numeric, default=0.0)
    rows = ""
    for position, metric in enumerate(metrics, start=1):
        value = metric["value"]
        label = display_metric_label(metric, ctx)
        text = metric_text(metric, ctx)
        fraction = (float(value) / scale if scale > 0 else 0.0) if _is_number(value) else None
        rows += (
            '<li class="path-row">'
            f'<div class="path-stage"><span class="path-index" aria-hidden="true">{position}</span>'
            f"<span>{esc(label)}{metric_tags(metric, ctx)}</span></div>"
            + _bar(fraction, f"{label}: {text}")
            + f'<div class="path-value{" is-missing" if value is None else ""}">{esc(text)}</div>'
            + (
                f'<div class="path-note">{esc(comparison_text(metric, ctx))}</div>'
                if comparison_text(metric, ctx)
                else ""
            )
            + "</li>"
        )
    scopes = {metric["time_scope"]["label"] for metric in metrics}
    caption_parts = [f'{ctx.t("unit")}：{unit}'] if unit else []
    if len(scopes) == 1:
        caption_parts.append(next(iter(scopes)))
    return (
        '<figure class="chart">'
        f'<figcaption class="chart-caption">{esc(" · ".join(caption_parts))}</figcaption>'
        f'<ol class="path">{rows}</ol></figure>'
        + definitions_details(metrics, ctx)
    )


def _render_table_block(block: Mapping[str, Any], ctx: RenderContext) -> str:
    head = "".join(f'<th scope="col">{esc(column)}</th>' for column in block["columns"])
    rows = ""
    for row in block["rows"]:
        cells = ""
        for cell in row:
            if cell is None:
                cells += f'<td class="is-missing">{esc(ctx.t("no_data_short"))}</td>'
            elif _is_number(cell):
                cells += f'<td class="num">{esc(_format_number(cell))}</td>'
            else:
                cells += f"<td>{esc(cell)}</td>"
        rows += f"<tr>{cells}</tr>"
    return (
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p class="source-note">{esc(block["source_note"])}</p>'
    )


def render_custom_section(section: Mapping[str, Any], ctx: RenderContext) -> str:
    blocks: list[str] = []
    for block in section["blocks"]:
        kind = block["type"]
        title = f'<h3 class="chart-title">{esc(block["title"])}</h3>' if "title" in block else ""
        if kind == "text":
            paragraphs = [part.strip() for part in block["body"].split("\n") if part.strip()]
            body = '<div class="prose">' + "".join(f"<p>{esc(part)}</p>" for part in paragraphs) + "</div>"
        elif kind == "callout":
            body = f'<aside class="callout">{esc(block["body"])}</aside>'
        elif kind == "metrics":
            body = '<div class="kpi-grid">' + "".join(render_kpi(metric, ctx) for metric in block["metrics"]) + "</div>"
        elif kind == "bars":
            body = _render_bars_block(block, ctx)
        else:
            body = _render_table_block(block, ctx)
        blocks.append(f'<div class="block block-{esc(kind)}">{title}{body}</div>')
    return "".join(blocks)


SECTION_RENDERERS = {
    "summary": render_summary,
    "kpis": render_kpis,
    "learning_path": render_learning_path,
    "lessons": render_lessons,
    "followups": render_followups,
    "engagement": render_engagement,
    "audience": render_audience,
    "recommendations": render_recommendations,
    "methods": render_methods,
    "operations": render_operations,
}


def _section_copy(section_id: str, ctx: RenderContext) -> tuple[str, str, str]:
    """Return eyebrow, title and description after applying teacher overrides."""
    if section_id.startswith("custom:"):
        section = next(
            item
            for item in ctx.report["custom_sections"]
            if item["id"] == section_id.split(":", 1)[1]
        )
        eyebrow, title, description = ctx.t("custom_eyebrow"), section["title"], section.get("description", "")
    else:
        eyebrow, title, description = ctx.strings["sections"][section_id]
    override = ctx.presentation.get("section_titles", {}).get(section_id, {})
    return eyebrow, override.get("title", title), override.get("description", description)


def render_body(report: Mapping[str, Any], ctx: RenderContext) -> tuple[str, str]:
    """Render visible sections in order and the matching table of contents."""
    sections: list[str] = []
    toc: list[str] = []
    for index, section_id in enumerate(resolve_sections(report), start=1):
        eyebrow, title, description = _section_copy(section_id, ctx)
        if section_id.startswith("custom:"):
            section = next(
                item
                for item in report["custom_sections"]
                if item["id"] == section_id.split(":", 1)[1]
            )
            body = render_custom_section(section, ctx)
            toc_label = title
        else:
            body = SECTION_RENDERERS[section_id](report, ctx)
            toc_label = eyebrow
        dom_id = "sec-" + section_id.replace(":", "-").replace("_", "-")
        description_html = (
            f'<p class="section-description">{esc(description)}</p>' if description else ""
        )
        sections.append(
            f'<section class="section" id="{esc(dom_id)}" data-section="{esc(section_id)}" '
            f'aria-labelledby="{esc(dom_id)}-heading">'
            '<div class="section-heading"><div class="section-eyebrow">'
            f'<span class="section-index">{index:02d}</span><span>{esc(eyebrow)}</span></div>'
            f'<h2 id="{esc(dom_id)}-heading">{esc(title)}</h2>{description_html}</div>'
            f"{body}</section>"
        )
        toc.append(
            f'<li><a href="#{esc(dom_id)}"><span class="toc-index">{index:02d}</span>'
            f"<span>{esc(toc_label)}</span></a></li>"
        )
    toc_html = f'<div class="toc-title">{esc(ctx.t("toc"))}</div><ol>{"".join(toc)}</ol>'
    return "".join(sections), toc_html


def _check_template_assets(template: str, path: Path) -> None:
    """Allow only embedded (data:) resources and in-page anchors in a template."""
    references = [
        next(group for group in match.groups() if group is not None)
        for match in ASSET_ATTRIBUTE.finditer(template)
    ]
    references += CSS_URL.findall(template)
    for reference in references:
        value = reference.strip()
        if value and not value.lower().startswith(("data:", "#", "{{")):
            raise ReportError(
                f"template {path} references {value[:60]!r}; reports must be self-contained, "
                "so embed resources as data: URIs"
            )
    if re.search(r"srcset\s*=", template, re.IGNORECASE):
        # A srcset lists several candidates; one embedded image in `src` is enough.
        raise ReportError(
            f"template {path} uses srcset; reports must be self-contained, "
            "so use a single src with a data: URI"
        )
    if "@import" in template.lower():
        raise ReportError(f"template {path} uses @import; reports must be self-contained")
    if re.search(r"""http-equiv\s*=\s*["']?\s*refresh""", template, re.IGNORECASE):
        raise ReportError(
            f"template {path} uses a meta refresh; reports must be self-contained"
        )


def render_report(report: Mapping[str, Any], template_path: Path | None = None) -> str:
    meta = report["meta"]
    ctx = RenderContext(report)
    brand = meta.get("brand", {})
    theme = ctx.presentation.get("theme", DEFAULT_THEME)
    accent = _safe_accent(brand.get("accent_color"), theme)
    organization = brand.get("organization_name", "")
    organization_html = (
        f'<span class="brand-divider" aria-hidden="true">/</span><span>{esc(organization)}</span>'
        if organization
        else ""
    )
    period = meta["period"]
    source_name = ctx.strings["source_names"].get(meta["source_kind"], meta["source_kind"])
    timezone_label = meta["timezone"]
    if ctx.is_zh and timezone_label == "Asia/Shanghai":
        timezone_label = "中国标准时间（Asia/Shanghai）"
    report_meta = "".join(
        (
            f'<span><strong>{esc(ctx.t("period"))}</strong>{esc(period["label"])}</span>',
            f'<span><strong>{esc(ctx.t("generated"))}</strong>{esc(_format_generated_at(meta["generated_at"], ctx.is_zh))}</span>',
            f'<span><strong>{esc(ctx.t("timezone"))}</strong>{esc(timezone_label)}</span>',
            f'<span><strong>{esc(ctx.t("source"))}</strong>{esc(source_name)}</span>',
        )
    )
    path = template_path or TEMPLATE_PATH
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"cannot read template {path}: {exc}") from exc
    _check_template_assets(template, path)

    body, toc = render_body(report, ctx)
    replacements = {
        "{{LANG}}": esc(meta["language"]),
        "{{THEME}}": esc(theme),
        "{{DENSITY}}": esc(ctx.presentation.get("density", "comfortable")),
        "{{COLOR_SCHEME}}": THEMES[theme]["scheme"],
        "{{COURSE_TITLE}}": esc(meta["course_title"]),
        "{{TITLE_SUFFIX}}": esc(ctx.t("title_suffix")),
        "{{ACCENT_COLOR}}": accent,
        "{{BRAND_LOGO}}": _brand_logo(ctx),
        "{{ORGANIZATION_NAME}}": organization_html,
        "{{SKIP_TEXT}}": esc(ctx.t("skip")),
        "{{TOC_LABEL}}": esc(ctx.t("toc")),
        "{{META_LABEL}}": esc(ctx.t("meta_label")),
        "{{REPORT_SUBTITLE}}": esc(ctx.presentation.get("subtitle", ctx.t("subtitle"))),
        "{{FOOTER_TEXT}}": esc(ctx.t("footer")),
        "{{REPORT_META}}": report_meta,
        "{{REPORT_TOC}}": toc,
        "{{REPORT_BODY}}": body,
        "{{CUSTOM_CSS}}": ctx.presentation.get("custom_css", ""),
    }

    found = TEMPLATE_PLACEHOLDER.findall(template)
    missing = sorted(set(replacements) - set(found))
    if missing:
        raise ReportError(f"template {path} is missing placeholder(s): {', '.join(missing)}")
    for single in ("{{REPORT_BODY}}", "{{REPORT_TOC}}", "{{CUSTOM_CSS}}"):
        if found.count(single) != 1:
            raise ReportError(f"template {path} must contain {single} exactly once")

    def replace_placeholder(match: re.Match[str]) -> str:
        placeholder = match.group(0)
        if placeholder not in replacements:
            raise ReportError(f"template has unknown placeholder: {placeholder}")
        return replacements[placeholder]

    return TEMPLATE_PLACEHOLDER.sub(replace_placeholder, template)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render an AI-Shifu course learning report."
    )
    parser.add_argument("--input", required=True, type=Path, help="report JSON (schema 1.0 or 1.1)")
    parser.add_argument("--output", type=Path, help="self-contained HTML output")
    parser.add_argument(
        "--template",
        type=Path,
        help="teacher-specific copy of assets/report-template.html (default: bundled template)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate schema, semantics, and privacy without rendering",
    )
    args = parser.parse_args(argv)
    if not args.validate_only and args.output is None:
        parser.error("--output is required unless --validate-only is used")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = validate_report(load_json(args.input))
        if args.validate_only:
            print(f"Valid report data: {args.input}")
            return 0
        rendered = render_report(report, args.template)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Rendered report: {args.output}")
        return 0
    except (ReportError, OSError) as exc:
        print(f"Report validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
