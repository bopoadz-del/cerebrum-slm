"""Unsupported figures are blocked. The verdict does not call a model."""

from __future__ import annotations

import ast
import inspect
import unittest

from src.retrieval.context import context_from_chunks
from src.retrieval.grounding import grounding_gate


def _context(text: str, source_id: str = "src-1"):
    return context_from_chunks([{"chunk_id": source_id, "text": text}])


class GroundingGateTests(unittest.TestCase):
    def test_supported_figure_passes_and_is_logged(self) -> None:
        with self.assertLogs("src.retrieval.grounding", level="INFO") as captured:
            verdict = grounding_gate(
                "the recorded value is 4",
                _context("recorded value 4"),
                cited_source_ids=("src-1",),
            )
        self.assertEqual(verdict.status, "PASS")
        self.assertEqual(verdict.answer, "the recorded value is 4")
        self.assertIsNone(verdict.reason)
        self.assertTrue(any("status=PASS" in line for line in captured.output))

    def test_unsupported_figure_is_blocked_answer_null(self) -> None:
        with self.assertLogs("src.retrieval.grounding", level="INFO") as captured:
            verdict = grounding_gate(
                "the recorded value is 9",
                _context("recorded value 4"),
                cited_source_ids=("src-1",),
            )
        self.assertEqual(verdict.status, "BLOCKED")
        self.assertIsNone(verdict.answer)
        self.assertEqual(verdict.reason, "unsupported figure: 9")
        self.assertTrue(any("status=BLOCKED" in line for line in captured.output))

    def test_larger_number_does_not_support_a_shorter_one(self) -> None:
        verdict = grounding_gate(
            "use 10",
            _context("use 100"),
            cited_source_ids=("src-1",),
        )
        self.assertEqual(verdict.status, "BLOCKED")
        self.assertIsNone(verdict.answer)

    def test_formula_return_supports_its_figure(self) -> None:
        verdict = grounding_gate(
            "result 8",
            _context("no digits here"),
            formula_result={"value": 8},
            cited_source_ids=("src-1",),
        )
        self.assertEqual(verdict.status, "PASS")
        self.assertEqual(verdict.answer, "result 8")

    def test_figure_without_a_source_id_is_blocked(self) -> None:
        verdict = grounding_gate(
            "result 4",
            _context("result 4"),
            cited_source_ids=(),
        )
        self.assertEqual(verdict.status, "BLOCKED")
        self.assertIsNone(verdict.answer)
        self.assertIn("source id", verdict.reason or "")

    def test_same_inputs_are_deterministic(self) -> None:
        context = _context("value 4")
        first = grounding_gate("value 4", context, cited_source_ids=("src-1",))
        second = grounding_gate("value 4", context, cited_source_ids=("src-1",))
        self.assertEqual(first, second)

    def test_verdict_imports_no_model(self) -> None:
        source = inspect.getsource(inspect.getmodule(grounding_gate))
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        banned = ("openai", "anthropic", "transformers", "langchain")
        self.assertFalse(any(any(word in name for word in banned) for name in imports))
        for name in inspect.signature(grounding_gate).parameters:
            self.assertNotIn("model", name)


if __name__ == "__main__":
    unittest.main()
