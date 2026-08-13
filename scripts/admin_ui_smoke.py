#!/usr/bin/env python3
"""Non-destructive Chromium smoke test for every admin console section."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ADMIN_SECTIONS = [
    "今日概览",
    "意图挖掘",
    "内容生成",
    "知识库",
    "内容审核",
    "发布分发",
    "线索管理",
    "人工客服",
    "运营指标",
    "城市站管理",
    "门店管理",
    "城市案例/FAQ",
    "城市 SEO",
    "域名/二级域名",
    "权限账号",
    "操作审计",
    "账号设置",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3100")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", "admin123"))
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def visible_errors(page: Page) -> list[str]:
    selectors = [
        ".form-message.error",
        ".admin-toast.is-error",
        "[role='alert']",
    ]
    errors: list[str] = []
    for selector in selectors:
        for node in page.locator(selector).all():
            if node.is_visible():
                text = node.inner_text().strip()
                if text:
                    errors.append(text)
    return sorted(set(errors))


def main() -> int:
    args = parse_args()
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    server_errors: list[str] = []
    checked: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.on(
            "response",
            lambda response: server_errors.append(
                f"{response.status} {response.request.method} {response.url}"
            )
            if response.status >= 500
            else None,
        )

        page.goto(f"{args.base_url.rstrip('/')}/admin", wait_until="networkidle")
        page.get_by_label("用户名").fill(args.username)
        page.get_by_label("密码").fill(args.password)
        page.get_by_role("button", name="登录", exact=True).click()
        page.locator(".admin-nav").wait_for(state="visible", timeout=10_000)

        actual_sections = [
            node.locator(".admin-nav-label").inner_text().strip()
            for node in page.locator(".admin-nav button").all()
        ]
        missing = [label for label in ADMIN_SECTIONS if label not in actual_sections]
        unexpected = [label for label in actual_sections if label not in ADMIN_SECTIONS]

        for label in ADMIN_SECTIONS:
            if label not in actual_sections:
                continue
            button = page.locator(".admin-nav button").filter(has_text=label).first
            button.click()
            page.locator(".admin-topbar h1").filter(has_text=label).wait_for(
                state="visible", timeout=5_000
            )
            page.wait_for_timeout(500)
            checked.append(
                {
                    "section": label,
                    "heading": page.locator(".admin-topbar h1").inner_text().strip(),
                    "visible_errors": visible_errors(page),
                }
            )

        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
        browser.close()

    result = {
        "url": f"{args.base_url.rstrip('/')}/admin",
        "expected_sections": len(ADMIN_SECTIONS),
        "checked_sections": len(checked),
        "missing_sections": missing,
        "unexpected_sections": unexpected,
        "sections": checked,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "failed_requests": failed_requests,
        "server_errors": server_errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    has_visible_errors = any(item["visible_errors"] for item in checked)
    failed = any(
        [
            missing,
            unexpected,
            console_errors,
            page_errors,
            failed_requests,
            server_errors,
            has_visible_errors,
            len(checked) != len(ADMIN_SECTIONS),
        ]
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
