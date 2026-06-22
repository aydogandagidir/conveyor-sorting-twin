"""Structural guard for the GitHub Pages landing page (web/index.html).

The Pages site is a project landing page that links to the auto-generated demo
report. This test keeps the two in sync: the landing must exist, point at
`demo_report.html`, and the Pages workflow must actually publish it as index.html.
(The report itself is covered by tests/test_demo_report.py.)

Dual-mode: runnable directly and collectable by pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANDING = os.path.join(_ROOT, "web", "index.html")
PAGES_WF = os.path.join(_ROOT, ".github", "workflows", "pages.yml")
README = os.path.join(_ROOT, "README.md")
HERO = os.path.join(_ROOT, "web", "hero.svg")
GETTING_STARTED = os.path.join(_ROOT, "GETTING_STARTED.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_landing_exists_and_is_html():
    assert os.path.exists(LANDING), "web/index.html is missing"
    html = _read(LANDING)
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "OpenLogiTwin" in html
    assert len(html) > 1500  # not a stub


def test_landing_links_to_demo_report():
    html = _read(LANDING)
    assert 'href="demo_report.html"' in html, "landing must link to the demo report"


def test_landing_links_to_repo():
    html = _read(LANDING)
    assert "github.com/aydogandagidir/conveyor-sorting-twin" in html


def test_pages_workflow_publishes_the_landing():
    wf = _read(PAGES_WF)
    # the workflow must copy the landing to the site root as index.html
    assert "web/index.html" in wf and "_site/index.html" in wf
    # and it must still build the report the landing points at
    assert "run_full_demo.py" in wf


def test_hero_image_present_and_published():
    assert os.path.exists(HERO), "web/hero.svg (the HMI hero image) is missing"
    svg = _read(HERO)
    assert svg.lstrip().startswith("<svg") and "</svg>" in svg, "hero.svg is not a valid SVG"
    assert "hero.svg" in _read(LANDING), "the landing must embed the hero image"
    assert "web/hero.svg" in _read(README), "the README must show the hero image"
    wf = _read(PAGES_WF)
    assert "web/hero.svg" in wf and "_site/hero.svg" in wf, "pages.yml must publish hero.svg"


def test_getting_started_present_and_linked():
    assert os.path.exists(GETTING_STARTED), "GETTING_STARTED.md is missing"
    assert "GETTING_STARTED.md" in _read(README), "the README must link the getting-started tour"


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]


def main():
    passed = 0
    for t in _all_tests():
        t()
        print(f"  [PASS] {t.__name__}")
        passed += 1
    print(f"pages landing tests: {passed} passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
