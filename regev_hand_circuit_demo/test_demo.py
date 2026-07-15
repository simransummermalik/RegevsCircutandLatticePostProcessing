"""Consistency checks for the standalone presentation demo.

The suite intentionally uses only the Python standard library, while retaining
normal unittest/pytest discovery.  It catches presentation drift in component
IDs, the fixed replay, QFT resource statements, links, and interaction hooks.
"""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator


DEMO_DIR = Path(__file__).resolve().parent
DATA_PATH = DEMO_DIR / "demo-data.json"
HTML_PATH = DEMO_DIR / "index.html"

EXPECTED_BUILD_ORDER = [
    "x1",
    "x2",
    "h1",
    "h2",
    "result",
    "aux",
    "modexp1",
    "modexp2",
    "qft1",
    "qft2",
    "measure1",
    "measure2",
]

EXPECTED_REPLAY_SAMPLES = [
    [6, 19],
    [3, 10],
    [16, 16],
    [6, 19],
    [0, 0],
    [16, 16],
    [10, 29],
]


class DemoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.slot_targets: list[str] = []
        self.local_refs: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {name: value for name, value in attrs}
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        accepts = values.get("data-accepts")
        if accepts:
            self.slot_targets.append(accepts)
        for attribute in ("href", "src"):
            reference = values.get(attribute)
            if (
                reference
                and not reference.startswith(("http://", "https://", "#", "data:"))
            ):
                self.local_refs.append(reference)


