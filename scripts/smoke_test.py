"""Read-only delivery smoke test for the public site and operations API.

Usage:
  $env:SMOKE_ADMIN_PASSWORD="..."
  python scripts/smoke_test.py --site-base http://localhost --expect-empty
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class HttpResponse:
    status_code: int
    body: bytes

    def json(self) -> dict:
        return json.loads(self.body.decode("utf-8"))


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


class SmokeTest:
    def __init__(self, site_base: str, username: str, password: str, expect_empty: bool):
        self.site_base = site_base.rstrip("/")
        self.username = username
        self.password = password
        self.expect_empty = expect_empty
        self.token = ""
        self.results: list[Result] = []
        self.opener = build_opener(NoRedirectHandler())

    def request(self, method: str, path: str, *, authenticated: bool = False, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if "data" in kwargs:
            body = urlencode(kwargs["data"]).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request = Request(f"{self.site_base}{path}", data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=12) as response:
                return HttpResponse(response.status, response.read())
        except HTTPError as exc:
            return HttpResponse(exc.code, exc.read())
        except (URLError, TimeoutError) as exc:
            self.results.append(Result(path, False, str(exc)))
            return None

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        self.results.append(Result(name, condition, detail))
        print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))

    def check_json_list(self, name: str, path: str, *, authenticated: bool = False) -> dict:
        response = self.request("GET", path, authenticated=authenticated)
        ok = response is not None and response.status_code == 200
        payload = response.json() if ok else {}
        self.check(name, ok and isinstance(payload.get("items"), list), f"status={getattr(response, 'status_code', 'N/A')}, total={payload.get('total', 'N/A')}")
        return payload

    def run(self) -> bool:
        print(f"Delivery smoke test: {self.site_base}\n")

        health = self.request("GET", "/health")
        self.check("health", health is not None and health.status_code == 200)

        home = self.request("GET", "/")
        self.check("homepage", home is not None and home.status_code == 200)

        missing_city = self.request("GET", "/definitely-not-a-city")
        self.check("unknown city is 404", missing_city is not None and missing_city.status_code == 404)

        missing_article = self.request("GET", "/articles/definitely-not-an-article")
        self.check("unknown article is 404", missing_article is not None and missing_article.status_code == 404)

        cities = self.check_json_list("public cities", "/api/v1/cities")
        stores = self.check_json_list("public stores", "/api/v1/cities/stores/all")
        articles = self.check_json_list("public articles", "/api/v1/articles")

        bad_geo = self.request("GET", "/api/geo/locate?lat=999&lng=999")
        self.check("invalid coordinates rejected", bad_geo is not None and bad_geo.status_code == 400)

        login = self.request(
            "POST",
            "/api/v1/auth/token",
            data={"username": self.username, "password": self.password},
        ) if self.password else None
        login_ok = login is not None and login.status_code == 200
        if login_ok:
            self.token = login.json().get("access_token", "")
        self.check("admin login", login_ok and bool(self.token), "set SMOKE_ADMIN_PASSWORD when omitted")

        if self.token:
            me = self.request("GET", "/api/v1/auth/me", authenticated=True)
            me_data = me.json() if me is not None and me.status_code == 200 else {}
            self.check("admin identity", me_data.get("role") == "admin", f"role={me_data.get('role')}")
            self.check_json_list("admin cities", "/api/v1/admin/cities", authenticated=True)
            self.check_json_list("admin users", "/api/v1/admin/users", authenticated=True)
            leads = self.check_json_list("admin leads", "/api/v1/leads", authenticated=True)
            posts = self.check_json_list("admin content posts", "/api/v1/content/posts", authenticated=True)
        else:
            leads = posts = {}

        if self.expect_empty:
            for name, payload in (
                ("public cities empty", cities),
                ("public stores empty", stores),
                ("public articles empty", articles),
                ("leads empty", leads),
                ("content posts empty", posts),
            ):
                self.check(name, payload.get("total") == 0, f"total={payload.get('total', 'N/A')}")

        failed = [result for result in self.results if not result.ok]
        print(f"\nResult: {len(self.results) - len(failed)}/{len(self.results)} passed")
        return not failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-base", default="http://localhost")
    parser.add_argument("--username", default=os.getenv("SMOKE_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("SMOKE_ADMIN_PASSWORD", ""))
    parser.add_argument("--expect-empty", action="store_true")
    args = parser.parse_args()
    return 0 if SmokeTest(args.site_base, args.username, args.password, args.expect_empty).run() else 1


if __name__ == "__main__":
    sys.exit(main())
