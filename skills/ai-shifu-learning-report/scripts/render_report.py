#!/usr/bin/env python3
"""Validate and render an AI-Shifu single-course learning report.

This module intentionally uses only the Python standard library. The JSON is
the factual artifact; the generated HTML is an escaped, self-contained view of
that exact data.
"""

from __future__ import annotations

import argparse
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

VALID_ACCENT = re.compile(r"^#[0-9A-Fa-f]{6}$")
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
        "title_suffix": "课程学习报告",
        "skip": "跳到报告正文",
        "subtitle": "课程学习报告 · 面向教学管理者与老师",
        "footer": "本报告由 AI-Shifu Learning Report 根据脱敏聚合数据生成。请结合课程设计与教学现场进行判断。",
        "period": "报告范围",
        "generated": "生成时间",
        "timezone": "时区",
        "source": "数据来源",
        "management": "管理结论",
        "management_desc": "先回答需要关注什么、为什么，以及下一步优先做什么。",
        "overall_health": "总体判断",
        "conclusion": "结论",
        "critical_limits": "关键限制",
        "kpis": "核心指标",
        "learning_path": "学习路径",
        "learning_path_desc": "按课程顺序观察触达，不把记录中的“进行中”直接解释为真实卡课。",
        "lesson_health": "课节健康度",
        "lesson_health_desc": "结合触达、反馈与追问信号定位值得验证的课节。",
        "lesson": "课节",
        "evidence": "证据",
        "followups": "追问主题",
        "followups_desc": "只展示最近受审计样本的聚合主题和去识别化意图，不保留原文。",
        "sample": "抽样说明",
        "theme": "主题",
        "intent": "学习意图摘要",
        "count_share": "数量 / 占比",
        "engagement": "评分与听读偏好",
        "engagement_desc": "分开呈现反馈、学习方式和活跃状态，避免把不同信号混作同一指标。",
        "ratings": "评分",
        "modes": "听读偏好",
        "activity": "活跃状态",
        "audience": "学员画像",
        "audience_desc": "仅展示名称映射明确的聚合分布。",
        "segment": "分组",
        "count": "人数",
        "share": "占比",
        "teaching_implication": "教学含义",
        "recommendations": "教学建议",
        "recommendations_desc": "每条建议都把观察、解释、置信度、行动与验证方法连在一起。",
        "observation": "观察",
        "interpretation": "解释",
        "action": "建议行动",
        "validation": "验证方法",
        "methods": "口径与数据质量",
        "methods_desc": "说明指标如何定义、哪些数据不可用，以及结论应如何解读。",
        "coverage": "数据覆盖",
        "limitations": "限制",
        "privacy": "隐私处理",
        "unavailable_metrics": "不可用指标",
        "metric": "指标",
        "reason": "原因",
        "definitions": "指标口径",
        "definition": "定义",
        "unit": "单位",
        "source_notes": "来源与注意事项",
        "metric_details": "口径与来源",
        "proxy_fraction": "代理分子 / 分母",
        "zero_followups": "查询成功：最近受审计样本中没有追问。",
        "operations": "经营与积分附录",
        "operations_desc": "仅因用户明确要求而包含，不作为教学效果证据。",
        "no_data": "暂无可靠数据",
        "not_collected": "本次未采集",
        "source_names": {"live": "AI 师傅平台", "supplied": "用户提供", "synthetic": "合成数据"},
    },
    "en": {
        "title_suffix": "Course Learning Report",
        "skip": "Skip to report",
        "subtitle": "Course learning report · for teaching managers and teachers",
        "footer": "Generated by AI-Shifu Learning Report from privacy-safe aggregate data. Interpret findings alongside course design and teaching context.",
        "period": "Reporting period",
        "generated": "Generated",
        "timezone": "Timezone",
        "source": "Source",
        "management": "Management conclusions",
        "management_desc": "What needs attention, why it matters, and what to do next.",
        "overall_health": "Overall assessment",
        "conclusion": "Conclusion",
        "critical_limits": "Critical limitations",
        "kpis": "Core metrics",
        "learning_path": "Learning path",
        "learning_path_desc": "Ordered reach without treating a recorded in-progress state as proof of blockage.",
        "lesson_health": "Lesson health",
        "lesson_health_desc": "Use reach, feedback, and follow-up signals to prioritize investigation.",
        "lesson": "Lesson",
        "evidence": "Evidence",
        "followups": "Follow-up themes",
        "followups_desc": "Only aggregate themes and de-identified intents from the latest audited sample are shown.",
        "sample": "Sample",
        "theme": "Theme",
        "intent": "Intent summary",
        "count_share": "Count / share",
        "engagement": "Ratings and read/listen preference",
        "engagement_desc": "Feedback, learning mode, and activity are kept as separate signals.",
        "ratings": "Ratings",
        "modes": "Read/listen preference",
        "activity": "Activity state",
        "audience": "Audience",
        "audience_desc": "Only aggregate distributions with a trusted name mapping are shown.",
        "segment": "Segment",
        "count": "Count",
        "share": "Share",
        "teaching_implication": "Teaching implication",
        "recommendations": "Teaching recommendations",
        "recommendations_desc": "Each recommendation connects observation, interpretation, confidence, action, and validation.",
        "observation": "Observation",
        "interpretation": "Interpretation",
        "action": "Action",
        "validation": "Validation method",
        "methods": "Definitions and data quality",
        "methods_desc": "How metrics are defined, what is unavailable, and how to interpret the findings.",
        "coverage": "Coverage",
        "limitations": "Limitations",
        "privacy": "Privacy handling",
        "unavailable_metrics": "Unavailable metrics",
        "metric": "Metric",
        "reason": "Reason",
        "definitions": "Metric definitions",
        "definition": "Definition",
        "unit": "Unit",
        "source_notes": "Source notes",
        "metric_details": "Definition and source",
        "proxy_fraction": "Proxy numerator / denominator",
        "zero_followups": "Query succeeded: no follow-up questions were observed in the latest audited sample.",
        "operations": "Operations and credits appendix",
        "operations_desc": "Included only at the user's explicit request and not used as evidence of teaching effectiveness.",
        "no_data": "No reliable data",
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


def validate_semantics(report: Mapping[str, Any]) -> None:
    definitions = report["metric_definitions"]
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

    completion_metrics = [
        (key, metric) for key, metric in metrics.items() if key.endswith("completion_proxy")
    ]
    if len(completion_metrics) != 1:
        raise ReportError(
            "report must contain exactly one metric whose key ends with 'completion_proxy'"
        )
    completion_key, completion = completion_metrics[0]
    if completion["value"] is not None:
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

    try:
        datetime.fromisoformat(report["meta"]["generated_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportError("$.meta.generated_at: expected an ISO 8601 date-time") from exc

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


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _safe_accent(value: Any) -> str:
    fallback = "#5B5BD6"
    if not isinstance(value, str) or VALID_ACCENT.fullmatch(value) is None:
        return fallback
    contrast_with_white = 1.05 / (_relative_luminance(value) + 0.05)
    return value if contrast_with_white >= 4.5 else fallback


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


def _enum_label(mapping: Mapping[str, tuple[str, str]], value: str, is_zh: bool) -> str:
    labels = mapping.get(value)
    return labels[0 if is_zh else 1] if labels else value


def _format_number(value: int | float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_share(value: int | float | None, strings: Mapping[str, Any]) -> str:
    if value is None:
        return str(strings["no_data"])
    return f"{value:.1%}"


def format_metric_value(metric: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    value = metric["value"]
    if value is None:
        return esc(strings["no_data"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        rendered = _format_number(value)
    else:
        rendered = esc(value)
    unit = metric["unit"]
    if unit:
        separator = "" if unit in {"%", "分", "人", "次", "条", "节"} else " "
        rendered += separator + esc(unit)
    if metric["is_approximate"]:
        rendered += f'<span class="approx-tag">{esc(DATA_QUALITY_LABELS["approximate"][0 if strings is TEXT["zh"] else 1])}</span>'
    return rendered


def _list_html(items: Iterable[str], empty_text: str) -> str:
    values = list(items)
    if not values:
        return f'<p class="empty-state">{esc(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in values) + "</ul>"


def _section_heading(index: int, title: str, description: str, heading_id: str) -> str:
    return (
        '<div class="section-heading"><div>'
        f'<span class="section-index">{index:02d}</span>'
        f'<h2 id="{esc(heading_id)}">{esc(title)}</h2>'
        f'<p class="section-description">{esc(description)}</p>'
        "</div></div>"
    )


def render_summary(report: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    summary = report["overview"]["executive_summary"]
    conclusions = "".join(
        '<article class="conclusion-card">'
        f'<strong>{esc(strings["conclusion"])} {index}</strong><p>{esc(item)}</p>'
        "</article>"
        for index, item in enumerate(summary["conclusions"], start=1)
    )
    limitations = summary["critical_limitations"]
    limitation_html = ""
    if limitations:
        limitation_html = (
            '<aside class="limitation-callout" aria-label="'
            + esc(strings["critical_limits"])
            + '"><strong>'
            + esc(strings["critical_limits"])
            + "：</strong> "
            + "；".join(esc(item) for item in limitations)
            + "</aside>"
        )
    kpis = "".join(render_kpi(metric, strings) for metric in report["overview"]["kpis"])
    return (
        '<section class="section summary-band" aria-labelledby="summary-heading">'
        '<div class="section-heading"><div><span class="section-index">01</span>'
        f'<h2 id="summary-heading">{esc(strings["management"])}</h2>'
        f'<p class="section-description">{esc(strings["management_desc"])}</p>'
        "</div></div>"
        '<div class="health-line"><span class="health-label">'
        + esc(strings["overall_health"])
        + '</span><span class="health-value">'
        + esc(summary["overall_health"])
        + "</span></div>"
        + f'<div class="conclusion-grid">{conclusions}</div>'
        + limitation_html
        + f'<h3 style="margin:26px 0 13px">{esc(strings["kpis"])}</h3>'
        + f'<div class="kpi-grid">{kpis}</div>'
        + "</section>"
    )


def render_kpi(metric: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    quality = _enum_label(
        DATA_QUALITY_LABELS, metric["data_quality"], strings is TEXT["zh"]
    )
    scope = metric["time_scope"]["label"]
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    fraction = ""
    if numerator is not None and denominator is not None:
        fraction = (
            f'<span class="proxy-fraction">{esc(strings["proxy_fraction"])}：'
            f'{esc(_format_number(numerator))} / {esc(_format_number(denominator))}</span>'
        )
    return (
        '<article class="kpi-card">'
        f'<span class="kpi-label">{esc(metric["label"])}</span>'
        f'<span class="kpi-value">{format_metric_value(metric, strings)}</span>'
        + fraction
        + f'<span class="kpi-meta">{esc(scope)} · {esc(quality)}</span>'
        + render_metric_details(metric, strings)
        + "</article>"
    )


def render_metric_details(metric: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    notes = "；".join(esc(note) for note in metric["source_notes"])
    return (
        '<details class="metric-details"><summary>'
        + esc(strings["metric_details"])
        + '</summary><div class="details-body"><p>'
        + esc(metric["definition"])
        + "</p><p>"
        + notes
        + "</p></div></details>"
    )


def render_learning_path(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    stages = report["overview"]["learning_path"]
    numeric = [
        float(stage["metric"]["value"])
        for stage in stages
        if isinstance(stage["metric"]["value"], (int, float))
        and not isinstance(stage["metric"]["value"], bool)
    ]
    maximum = max(numeric, default=0.0)
    rows: list[str] = []
    for stage in stages:
        metric = stage["metric"]
        value = metric["value"]
        if isinstance(value, (int, float)) and not isinstance(value, bool) and maximum > 0:
            width = max(0.0, min(100.0, float(value) / maximum * 100))
            bar = (
                f'<div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>'
            )
        else:
            bar = '<div class="bar-track"><div class="bar-fill" style="width:0"></div></div>'
        value_label = format_metric_value(metric, strings)
        quality_label = _enum_label(
            DATA_QUALITY_LABELS, metric["data_quality"], strings is TEXT["zh"]
        )
        source_summary = "；".join(metric["source_notes"])
        path_note = (
            f'{stage["note"]} · {metric["time_scope"]["label"]} · '
            f"{quality_label} · {source_summary}"
        )
        aria = (
            f'{stage["stage"]}: {re.sub("<[^>]+>", "", value_label)}. '
            f"{path_note}"
        )
        rows.append(
            f'<div class="path-row" role="img" aria-label="{esc(aria)}">'
            f'<div class="path-stage">{esc(stage["stage"])}</div>{bar}'
            f'<div class="bar-label">{value_label}</div>'
            f'<div class="path-note">{esc(path_note)}</div></div>'
        )
    content = "".join(rows) if rows else f'<div class="empty-state">{esc(strings["no_data"])}</div>'
    return (
        f'<section class="section" aria-labelledby="path-heading">{_section_heading(index, strings["learning_path"], strings["learning_path_desc"], "path-heading")}'
        f'<div class="path-list">{content}</div></section>'
    )


def _metric_rows(metrics: Sequence[Mapping[str, Any]], strings: Mapping[str, Any]) -> str:
    if not metrics:
        return f'<div class="empty-state">{esc(strings["no_data"])}</div>'
    return (
        '<dl class="metric-list">'
        + "".join(_render_metric_row(metric, strings) for metric in metrics)
        + "</dl>"
    )


def _render_metric_row(metric: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    quality = _enum_label(
        DATA_QUALITY_LABELS, metric["data_quality"], strings is TEXT["zh"]
    )
    context = f'{metric["time_scope"]["label"]} · {quality}'
    return (
        '<div class="metric-row"><dt>'
        + esc(metric["label"])
        + f'<span class="metric-context">{esc(context)}</span></dt>'
        + f'<dd>{format_metric_value(metric, strings)}</dd>'
        + render_metric_details(metric, strings)
        + "</div>"
    )


def render_evidence_badges(
    references: Sequence[str],
    metrics: Mapping[str, Mapping[str, Any]],
    strings: Mapping[str, Any],
) -> str:
    return "".join(
        '<span class="evidence-ref">'
        + esc(metrics[reference]["label"])
        + "："
        + format_metric_value(metrics[reference], strings)
        + "</span>"
        for reference in references
    )


def render_lessons(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    cards: list[str] = []
    is_zh = strings is TEXT["zh"]
    metrics = {metric["key"]: metric for _, metric in iter_metrics(report)}
    for lesson in report["lesson_health"]:
        status = lesson["health_status"]
        status_label = _enum_label(HEALTH_LABELS, status, is_zh)
        evidence = render_evidence_badges(lesson["evidence"], metrics, strings)
        cards.append(
            '<article class="lesson-card">'
            '<div class="lesson-card-header"><div>'
            f'<span class="lesson-order">{esc(strings["lesson"])} {lesson["position"]:02d}</span>'
            f'<h3>{esc(lesson["title"])}</h3></div>'
            f'<span class="status-pill is-{esc(status)}">{esc(status_label)}</span></div>'
            '<div class="lesson-card-body">'
            f'<p class="lesson-finding">{esc(lesson["finding"])}</p>'
            + _metric_rows(lesson["metrics"], strings)
            + f'<div class="evidence-list" aria-label="{esc(strings["evidence"])}">{evidence}</div>'
            + "</div></article>"
        )
    content = "".join(cards) if cards else f'<div class="empty-state">{esc(strings["no_data"])}</div>'
    return (
        f'<section class="section" aria-labelledby="lessons-heading">{_section_heading(index, strings["lesson_health"], strings["lesson_health_desc"], "lessons-heading")}'
        f'<div class="lesson-grid">{content}</div></section>'
    )


def render_followups(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    followups = report["engagement"]["follow_up_analysis"]
    status = followups["status"]
    if status == "available":
        sample_size = followups["sample_size"]
        span = followups["effective_span"] or strings["no_data"]
        sample_note = (
            f'{strings["sample"]}：{followups["sampling_rule"]} · '
            f'{sample_size}/{followups["sample_limit"]} · {span}'
        )
        themes: list[str] = []
        for theme in followups["themes"]:
            share = strings["no_data"] if theme["share"] is None else f'{theme["share"]:.1%}'
            lesson_labels = "、".join(theme["lesson_labels"])
            suffix = f" · {lesson_labels}" if lesson_labels else ""
            themes.append(
                '<div class="theme-row" role="listitem">'
                f'<div><h3>{esc(theme["theme"])}</h3><span class="kpi-meta">{esc(suffix.lstrip(" ·"))}</span></div>'
                f'<div class="theme-intent">{esc(theme["intent_summary"])}</div>'
                f'<div class="theme-count">{theme["count"]} · {esc(share)}</div></div>'
            )
        if sample_size == 0:
            body = f'<div class="empty-state">{esc(strings["zero_followups"])}</div>'
        else:
            body = "".join(themes)
    else:
        sample_note = followups["sampling_rule"]
        state_text = strings["not_collected"] if status == "not_collected" else strings["no_data"]
        body = f'<div class="empty-state">{esc(state_text)}</div>'
    return (
        f'<section class="section" aria-labelledby="followups-heading">{_section_heading(index, strings["followups"], strings["followups_desc"], "followups-heading")}'
        f'<p class="sample-note">{esc(sample_note)}</p>'
        f'<div class="theme-list" role="list" aria-label="{esc(strings["followups"])}">{body}</div></section>'
    )


def render_engagement(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    engagement = report["engagement"]
    groups = (
        (strings["ratings"], engagement["ratings"]),
        (strings["modes"], engagement["learning_modes"]),
        (strings["activity"], engagement["activity"]),
    )
    cards = "".join(
        f'<article class="quality-card"><h3>{esc(title)}</h3>{_metric_rows(metrics, strings)}</article>'
        for title, metrics in groups
    )
    return (
        f'<section class="section" aria-labelledby="engagement-heading">{_section_heading(index, strings["engagement"], strings["engagement_desc"], "engagement-heading")}'
        f'<div class="quality-grid">{cards}</div></section>'
    )


def render_audience(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    audience = report["audience"]
    dimensions: list[str] = []
    for dimension in audience["dimensions"]:
        rows = "".join(
            f'<tr><td>{esc(segment["label"])}</td><td>{segment["count"]:,}</td>'
            f'<td>{esc(_format_share(segment["share"], strings))}</td></tr>'
            for segment in dimension["segments"]
        )
        dimensions.append(
            '<article class="audience-dimension">'
            f'<h3>{esc(dimension["name"])}</h3><div class="table-wrap"><table>'
            f'<caption>{esc(dimension["name"])}</caption><thead><tr><th>{esc(strings["segment"])}</th>'
            f'<th>{esc(strings["count"])}</th><th>{esc(strings["share"])}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            f'<p class="audience-implication"><strong>{esc(strings["teaching_implication"])}：</strong> '
            f'{esc(dimension["teaching_implication"])}</p></article>'
        )
    if not dimensions:
        body = f'<div class="empty-state">{esc(audience["note"])}</div>'
    else:
        body = "".join(dimensions) + f'<p class="privacy-callout">{esc(audience["note"])}</p>'
    return (
        f'<section class="section" aria-labelledby="audience-heading">{_section_heading(index, strings["audience"], strings["audience_desc"], "audience-heading")}'
        f'<div>{body}</div></section>'
    )


def render_recommendations(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    is_zh = strings is TEXT["zh"]
    cards: list[str] = []
    metrics = {metric["key"]: metric for _, metric in iter_metrics(report)}
    for recommendation in report["recommendations"]:
        priority = recommendation["priority"]
        confidence = recommendation["confidence"]
        evidence = render_evidence_badges(recommendation["evidence"], metrics, strings)
        cards.append(
            '<article class="recommendation-card">'
            '<div class="recommendation-top">'
            f'<h3>{esc(recommendation["title"])}</h3>'
            f'<span class="priority-pill is-{esc(priority)}">{esc(_enum_label(PRIORITY_LABELS, priority, is_zh))}</span>'
            "</div><dl>"
            f'<div><dt>{esc(strings["observation"])}</dt><dd>{esc(recommendation["observation"])}</dd></div>'
            f'<div><dt>{esc(strings["interpretation"])}</dt><dd>{esc(recommendation["interpretation"])}</dd></div>'
            f'<div><dt>{esc(_enum_label(CONFIDENCE_LABELS, confidence, is_zh))}</dt><dd>'
            f'<span class="confidence-pill is-{esc(confidence)}">{esc(_enum_label(CONFIDENCE_LABELS, confidence, is_zh))}</span></dd></div>'
            f'<div><dt>{esc(strings["action"])}</dt><dd>{esc(recommendation["action"])}</dd></div>'
            f'<div><dt>{esc(strings["validation"])}</dt><dd>{esc(recommendation["validation"])}</dd></div>'
            "</dl>"
            f'<div class="evidence-list" aria-label="{esc(strings["evidence"])}">{evidence}</div>'
            "</article>"
        )
    return (
        f'<section class="section" aria-labelledby="recommendations-heading">{_section_heading(index, strings["recommendations"], strings["recommendations_desc"], "recommendations-heading")}'
        f'<div class="recommendation-grid">{"".join(cards)}</div></section>'
    )


def render_methods(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    quality = report["data_quality"]
    cards = (
        f'<article class="quality-card"><h3>{esc(strings["coverage"])}</h3>{_list_html(quality["coverage_notes"], strings["no_data"])}</article>'
        f'<article class="quality-card"><h3>{esc(strings["limitations"])}</h3>{_list_html(quality["limitations"], strings["no_data"])}</article>'
        f'<article class="quality-card"><h3>{esc(strings["privacy"])}</h3>{_list_html(quality["privacy_notes"], strings["no_data"])}</article>'
    )
    unavailable = quality["unavailable_metrics"]
    if unavailable:
        rows = "".join(
            f'<tr><td>{esc(item["label"])}</td><td>{esc(item["reason"])}</td></tr>'
            for item in unavailable
        )
        unavailable_html = (
            f'<h3 style="margin:24px 0 8px">{esc(strings["unavailable_metrics"])}</h3>'
            '<div class="table-wrap"><table><thead><tr>'
            f'<th>{esc(strings["metric"])}</th><th>{esc(strings["reason"])}</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )
    else:
        unavailable_html = ""

    definition_rows = "".join(
        f'<tr><td>{esc(item["label"])}</td>'
        f'<td>{esc(item["definition"])}</td><td>{esc(item["unit"])}</td>'
        f'<td>{"；".join(esc(note) for note in item["source_notes"])}</td></tr>'
        for _, item in sorted(report["metric_definitions"].items())
    )
    details = (
        '<details><summary>'
        + esc(strings["definitions"])
        + '</summary><div class="details-body table-wrap"><table><thead><tr>'
        + f'<th>{esc(strings["metric"])}</th><th>{esc(strings["definition"])}</th>'
        + f'<th>{esc(strings["unit"])}</th><th>{esc(strings["source_notes"])}</th>'
        + f"</tr></thead><tbody>{definition_rows}</tbody></table></div></details>"
    )
    return (
        f'<section class="section" aria-labelledby="methods-heading">{_section_heading(index, strings["methods"], strings["methods_desc"], "methods-heading")}'
        f'<div class="quality-grid">{cards}</div>{unavailable_html}{details}</section>'
    )


def render_operations(report: Mapping[str, Any], strings: Mapping[str, Any], index: int) -> str:
    operations = report["operations"]
    return (
        f'<section class="section" aria-labelledby="operations-heading">{_section_heading(index, strings["operations"], strings["operations_desc"], "operations-heading")}'
        f'<p class="privacy-callout">{esc(operations["note"])}</p>'
        f'<div class="kpi-grid">{"".join(render_kpi(metric, strings) for metric in operations["metrics"])}</div></section>'
    )


def render_body(report: Mapping[str, Any], strings: Mapping[str, Any]) -> str:
    sections = [
        render_summary(report, strings),
        render_learning_path(report, strings, 2),
        render_lessons(report, strings, 3),
        render_followups(report, strings, 4),
        render_engagement(report, strings, 5),
        render_audience(report, strings, 6),
        render_recommendations(report, strings, 7),
        render_methods(report, strings, 8),
    ]
    if "operations" in report:
        sections.append(render_operations(report, strings, 9))
    return "".join(sections)


def render_report(report: Mapping[str, Any]) -> str:
    meta = report["meta"]
    is_zh, strings = _language(meta)
    brand = meta.get("brand", {})
    accent = _safe_accent(brand.get("accent_color"))
    organization_name = brand.get("organization_name", "AI 师傅" if strings is TEXT["zh"] else "AI-Shifu")
    logo_text = brand.get("logo_text", "AI 师傅" if strings is TEXT["zh"] else "AI-Shifu")
    period = meta["period"]
    source_name = strings["source_names"].get(meta["source_kind"], meta["source_kind"])
    timezone_label = meta["timezone"]
    if is_zh and timezone_label == "Asia/Shanghai":
        timezone_label = "中国标准时间（Asia/Shanghai）"
    report_meta = "".join(
        (
            f'<span><strong>{esc(strings["period"])}：</strong>{esc(period["label"])}</span>',
            f'<span><strong>{esc(strings["generated"])}：</strong>{esc(_format_generated_at(meta["generated_at"], is_zh))}</span>',
            f'<span><strong>{esc(strings["timezone"])}：</strong>{esc(timezone_label)}</span>',
            f'<span><strong>{esc(strings["source"])}：</strong>{esc(source_name)}</span>',
        )
    )
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"cannot read template {TEMPLATE_PATH}: {exc}") from exc
    replacements = {
        "{{LANG}}": esc(meta["language"]),
        "{{COURSE_TITLE}}": esc(meta["course_title"]),
        "{{TITLE_SUFFIX}}": esc(strings["title_suffix"]),
        "{{ACCENT_COLOR}}": accent,
        "{{ORGANIZATION_NAME}}": esc(organization_name),
        "{{LOGO_TEXT}}": esc(logo_text),
        "{{SKIP_TEXT}}": esc(strings["skip"]),
        "{{REPORT_SUBTITLE}}": esc(strings["subtitle"]),
        "{{FOOTER_TEXT}}": esc(strings["footer"]),
        "{{REPORT_META}}": report_meta,
        "{{REPORT_BODY}}": render_body(report, strings),
    }
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
    parser.add_argument("--input", required=True, type=Path, help="schema-version 1.0 JSON")
    parser.add_argument("--output", type=Path, help="self-contained HTML output")
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
        rendered = render_report(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Rendered report: {args.output}")
        return 0
    except (ReportError, OSError) as exc:
        print(f"Report validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
