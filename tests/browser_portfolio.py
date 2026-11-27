"""Real Chromium smoke/regression tests for the public portfolio and local preview.

Run after: pip install playwright && python -m playwright install chromium
Then: python tests/browser_portfolio.py
Does not write public project data, change a deployed page, or publish a build.
Screenshots/reports are written only beneath tests/_artifacts/.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Thread
import unicodedata
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "tests" / "_artifacts" / "browser-qa"
PUBLIC = "https://leechung0214-afk.github.io/fineinc-website/"
WIDTHS = (360, 390, 430, 1440)
SOURCE = json.loads((ROOT / "assets" / "projects.json").read_text(encoding="utf-8"))
PROJECTS = SOURCE["projects"]
EQUIPMENT = json.loads((ROOT / "assets" / "equipment.json").read_text(encoding="utf-8"))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def must(condition, reason):
    if not condition:
        raise AssertionError(reason)


def normalize(value):
    return unicodedata.normalize("NFKC", str(value or "")).lower()


def year_of(project):
    return project["startDate"][:4] if "startDate" in project else str(project["year"])


def photo_count(project):
    return len({p["src"] for p in [project["cover"], *project.get("gallery", [])]})


def matches(project, words="", year="all", category="all"):
    haystack = normalize(" ".join([project["title"], project.get("location", ""), project.get("role", "")]))
    return ((year == "all" or year_of(project) == year)
            and (category == "all" or project["category"] == category)
            and all(word in haystack for word in normalize(words).split()))


def visible_cards(page):
    return page.locator("#projectGrid .project-photo-card:visible").count()


def assert_results(page, query="", year="all", category="all"):
    selected = [p for p in PROJECTS if matches(p, query, year, category)]
    count = len(selected)
    photos = sum(photo_count(p) for p in selected)
    must(visible_cards(page) == count, f"expected {count} visible cards, got {visible_cards(page)}")
    must(page.locator("#projectCount").inner_text().strip() == f"수행 프로젝트 {count}건 · 현장 사진 {photos}장",
         f"incorrect counter: {page.locator('#projectCount').inner_text()!r}")
    must(page.locator("#projectEmpty").is_visible() == (count == 0), "zero-results state differs from count")


def ready(page, base):
    page.goto(base, wait_until="domcontentloaded", timeout=40000)
    page.locator("#projectLoadState[data-state='ready']").wait_for(timeout=40000)
    must(page.locator("#projectTools").is_visible(), "filters should be visible after load")
    must(page.locator("#projectGrid").get_attribute("aria-busy") == "false", "aria-busy not cleared")


def assert_no_horizontal_overflow(page, label):
    info = page.evaluate("""() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      offenders: [...document.querySelectorAll('#projects, #projects *')]
       .filter(el => {const r = el.getBoundingClientRect(); return r.width && (r.right > innerWidth + 2 || r.left < -2)})
       .slice(0, 8).map(el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '.' + el.className))
    })""")
    must(info["scroll"] <= info["viewport"] + 2,
         f"{label}: horizontal overflow {info['scroll']} vs {info['viewport']}; project offenders={info['offenders']}")


def button_size(page, selector, label):
    rect = page.locator(selector).bounding_box()
    must(rect is not None and rect["width"] >= 44 and rect["height"] >= 44,
         f"{label} touch target smaller than 44px: {rect}")


def test_viewports(page, scope):
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 900})
        first_cover = page.locator("#projectGrid .project-photo-card:visible .project-photo-open img").first
        first_cover.scroll_into_view_if_needed()
        page.wait_for_function("() => { const img = document.querySelector('#projectGrid .project-photo-card:not([hidden]) .project-photo-open img'); return img && img.complete && img.naturalWidth > 0; }", timeout=20000)
        page.locator("#projectTools").scroll_into_view_if_needed()
        assert_no_horizontal_overflow(page, f"{scope} {width}px")
        for selector in ("#projectSearch", "#projectYear", "#projectCategory", "#projectFilterReset", "#projectFilterShare"):
            button_size(page, selector, f"{scope} {width}px {selector}")
        page.screenshot(path=str(ARTIFACTS / f"{scope}-{width}.png"), animations="disabled")
        must(page.locator("#projectTools").is_visible(), f"{scope} {width}: controls hidden")


def test_search_and_history(page, context, base):
    first = PROJECTS[0]
    sample_year, sample_category = year_of(first), first["category"]
    word_match = re.search(r"[가-힣]{2,}", first["title"])
    must(word_match is not None, "no Korean fixture token in first published event")
    korean = word_match.group()
    page.locator("#projectSearch").fill(korean)
    must(parse_qs(urlparse(page.url).query).get("p_q") == [korean], "Korean query not encoded in URL")
    assert_results(page, korean)
    page.locator("#projectYear").select_option(sample_year)
    page.locator("#projectCategory").select_option(sample_category)
    assert_results(page, korean, sample_year, sample_category)

    page.goto(base.split("#")[0] + "?v=qa-browser&private_token=should-not-share#projects", wait_until="domcontentloaded")
    page.locator("#projectLoadState[data-state='ready']").wait_for(timeout=30000)
    page.locator("#projectSearch").fill(korean)
    page.locator("#projectYear").select_option(sample_year)
    page.locator("#projectCategory").select_option(sample_category)
    page.locator("#projectFilterShare").click()
    page.wait_for_function("""() => document.querySelector('#projectShareStatus').textContent.trim().length > 0""")
    status = page.locator("#projectShareStatus").inner_text()
    if page.locator("#projectShareUrl").is_visible():
        shared = page.locator("#projectShareUrl").input_value()
        must("복사" in status, "clipboard fallback has no explanation")
    else:
        shared = page.evaluate("navigator.clipboard.readText()")
        must("복사" in status, "native clipboard not reported successful")
    parsed = urlparse(shared)
    params = parse_qs(parsed.query)
    must("private_token" not in params, "private query accidentally included in share URL")
    must(params.get("v") == ["qa-browser"], "version query lost when sharing")
    must(params.get("p_q") == [korean] and params.get("p_year") == [sample_year]
         and params.get("p_category") == [sample_category] and parsed.fragment == "projects",
         f"incorrect shared query {shared}")

    new_tab = context.new_page()
    try:
        ready(new_tab, shared)
        must(new_tab.locator("#projectSearch").input_value() == korean, "new tab lost Korean query")
        must(new_tab.locator("#projectYear").input_value() == sample_year, "new tab lost year")
        must(new_tab.locator("#projectCategory").input_value() == sample_category, "new tab lost category")
        assert_results(new_tab, korean, sample_year, sample_category)
    finally:
        new_tab.close()

    page.locator("#projectFilterReset").click()
    must(page.locator("#projectSearch").input_value() == "", "reset did not clear keyword")
    must(page.locator("#projectYear").input_value() == "all", "reset did not clear year")
    must(page.locator("#projectCategory").input_value() == "all", "reset did not clear category")
    assert_results(page)
    page.locator("#projectYear").select_option(sample_year)
    page.locator("#projectCategory").select_option(sample_category)
    assert_results(page, year=sample_year, category=sample_category)
    page.evaluate("history.back()")
    page.wait_for_function("() => document.querySelector('#projectCategory').value === 'all'")
    assert_results(page, year=sample_year)
    page.evaluate("history.back()")
    page.wait_for_function("() => document.querySelector('#projectYear').value === 'all'")
    assert_results(page)
    page.evaluate("history.forward()")
    page.wait_for_function(f"() => document.querySelector('#projectYear').value === '{sample_year}'")
    assert_results(page, year=sample_year)
    page.evaluate("history.forward()")
    page.wait_for_function(f"() => document.querySelector('#projectCategory').value !== 'all'")
    assert_results(page, year=sample_year, category=sample_category)

    page.locator("#projectSearch").fill("존재하지않는행사명_qa_47821")
    assert_results(page, "존재하지않는행사명_qa_47821", sample_year, sample_category)
    page.locator("#projectFilterReset").click()
    assert_results(page)


def test_gallery(page):
    chosen = next(p for p in PROJECTS if photo_count(p) > 1)
    opener = page.get_by_role("button", name=f"{chosen['title']} 현장 사진 보기")
    opener.click()
    dialog = page.locator("#projectDialog")
    must(dialog.is_visible(), "gallery did not open")
    must(page.locator("#projectDialogTitle").inner_text() == chosen["title"], "gallery shows wrong title")
    must(page.locator("#projectImageNumber").inner_text() == f"1 / {photo_count(chosen)}", "gallery counter wrong")
    page.wait_for_function("() => document.querySelector('#projectDialogImage').naturalWidth > 0", timeout=20000)
    button_size(page, "#projectDialogClose", "gallery close")
    button_size(page, "#projectImageNext", "gallery next")
    page.locator("#projectImageNext").click()
    must(page.locator("#projectImageNumber").inner_text().startswith("2 /"), "gallery next did not work")
    page.keyboard.press("ArrowLeft")
    must(page.locator("#projectImageNumber").inner_text().startswith("1 /"), "gallery arrow key did not work")
    page.locator("#projectThumbnails button").nth(1).click()
    must(page.locator("#projectImageNumber").inner_text().startswith("2 /"), "thumbnail did not work")
    assert_no_horizontal_overflow(page, "gallery")
    page.keyboard.press("Escape")
    must(not dialog.is_visible(), "Escape did not close native dialog")
    must(opener.evaluate("(el) => document.activeElement === el"), "focus did not return to opener")


def test_local_error_and_retry(context, base):
    page = context.new_page()
    attempts = [0]

    def intermittent(route):
        attempts[0] += 1
        if attempts[0] == 1:
            route.fulfill(status=503, content_type="text/plain", body="QA unavailable")
        else:
            route.continue_()

    page.route("**/assets/projects.json", intermittent)
    try:
        page.goto(base, wait_until="domcontentloaded")
        page.locator("#projectLoadState[data-state='error']").wait_for(timeout=20000)
        must(not page.locator("#projectTools").is_visible(), "failed load left filters visible")
        must(page.locator("#projectGrid .project-photo-card").count() == 0, "failed load exposed stale cards")
        page.locator("#projectRetry").click()
        page.locator("#projectLoadState[data-state='ready']").wait_for(timeout=20000)
        must(attempts[0] >= 2, "retry did not request JSON again")
        assert_results(page)
    finally:
        page.close()


def test_local_empty_and_long(context, base):
    empty_page = context.new_page()
    empty = {"schemaVersion": 1, "replaceExisting": True, "projects": []}
    empty_page.route("**/assets/projects.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(empty, ensure_ascii=False)))
    try:
        empty_page.goto(base, wait_until="domcontentloaded")
        empty_page.locator("#projectLoadState[data-state='empty']").wait_for(timeout=20000)
        must(not empty_page.locator("#projectTools").is_visible(), "empty dataset should hide filters")
        must(empty_page.locator("#projectGrid .project-photo-card").count() == 0, "empty dataset has cards")
    finally:
        empty_page.close()

    long_page = context.new_page()
    item = deepcopy(PROJECTS[0])
    item["id"] = "qa-long-title"
    item["title"] = ("매우 긴 행사명과 지역 행사 수행업무 확인 " * 7)[:280]
    item["role"] = ("음향 · 조명 · 영상 통합 기술운영 · " * 18)[:520]
    fixture = {"schemaVersion": 1, "replaceExisting": True, "projects": [item]}
    long_page.route("**/assets/projects.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(fixture, ensure_ascii=False)))
    try:
        long_page.goto(base, wait_until="domcontentloaded")
        long_page.locator("#projectLoadState[data-state='ready']").wait_for(timeout=20000)
        for width in WIDTHS:
            long_page.set_viewport_size({"width": width, "height": 900})
            long_page.locator(".project-photo-open img").first.scroll_into_view_if_needed()
            long_page.wait_for_function("() => {const img=document.querySelector('.project-photo-open img'); return img && img.complete && img.naturalWidth > 0;}", timeout=20000)
            assert_no_horizontal_overflow(long_page, f"long Korean title {width}")
            geometry = long_page.locator(".project-title-button").evaluate("""el => {
              const a=el.getBoundingClientRect(), b=el.closest('.project-card').getBoundingClientRect();
              return { left:a.left, right:a.right, max:b.right };
            }""")
            must(geometry["right"] <= geometry["max"] + 2, f"long title escaped card at {width}px")
            long_page.locator("#projectTools").scroll_into_view_if_needed()
            long_page.screenshot(path=str(ARTIFACTS / f"long-title-{width}.png"), animations="disabled")
    finally:
        long_page.close()


def run_case(label, fn, results):
    print(f"[RUN] {label}", flush=True)
    try:
        fn()
        results.append({"case": label, "status": "PASS"})
        print(f"[PASS] {label}", flush=True)
    except Exception as exc:
        results.append({"case": label, "status": "FAIL", "detail": str(exc)})
        print(f"[FAIL] {label}: {exc}", flush=True)


def run_scope(browser, scope, base, results):
    context = browser.new_context(viewport={"width": 1440, "height": 900},
                                  permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    try:
        try:
            ready(page, base)
        except Exception as exc:
            results.append({"case": scope + ": open/ready", "status": "FAIL", "detail": str(exc)})
            print(f"[FAIL] {scope}: open/ready: {exc}", flush=True)
            return
        run_case(f"{scope}: published counts", lambda: (
            must(len(PROJECTS) == 47, "source event count changed"),
            must(sum(photo_count(p) for p in PROJECTS) == 122, "source photo count changed"),
            must(len(EQUIPMENT["items"]) == 39, "source equipment count changed"),
            assert_results(page)), results)
        run_case(f"{scope}: desktop/mobile viewport and targets",
                 lambda: test_viewports(page, scope), results)
        run_case(f"{scope}: Korean query, combined filters, share, new tab, history, zero, reset",
                 lambda: test_search_and_history(page, context, base), results)
        run_case(f"{scope}: gallery image, next, thumbnails, keyboard and focus",
                 lambda: test_gallery(page), results)
        if scope == "local":
            run_case("local: fetch failure and retry", lambda: test_local_error_and_retry(context, base), results)
            run_case("local: empty data and long Korean title",
                     lambda: test_local_empty_and_long(context, base), results)
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-url", default=PUBLIC)
    parser.add_argument("--skip-public", action="store_true")
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    results = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    local = f"http://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                run_scope(browser, "local", local, results)
                if not args.skip_public:
                    run_scope(browser, "public", args.public_url, results)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {"base_sha": "e184d107bc8d982767db1bf9465d7ca9f99a3e68",
              "local": local, "public": None if args.skip_public else args.public_url,
              "results": results}
    (ARTIFACTS / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [row for row in results if row["status"] != "PASS"]
    print(f"QA SUMMARY: {len(results) - len(failures)} passed, {len(failures)} failed", flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
