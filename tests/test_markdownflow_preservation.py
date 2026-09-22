from __future__ import annotations

import unittest
from unittest.mock import patch

from markdown_flow import LLMProvider, MarkdownFlow, ProcessMode


GENERATED_TEXT = "GENERATED_PLACEHOLDER"
IMAGE = "![示意图](https://example.org/diagram.png)"


class RecordingProvider(LLMProvider):
    """Record generation requests without contacting a model or fetching images."""

    def __init__(self):
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages, model=None, temperature=None):
        self.calls.append([message.copy() for message in messages])
        return GENERATED_TEXT

    def stream(self, messages, model=None, temperature=None):
        yield self.complete(messages, model, temperature)


class MarkdownFlowPreservationTests(unittest.TestCase):
    def setUp(self):
        # Fail on accidental network use, including DNS and image fetching.
        for target in (
            "socket.getaddrinfo",
            "socket.create_connection",
            "socket.socket.connect",
            "socket.socket.connect_ex",
        ):
            self.enterContext(
                patch(target, side_effect=AssertionError("Network access is forbidden"))
            )

    def assert_document(self, document, expected_blocks):
        provider = RecordingProvider()
        flow = MarkdownFlow(document=document, llm_provider=provider)
        blocks = flow.get_all_blocks()
        self.assertEqual(len(blocks), len(expected_blocks))

        for index, (block, expected) in enumerate(zip(blocks, expected_blocks)):
            block_type, raw_content, expected_output, expected_calls = expected
            with self.subTest(block=index):
                self.assertEqual(block.block_type.name, block_type)
                self.assertEqual(block.content, raw_content)
                calls_before = len(provider.calls)
                result = flow.process(block_index=index, mode=ProcessMode.COMPLETE)
                pieces = [result] if hasattr(result, "content") else list(result)
                output = "".join(piece.content or "" for piece in pieces)
                self.assertEqual(output, expected_output)
                self.assertEqual(len(provider.calls) - calls_before, expected_calls)

        self.assertEqual(
            len(provider.calls), sum(expected[3] for expected in expected_blocks)
        )
        return provider

    def assert_mixed_content(self, instruction, preserved_text, fixed_output):
        document = f"{instruction}\n\n{preserved_text}"
        provider = self.assert_document(
            document, [("CONTENT", document, GENERATED_TEXT, 1)]
        )
        user_messages = "\n".join(
            message["content"]
            for message in provider.calls[0]
            if message["role"] == "user"
        )
        self.assertIn(instruction, user_messages)
        self.assertIn(fixed_output, user_messages)
        self.assertNotIn("===", user_messages)

    def test_single_line_complete_block_bypasses_provider(self):
        document = "===固定句。==="
        self.assert_document(
            document, [("PRESERVED_CONTENT", document, "固定句。", 0)]
        )

    def test_multiline_complete_block_preserves_paragraphs_without_provider(self):
        document = "!===\n第一行。\n\n第二行。\n!==="
        self.assert_document(
            document,
            [("PRESERVED_CONTENT", document, "第一行。\n\n第二行。", 0)],
        )

    def test_single_line_marker_in_mixed_block_uses_provider(self):
        self.assert_mixed_content("解释本节概念。", "===固定句。===", "固定句。")

    def test_multiline_marker_in_mixed_block_uses_provider(self):
        self.assert_mixed_content(
            "解释本节概念。", "!===\n固定句。\n!===", "固定句。"
        )

    def test_separators_isolate_fixed_material_at_its_original_position(self):
        self.assert_document(
            "先解释。\n\n---\n\n===固定句。===\n\n---\n\n继续解释。",
            [
                ("CONTENT", "先解释。", GENERATED_TEXT, 1),
                ("PRESERVED_CONTENT", "===固定句。===", "固定句。", 0),
                ("CONTENT", "继续解释。", GENERATED_TEXT, 1),
            ],
        )

    def test_interaction_separates_complete_preserved_blocks(self):
        self.assert_document(
            "===问题？===\n\n?[继续]\n\n===结尾。===",
            [
                ("PRESERVED_CONTENT", "===问题？===", "问题？", 0),
                ("INTERACTION", "?[继续]", "?[继续]", 0),
                ("PRESERVED_CONTENT", "===结尾。===", "结尾。", 0),
            ],
        )

    def test_interaction_does_not_split_mixed_content_before_it(self):
        mixed = "解释本节概念。\n\n===固定句。==="
        self.assert_document(
            f"{mixed}\n\n?[继续]\n\n===结尾。===",
            [
                ("CONTENT", mixed, GENERATED_TEXT, 1),
                ("INTERACTION", "?[继续]", "?[继续]", 0),
                ("PRESERVED_CONTENT", "===结尾。===", "结尾。", 0),
            ],
        )

    def test_complete_image_block_outputs_exact_markdown_without_provider(self):
        document = f"==={IMAGE}==="
        self.assert_document(document, [("PRESERVED_CONTENT", document, IMAGE, 0)])

    def test_image_marker_in_mixed_block_uses_provider(self):
        self.assert_mixed_content("解释图片含义。", f"==={IMAGE}===", IMAGE)


if __name__ == "__main__":
    unittest.main()
