"""End-to-end and unit tests for github-to-cv.

Run:  python -m unittest discover -s tests -v
PDF tests are skipped automatically when no PDF engine (Chrome/Playwright/WeasyPrint) is available.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "github-to-cv"
sys.path.insert(0, str(SKILL / "scripts"))

import _common  # noqa: E402
import analyze_profile  # noqa: E402
import ats_check  # noqa: E402
import fetch_github  # noqa: E402
import render  # noqa: E402
import validate_cv  # noqa: E402

EX = ROOT / "examples"
TEMPLATES = sorted(p.name for p in (SKILL / "templates").iterdir() if (p / "manifest.json").exists())
EXAMPLES = ["senior-backend", "new-grad", "researcher"]


def has_module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def pdf_engine_available():
    return bool(render.find_chrome()) or has_module("playwright") or has_module("weasyprint")


class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        self.t = _common.taxonomy()

    def test_tricky_matches(self):
        f = self.t.find("We use Go and Rust. Go to the docs. R&D team. Node.js, scikit learn, CI/CD on AWS.")
        self.assertIn("Go", f)
        self.assertEqual(f["Go"], 1, "'Go to the docs' must not count as Go")
        self.assertNotIn("R", f, "'R&D' must not count as R")
        for s in ("Rust", "Node.js", "scikit-learn", "CI/CD", "AWS"):
            self.assertIn(s, f)

    def test_case_sensitive_words(self):
        f = self.t.find("Teams react to incidents; express yourself; the rest of the team")
        for s in ("React", "Express.js", "REST APIs"):
            self.assertNotIn(s, f)

    def test_longest_match_wins(self):
        f = self.t.find("Deployed with GitHub Actions and Docker Compose")
        self.assertIn("GitHub Actions", f)
        self.assertNotIn("GitHub", f)
        self.assertIn("Docker Compose", f)
        self.assertNotIn("Docker", f)

    def test_substrings_not_matched(self):
        f = self.t.find("HTML and YAML, MySQL, JavaScript")
        self.assertNotIn("Machine Learning", f)
        self.assertNotIn("Java", f)
        self.assertNotIn("SQL", f)


class TestDatesAndJD(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(_common.fmt_date("2023-05"), "May 2023")
        self.assertEqual(_common.fmt_date("Sept 2021"), "Sep 2021")
        self.assertEqual(_common.fmt_date("05/2020", "mm/yyyy"), "05/2020")
        self.assertEqual(_common.fmt_range("2022-05", None), "May 2022 – Present")
        self.assertEqual(_common.fmt_range("2023", "2023"), "2023")
        self.assertTrue(_common.fmt_range("2024-08", "2099-05", expected_label="Expected").endswith("Expected May 2099"))
        self.assertIsNone(_common.parse_date("2023-13"))

    def test_jd_split(self):
        jd = (EX / "sample-jd.txt").read_text(encoding="utf-8")
        p = _common.parse_jd(jd)
        pri = {s["name"]: s["priority"] for s in p["skills"]}
        self.assertEqual(pri["PostgreSQL"], "required")
        self.assertEqual(pri["Snowflake"], "preferred")
        self.assertIn(5, p["years_mentioned"])
        self.assertTrue(p["title_guess"].startswith("Senior Backend Engineer"))


class TestFetch(unittest.TestCase):
    def test_parse_login(self):
        self.assertEqual(fetch_github.parse_login("https://github.com/octocat/"), "octocat")
        self.assertEqual(fetch_github.parse_login("github.com/some-user/repo"), "some-user")
        self.assertEqual(fetch_github.parse_login("@octocat"), "octocat")
        with self.assertRaises(SystemExit):
            fetch_github.parse_login("not a user!")

    def test_fetch_with_mocked_api(self):
        user = {"login": "demo", "name": "Demo User", "public_repos": 2, "followers": 1,
                "created_at": "2020-01-01T00:00:00Z", "html_url": "https://github.com/demo"}
        repos = [
            {"name": "alpha", "full_name": "demo/alpha", "html_url": "https://github.com/demo/alpha", "description": "Fast thing in Go",
             "language": "Go", "topics": ["go"], "stargazers_count": 50, "forks_count": 3, "size": 900, "fork": False,
             "pushed_at": "2026-10-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z", "license": {"spdx_id": "MIT"}},
            {"name": "beta", "full_name": "demo/beta", "html_url": "https://github.com/demo/beta", "description": None,
             "language": "Python", "topics": [], "stargazers_count": 0, "forks_count": 0, "size": 10, "fork": True,
             "pushed_at": "2021-01-01T00:00:00Z", "created_at": "2021-01-01T00:00:00Z", "license": None},
        ]
        search = {"total_count": 1, "items": [{"repository_url": "https://api.github.com/repos/big/proj", "title": "Fix bug",
                                               "html_url": "https://github.com/big/proj/pull/1",
                                               "pull_request": {"merged_at": "2025-05-05T00:00:00Z"}}]}

        def fake(self, url, accept="application/vnd.github+json", payload=None):
            path = url.split("api.github.com", 1)[1]
            if path.startswith("/users/demo/repos"):
                return 200, json.dumps(repos).encode()
            if path == "/users/demo":
                return 200, json.dumps(user).encode()
            if path.startswith("/users/demo/"):
                return 200, b"[]"
            if path == "/repos/demo/alpha/languages":
                return 200, json.dumps({"Go": 12000, "Makefile": 100}).encode()
            if path == "/repos/demo/alpha/readme":
                return 200, b"# alpha\nHandles 10k req/s with p99 under 5 ms."
            if path.startswith("/search/issues"):
                return 200, json.dumps(search).encode()
            if path == "/repos/big/proj":
                return 200, json.dumps({"stargazers_count": 5000, "description": "Big", "language": "Go"}).encode()
            return 404, b"{}"

        with mock.patch.object(fetch_github.GitHub, "_request", fake):
            data = fetch_github.fetch("demo", token=None, verbose=False)
        self.assertEqual(data["profile"]["name"], "Demo User")
        alpha = next(r for r in data["repos"] if r["name"] == "alpha")
        self.assertTrue(alpha["deep"])
        self.assertIn("10k req/s", alpha["readme"])
        self.assertEqual(data["external_contributions"][0]["stars"], 5000)
        self.assertNotIn("token", json.dumps(data).lower().replace("tokens", ""))


class TestAnalyze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gh = _common.load_json(EX / "sample-github.json")
        cls.a = analyze_profile.analyze(gh, jd_text=(EX / "sample-jd.txt").read_text(encoding="utf-8"), target="Senior Backend Engineer")

    def test_featured_excludes_noise(self):
        feat = self.a["featured"]
        self.assertEqual(feat[:3], ["ledgerline", "fastapi-ratelimit", "k8s-preview-envs"])
        for bad in ("react-todo-app", "ml-course-notebooks", "dotfiles", "leetcode-solutions", "cpython", "jordanlee-example"):
            self.assertNotIn(bad, feat)

    def test_evidence_levels(self):
        lv = {s["name"]: s["level"] for s in self.a["skills"]}
        self.assertEqual(lv["Go"], "strong")
        self.assertEqual(lv["Kafka"], "weak")             # only in a README
        self.assertEqual(lv["Infrastructure as Code"], "medium")  # implied by Terraform, capped
        self.assertEqual(lv["React"], "weak")             # only from a starter project
        self.assertEqual(lv["Open Source"], "strong")     # merged PRs to other projects

    def test_jd_coverage_and_questions(self):
        c = self.a["jd_coverage"]
        self.assertGreaterEqual(c["required_pct"], 70)
        self.assertIn("Kafka", c["required_missing"])
        self.assertTrue(any("Kafka" in q for q in self.a["questions"]))

    def test_readme_facts_and_packages(self):
        ledger = next(p for p in self.a["projects"] if p["name"] == "ledgerline")
        self.assertTrue(any("4,800 transfers/sec" in f for f in ledger["readme_facts"]))
        rl = next(p for p in self.a["projects"] if p["name"] == "fastapi-ratelimit")
        self.assertIn({"registry": "PyPI", "name": "fastapi-ratelimit-kit",
                       "stats_url": "https://pypistats.org/packages/fastapi-ratelimit-kit"}, rl["packages"])

    def test_draft_is_facts_only(self):
        d = analyze_profile.draft_cv(self.a, "Senior Backend Engineer")
        self.assertEqual(d["basics"]["name"], "Jordan Lee")
        self.assertEqual(d["work"], [])
        self.assertTrue(all(p["highlights"] == [] for p in d["projects"]))
        self.assertTrue(any(p["network"] == "LinkedIn" for p in d["basics"]["profiles"]))
        md = analyze_profile.to_markdown(self.a)
        self.assertIn("## Questions to ask the user", md)

    def test_pretty_names(self):
        self.assertEqual(analyze_profile.pretty_name("fastapi-ratelimit"), "FastAPI Ratelimit")
        self.assertEqual(analyze_profile.pretty_name("k8s-preview-envs"), "K8s Preview Envs")
        self.assertEqual(analyze_profile.pretty_name("pg-backup-s3"), "PG Backup S3")


class TestValidate(unittest.TestCase):
    def test_examples_have_no_errors(self):
        for ex in EXAMPLES:
            errors, _, _ = validate_cv.validate(_common.load_json(EX / f"{ex}.cv.json"))
            self.assertEqual(errors, [], ex)

    def test_catches_problems(self):
        cv = {"basics": {"name": "A B", "email": "bad"}, "work": [
            {"name": "X", "position": "Dev", "startDate": "2024-05", "endDate": "2023-01",
             "highlights": ["Responsible for TODO things", "I built stuff"]}]}
        errors, warnings, _ = validate_cv.validate(cv)
        joined = " ".join(errors + warnings)
        self.assertIn("email looks invalid", joined)
        self.assertIn("endDate is before startDate", joined)
        self.assertIn("placeholder", joined)
        self.assertIn("weak opener", joined)
        self.assertIn("pronoun", joined)


class TestTemplates(unittest.TestCase):
    def test_manifests(self):
        self.assertGreaterEqual(len(TEMPLATES), 6)
        for t in TEMPLATES:
            m = _common.load_json(SKILL / "templates" / t / "manifest.json")
            for k in ("name", "displayName", "description", "bestFor", "entryStyle", "accent", "defaultSectionOrder", "docx"):
                self.assertIn(k, m, f"{t}: {k}")
            self.assertEqual(m["name"], t)
            self.assertIn(m["entryStyle"], ("title-first", "org-first", "inline"))

    def test_css_ats_rules(self):
        for css in (SKILL / "templates").glob("*/*.css"):
            s = re.sub(r"/\*.*?\*/", "", css.read_text(encoding="utf-8"), flags=re.S)
            self.assertNotIn("small-caps", s, css)
            self.assertNotRegex(s, r"url\(", f"{css}: no images/remote fonts")
            self.assertNotRegex(s, r"column-count|columns:\s*\d|grid-template-columns", f"{css}: single column only")
            for m in re.finditer(r"letter-spacing:\s*(-?[\d.]+)em", s):
                self.assertLessEqual(float(m.group(1)), 0.08, f"{css}: {m.group(0)}")

    def test_text_formats_all_templates(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for t in TEMPLATES:
                for ex in EXAMPLES:
                    fmts = ["md", "txt", "html"] + (["docx"] if has_module("docx") else [])
                    res = render.render_all(EX / f"{ex}.cv.json", template=t, formats=fmts, out_dir=tmp / t / ex, quiet=True)
                    txt = Path(res["files"]["txt"]).read_text(encoding="utf-8")
                    name = _common.load_json(EX / f"{ex}.cv.json")["basics"]["name"]
                    self.assertTrue(txt.startswith(name.upper()), f"{t}/{ex}")
                    html = Path(res["files"]["html"]).read_text(encoding="utf-8")
                    self.assertIn('class="cv-name"', html)
                    self.assertNotIn("{{", html)
                    if "docx" in res["files"]:
                        dtext = _common.docx_to_text(res["files"]["docx"])
                        self.assertTrue(dtext.startswith(name), f"{t}/{ex} docx")
                        self.assertNotRegex(dtext, r"\n\t", "no stray leading tabs in DOCX text")
                        meta = _common.docx_to_text.last_meta
                        self.assertFalse(meta["has_tables"] or meta["has_textboxes"] or meta["has_images"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_promotions_grouped(self):
        cv = _common.load_json(EX / "senior-backend.cv.json")
        ctx = render.build_context(cv, render.load_manifest("modern"))
        work = next(s for s in ctx["sections"] if s["id"] == "work")
        self.assertEqual(len(work["entries"]), 2)
        self.assertEqual(len(work["entries"][0]["roles"]), 2)

    def test_missing_pdf_engine_degrades_gracefully(self):
        if not has_module("jinja2"):
            self.skipTest("jinja2 not installed")

        def broken(*a, **k):
            raise RuntimeError("engine unavailable")
        tmp = Path(tempfile.mkdtemp())
        try:
            with mock.patch.dict(render.ENGINES, {"playwright": broken, "chrome": broken, "weasyprint": broken}):
                res = render.render_all(EX / "new-grad.cv.json", formats=["pdf", "txt"], out_dir=tmp, quiet=True)
            self.assertIn("pdf", res["skipped"])
            self.assertTrue(Path(res["files"]["html"]).exists(), "HTML kept for Print → PDF")
            self.assertTrue(Path(res["files"]["txt"]).exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_contact_lines_split_when_long(self):
        cv = _common.load_json(EX / "senior-backend.cv.json")
        ctx = render.build_context(cv, render.load_manifest("modern"))
        self.assertEqual(len(ctx["contact_lines"]), 2)
        self.assertEqual([c["kind"] for c in ctx["contact_lines"][0]], ["location", "phone", "email"])


@unittest.skipUnless(pdf_engine_available() and has_module("jinja2"), "no PDF engine")
class TestPDF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pdf_parses_cleanly_and_scores_high(self):
        jd = (EX / "sample-jd.txt").read_text(encoding="utf-8")
        cv = _common.load_json(EX / "senior-backend.cv.json")
        for t in TEMPLATES:
            res = render.render_all(EX / "senior-backend.cv.json", template=t, formats=["pdf"], out_dir=self.tmp / t,
                                    max_pages=2, quiet=True)
            pdf = res["files"]["pdf"]
            text, info = _common.extract_text(pdf)
            self.assertIn("jordan lee", text[:200].lower(), t)  # classic uppercases the name; parsers normalise case
            self.assertRegex(text, r"•\s?Led the redesign", f"{t}: bullets must extract as '• text' in order")
            self.assertNotRegex(text, r"\b(?:[A-Z] ){4,}[A-Z]\b", f"{t}: letter-spaced headings")
            r = ats_check.check(pdf, jd_text=jd, cv=cv, level="senior")
            self.assertGreaterEqual(r["score"], 85, f"{t}: {r['score']} {r['top_fixes']}")
            for sec in ("experience", "education", "skills"):
                self.assertIn(sec, r["sections_found"], t)

    def test_max_pages_fits_one_page(self):
        res = render.render_all(EX / "new-grad.cv.json", formats=["pdf"], out_dir=self.tmp / "ng", max_pages=1, quiet=True)
        self.assertEqual(res["pages"], 1)


if __name__ == "__main__":
    unittest.main()
