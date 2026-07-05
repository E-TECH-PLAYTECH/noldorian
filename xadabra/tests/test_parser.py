from __future__ import annotations

import unittest

from xadabra.parser import (
    find_placeholders,
    normalize_path_input,
    parse_placeholder_inner,
    substitute,
    substitute_for_run,
)


class TestParser(unittest.TestCase):
    def test_name_only(self) -> None:
        ph = parse_placeholder_inner("NAME")
        self.assertEqual(ph.name, "NAME")
        self.assertFalse(ph.secret)
        self.assertIsNone(ph.ptype)
        self.assertIsNone(ph.question)

    def test_friendly_question(self) -> None:
        ph = parse_placeholder_inner("NAME:Friendly question")
        self.assertEqual(ph.question, "Friendly question")
        self.assertIsNone(ph.default)

    def test_question_with_default(self) -> None:
        ph = parse_placeholder_inner("NAME:Question:default")
        self.assertEqual(ph.question, "Question")
        self.assertEqual(ph.default, "default")

    def test_secret(self) -> None:
        ph = parse_placeholder_inner("!API_KEY:Paste the key")
        self.assertTrue(ph.secret)
        self.assertEqual(ph.name, "API_KEY")
        self.assertEqual(ph.question, "Paste the key")

    def test_path_type(self) -> None:
        ph = parse_placeholder_inner("FOLDER|path:Where is the folder?")
        self.assertEqual(ph.name, "FOLDER")
        self.assertEqual(ph.ptype, "path")
        self.assertEqual(ph.question, "Where is the folder?")

    def test_unique_names_order(self) -> None:
        script = "echo {{A}} {{B}} {{A}}"
        names = [p.name for p in find_placeholders(script)]
        self.assertEqual(names, ["A", "B"])

    def test_substitute_masks_secret(self) -> None:
        script = "curl -H 'Auth: {{!API_KEY:Key}}'"
        out = substitute(script, {"API_KEY": "sekrit"}, mask_secrets={"API_KEY"})
        self.assertIn("*****", out)
        self.assertNotIn("sekrit", out)

    def test_substitute_for_run_uses_real_secret(self) -> None:
        script = "echo {{!API_KEY:Key}}"
        out = substitute_for_run(script, {"API_KEY": "sekrit"})
        self.assertIn("sekrit", out)

    def test_repeated_name_same_value(self) -> None:
        script = "echo {{NAME}} and {{NAME}}"
        out = substitute_for_run(script, {"NAME": "x"})
        self.assertEqual(out, "echo x and x")

    def test_path_unescape(self) -> None:
        self.assertEqual(normalize_path_input("/foo/bar\\ baz"), "/foo/bar baz")
        self.assertEqual(normalize_path_input('"/tmp/x"'), "/tmp/x")


if __name__ == "__main__":
    unittest.main()