def walk_json(value: Any) -> Iterator[Any]:
    """Yield every node in a decoded JSON tree."""

    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def semantically_named_value(
    value: Any, key_pattern: re.Pattern[str], expected: Any
) -> bool:
    """Find a value whose normalized key carries the requested meaning."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if key_pattern.search(normalized) and child == expected:
                return True
            if semantically_named_value(child, key_pattern, expected):
                return True
    elif isinstance(value, list):
        return any(
            semantically_named_value(child, key_pattern, expected)
            for child in value
        )
    return False


class DemoDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def test_component_inventory_and_build_order_are_exact(self) -> None:
        components = self.data["components"]
        component_ids = [component["id"] for component in components]
        self.assertEqual(self.data["buildOrder"], EXPECTED_BUILD_ORDER)
        self.assertEqual(len(component_ids), 12)
        self.assertEqual(set(component_ids), set(EXPECTED_BUILD_ORDER))
        self.assertEqual(len(component_ids), len(set(component_ids)))

    def test_concrete_circuit_facts(self) -> None:
        instance = self.data["demoInstance"]
        self.assertEqual(instance["N"], 55)
        self.assertEqual(instance["factors"], [5, 11])
        self.assertEqual(instance["roots"], [2, 3])
        self.assertEqual(instance["circuitBases"], [4, 9])
        self.assertEqual(instance["M"], 32)
        self.assertEqual(instance["dimension"], 2)
        self.assertEqual(instance["exponentQubitsPerRegister"], 5)
        self.assertEqual(instance["resultQubits"], 6)
        self.assertEqual(instance["auxiliaryQubits"], 7)
        self.assertEqual(instance["totalLogicalQubits"], 23)
        self.assertEqual(instance["samplesPerRecoveryAttempt"], 7)

    def test_completion_trace_is_the_frozen_successful_replay(self) -> None:
        all_nodes = list(walk_json(self.data))
        all_strings = " ".join(node for node in all_nodes if isinstance(node, str))
        self.assertIn(2026091301, all_nodes)
        self.assertIn(EXPECTED_REPLAY_SAMPLES, all_nodes)
        self.assertIn([3, -1], all_nodes)
        self.assertRegex(all_strings.lower(), r"uniform[- ]hard[- ]box|model a")
        self.assertEqual(self.data["successfulReplay"]["preset"], "omit1")
        self.assertTrue(
            semantically_named_value(
                self.data, re.compile(r"beta|storedroot(?:product|value)"), 21
            ),
            "the completion replay must name the stored-root product beta=21",
        )

    def test_qft_resource_counts_and_scoped_claims(self) -> None:
        presets = self.data["qftPresets"]
        expected = {
            "exact": (0, 0, 0),
            "omit1": (2, 4, 0),
            "omit2": (6, 12, 0),
        }
        for name, (phases, cx, depth) in expected.items():
            with self.subTest(preset=name):
                preset = presets[name]
                self.assertEqual(preset["controlledPhasesRemoved"], phases)
                self.assertEqual(preset["qftOnlyCxRemoved"], cx)
                self.assertEqual(preset["qftOnlyDepthRemoved"], depth)

        omit1_claim = " ".join(
            str(presets["omit1"].get(field, ""))
            for field in ("observed", "scope")
        ).lower()
        self.assertIn("models a and b", omit1_claim)
        self.assertIn("eight held-out", omit1_claim)
        self.assertRegex(omit1_claim, r"does not prove|not (a )?universal")
        omit2_scope = " ".join(
            str(presets["omit2"].get(field, ""))
            for field in ("observed", "scope")
        ).lower()
        self.assertRegex(omit2_scope, r"gaussian|model b")
        self.assertIn("model a", omit2_scope)
        self.assertIn("fail", omit2_scope)
        self.assertRegex(omit2_scope, r"not (a )?universal")
        self.assertNotIn("safe for all", omit2_scope)

    def test_every_component_code_link_resolves(self) -> None:
        for component in self.data["components"]:
            with self.subTest(component=component["id"]):
                self.assertTrue(component["what"].strip())
                self.assertTrue(component["role"].strip())
                self.assertTrue(component["built"].strip())
                target = (DEMO_DIR / component["codeFile"]).resolve()
                self.assertTrue(target.is_file(), f"missing code target: {target}")


class DemoHTMLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.parser = DemoHTMLParser()
        cls.parser.feed(cls.html)

    def test_required_interface_regions_exist(self) -> None:
        required = {
            "guidedMode",
            "challengeMode",
            "cameraButton",
            "autoplayButton",
            "fullscreenButton",
            "resetButton",
            "componentPalette",
            "webcam",
            "handCanvas",
            "circuitWorkspace",
            "qftLab",
            "sampleStream",
            "handCursor",
            "researchReadout",
            "latticePipeline",
            "factorReveal",
            "completionDialog",
            "runLatticeButton",
        }
        self.assertEqual(required - self.parser.ids, set())

    def test_slot_targets_match_data_build_order(self) -> None:
        self.assertEqual(len(self.parser.slot_targets), 12)
        self.assertEqual(set(self.parser.slot_targets), set(EXPECTED_BUILD_ORDER))

    def test_all_local_html_references_resolve(self) -> None:
        for reference in self.parser.local_refs:
            path_only = reference.split("?", 1)[0].split("#", 1)[0]
            if not path_only:
                continue
            with self.subTest(reference=reference):
                target = (DEMO_DIR / path_only).resolve()
                self.assertTrue(target.exists(), f"broken local reference: {reference}")


class DemoInteractionTests(unittest.TestCase):
    def test_app_has_pointer_fallback_and_presentation_flow(self) -> None:
        app = (DEMO_DIR / "app.js").read_text(encoding="utf-8")
        for marker in (
            "pointerdown",
            "pointermove",
            "pointerup",
            "autoplayButton",
            "guidedMode",
            "challengeMode",
            "completionDialog",
            "latticePipeline",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, app)

    def test_hand_tracking_uses_pinned_official_api_and_pinches(self) -> None:
        tracking = (DEMO_DIR / "hand-tracking.js").read_text(encoding="utf-8")
        self.assertRegex(
            tracking,
            r'(?:@mediapipe/tasks-vision@0\.10\.35|MEDIAPIPE_VERSION\s*=\s*["\']0\.10\.35["\'])',
        )
        self.assertIn("HandLandmarker", tracking)
        self.assertIn("detectForVideo", tracking)
        self.assertIn("hand_landmarker.task", tracking)
        self.assertIn("getUserMedia", tracking)
        thumb_tip = re.search(r"(?:THUMB_TIP\s*=\s*4|landmarks\s*\[\s*4\s*\])", tracking)
        index_tip = re.search(r"(?:INDEX_TIP\s*=\s*8|landmarks\s*\[\s*8\s*\])", tracking)
        self.assertIsNotNone(thumb_tip, "pinch logic must use thumb-tip landmark 4")
        self.assertIsNotNone(index_tip, "pinch logic must use index-tip landmark 8")

    def test_camera_is_mirrored_and_reduced_motion_is_supported(self) -> None:
        css = (DEMO_DIR / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"(?:scaleX\s*\(\s*-1\s*\)|rotateY\s*\(\s*180deg\s*\))")
        self.assertIn("prefers-reduced-motion", css)


class DocumentationScopeTests(unittest.TestCase):
    def test_readme_keeps_replay_and_research_claims_separate(self) -> None:
        readme = (DEMO_DIR / "README.md").read_text(encoding="utf-8").lower()
        normalized = " ".join(readme.split())
        self.assertIn("fixed successful replay", readme)
        self.assertIn("not a new experimental endpoint", readme)
        self.assertIn("not a universal", readme)
        self.assertIn("not a demonstrated end-to-end hardware speedup", normalized)
        self.assertIn("2026091301", readme)
        self.assertIn("z=(3,-1)", readme.replace(" ", ""))
        compact_math = readme.replace("\\beta", "beta").replace(" ", "")
        self.assertIn("beta=2^33^{-1}\\equiv21", compact_math)

    def test_server_is_repository_rooted_for_source_links(self) -> None:
        server = (DEMO_DIR / "serve_demo.py").read_text(encoding="utf-8")
        self.assertIn("REPOSITORY_ROOT = DEMO_DIRECTORY.parent", server)
        self.assertIn("ThreadingHTTPServer", server)
        self.assertIn('DEFAULT_HOST = "127.0.0.1"', server)


if __name__ == "__main__":
    unittest.main()
