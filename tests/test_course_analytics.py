from __future__ import annotations

import json
import re
import sqlite3
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "ai-shifu-course-creator"


class CourseAnalyticsTests(unittest.TestCase):
    def test_learner_distribution_remains_queryable_with_aggregate_privacy(self):
        analytics_root = SKILL_ROOT / "references" / "analytics"
        recipes = (analytics_root / "query-recipes.md").read_text(encoding="utf-8")
        recipe = recipes.split("### Recipe 15 —", 1)[1].split("\n## ", 1)[0]
        queries = [
            json.loads(body)
            for body in re.findall(r"--dsl '(\{.*?\})'", recipe, re.DOTALL)
        ]
        self.assertEqual(len(queries), 2, "Discover IDs before querying one distribution")
        discovery, query = queries
        self.assertEqual(discovery["table"], "var_variable_values")
        self.assertEqual(discovery["select"], ["variable_bid"])
        self.assertEqual(discovery["group_by"], ["variable_bid"])
        self.assertNotIn("where", discovery)
        self.assertEqual(
            discovery["aggregate"],
            [{"fn": "count_distinct", "field": "user_bid", "alias": "n"}],
        )
        self.assertEqual(discovery["order_by"], [{"field": "variable_bid", "dir": "asc"}])
        self.assertEqual(discovery["offset"], 0)

        self.assertEqual(query["table"], "var_variable_values")
        self.assertEqual(
            query["where"],
            [{"field": "variable_bid", "op": "=", "value": "<variable_bid>"}],
        )
        self.assertEqual(query["select"], ["value"])
        self.assertEqual(query["group_by"], ["value"])
        self.assertEqual(
            query["aggregate"],
            [{"fn": "count_distinct", "field": "user_bid", "alias": "n"}],
        )
        self.assertIn("privacy-and-presentation.md", recipe)
        guide = (analytics_root / "guide.md").read_text(encoding="utf-8")
        self.assertRegex(guide, r"Learner profile distribution[^\n]*var_variable_values")
        privacy = (analytics_root / "privacy-and-presentation.md").read_text(
            encoding="utf-8"
        )
        policy = privacy.split("## `var_variable_values.value`", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Aggregate only", policy)
        self.assertIn("never paste the raw value list", policy)

    def test_learner_distribution_paging_retains_all_tied_answer_groups(self):
        recipes = (
            SKILL_ROOT / "references" / "analytics" / "query-recipes.md"
        ).read_text(encoding="utf-8")
        recipe = recipes.split("### Recipe 15 —", 1)[1].split("\n## ", 1)[0]
        _, query = [
            json.loads(body)
            for body in re.findall(r"--dsl '(\{.*?\})'", recipe, re.DOTALL)
        ]
        limit = query["limit"]
        self.assertGreater(limit, 0)
        self.assertLessEqual(limit, 1000)

        # Materialized aggregate results isolate the recipe's ordering contract.
        # A database may return tied groups in either source order between pages.
        grouped_rows = (
            [("Most common answer", 8)]
            + [(f"Answer {index:04}", 3) for index in range(2 * limit + 5)]
            + [("Rare answer", 1)]
        )
        sources = []
        for source_rows in (grouped_rows, list(reversed(grouped_rows))):
            source = sqlite3.connect(":memory:")
            self.addCleanup(source.close)
            source.execute("CREATE TABLE grouped_answers (value TEXT, n INTEGER)")
            source.executemany(
                "INSERT INTO grouped_answers (value, n) VALUES (?, ?)", source_rows
            )
            sources.append(source)

        order_by = ", ".join(
            f'"{term["field"]}" {term["dir"].upper()}'
            for term in query["order_by"]
        )
        page_sql = (
            f"SELECT value, n FROM grouped_answers ORDER BY {order_by} "
            "LIMIT ? OFFSET ?"
        )
        offset = query.get("offset", 0)
        paged_rows = []
        page_index = 0
        while True:
            page = sources[page_index % len(sources)].execute(
                page_sql, (limit, offset)
            ).fetchall()
            paged_rows.extend(page)
            if len(page) < limit:
                break
            offset += limit
            page_index += 1

        self.assertEqual(
            len({value for value, _ in paged_rows}),
            len(grouped_rows),
            "Offset pages must not repeat or skip answer groups when counts tie",
        )
        self.assertEqual(paged_rows, grouped_rows)



if __name__ == "__main__":
    unittest.main()
