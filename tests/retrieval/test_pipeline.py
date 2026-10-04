"""Answers cite Fork source ids. Formulas are called. Outside cites are not emitted."""

from __future__ import annotations

import sys
import types
import unittest

from src.retrieval.fork import FORMULA_MODULE, RETRIEVER_MODULE
from src.retrieval.pipeline import answer


def _install(module_name: str) -> types.ModuleType:
    parts = module_name.split(".")
    parent = ""
    for part in parts:
        name = part if not parent else f"{parent}.{part}"
        if name not in sys.modules:
            module = types.ModuleType(name)
            sys.modules[name] = module
            if parent:
                setattr(sys.modules[parent], part, module)
        parent = name
    return sys.modules[module_name]


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.formula_calls: list[tuple] = []
        retriever = _install(RETRIEVER_MODULE)
        retriever.available = lambda: True
        retriever.retrieve = lambda query, project_id, k=None, intent=None: {
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "doc_id": "doc-1",
                    "formula_id": "formula-2",
                    "clause_id": "clause-9",
                    "text": "stored quantity 4",
                }
            ]
        }
        formulas = _install(FORMULA_MODULE)

        def run_formula(formula_id, params=None):
            self.formula_calls.append((formula_id, params))
            return {"value": 8}

        formulas.run_formula = run_formula

    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)

    def test_answer_cites_only_source_ids_from_attached_context(self) -> None:
        result = answer(
            "quantity",
            "project-7",
            "stored quantity 4",
            sources=("chunk-1", "doc-1"),
            clauses=("clause-9",),
            confidence=0.9,
            task_type="lookup",
        )
        self.assertEqual(result.answer, "stored quantity 4")
        self.assertEqual(result.citations, ("clause-9", "chunk-1", "doc-1"))
        self.assertEqual(result.grounding_status, "PASS")
        self.assertFalse(result.escalated)
        self.assertEqual(self.formula_calls, [])

    def test_formula_is_called_and_its_figure_is_cited(self) -> None:
        result = answer(
            "compute",
            "project-7",
            "computed 8",
            sources=("chunk-1",),
            formula_id="formula-2",
            formula_params={"width": 2},
            confidence=0.9,
            task_type="compute",
        )
        self.assertEqual(self.formula_calls, [("formula-2", {"width": 2})])
        self.assertEqual(result.answer, "computed 8")
        self.assertIn("formula-2", result.citations)
        self.assertIn("chunk-1", result.citations)
        self.assertEqual(result.formula_called, "formula-2")

    def test_formula_id_outside_context_is_not_called(self) -> None:
        result = answer(
            "compute",
            "project-7",
            "computed 8",
            sources=("chunk-1",),
            formula_id="formula-missing",
            confidence=0.9,
            task_type="compute",
        )
        self.assertEqual(self.formula_calls, [])
        self.assertIsNone(result.answer)
        self.assertEqual(result.reason, "unsupported figure: 8")

    def test_citation_outside_context_is_not_emitted(self) -> None:
        result = answer(
            "quantity",
            "project-7",
            "stored quantity 4",
            sources=("chunk-1", "src-not-attached"),
            confidence=0.9,
            task_type="lookup",
        )
        self.assertIsNone(result.answer)
        self.assertEqual(result.citations, ())
        self.assertNotIn("src-not-attached", result.citations)
        self.assertEqual(result.reason, "identifier is not in the attached context")

    def test_empty_context_refuses_citation_and_escalates(self) -> None:
        retriever = sys.modules[RETRIEVER_MODULE]
        retriever.retrieve = lambda *args, **kwargs: {"chunks": []}
        with self.assertLogs("src.policy.escalation", level="INFO") as captured:
            result = answer(
                "quantity",
                "project-7",
                "stored quantity 4",
                sources=("chunk-1",),
                confidence=0.9,
                task_type="lookup",
            )
        self.assertIsNone(result.answer)
        self.assertEqual(result.citations, ())
        self.assertEqual(result.reason, "empty context: no citation is possible")
        self.assertTrue(result.escalated)
        self.assertIn("context_absent", result.escalation_reasons)
        self.assertTrue(any("escalation" in line for line in captured.output))


if __name__ == "__main__":
    unittest.main()
