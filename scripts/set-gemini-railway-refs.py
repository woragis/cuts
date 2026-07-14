#!/usr/bin/env python3
"""Set GEMINI_API_KEY=${{api.GEMINI_API_KEY}} on workers that call Gemini.

Uses Railway GraphQL over IPv4 (avoids flaky IPv6). Requires a fresh
`railway login` so ~/.railway/config.json accessToken is valid.

Usage:
  python3 scripts/set-gemini-railway-refs.py
"""

from __future__ import annotations

import json
import ssl
import socket
import http.client
import time
from pathlib import Path

CONFIG = Path.home() / ".railway" / "config.json"
IP = "104.18.25.53"  # Cloudflare for backboard.railway.com (IPv4)

SERVICES = (
    "worker-plan",
    "worker-analyze",
    "worker-control",
    "worker-ffmpeg",
    "worker-transcribe",
    "worker-factory",
    "worker-media",
)

REF = "${{api.GEMINI_API_KEY}}"


class HTTPSConnectionIPv4(http.client.HTTPSConnection):
    def connect(self) -> None:
        sock = socket.create_connection((IP, self.port), timeout=self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def gql(token: str, query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    conn = HTTPSConnectionIPv4(
        "backboard.railway.com",
        443,
        timeout=60,
        context=ssl.create_default_context(),
    )
    conn.request(
        "POST",
        "/graphql/v2",
        body,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Host": "backboard.railway.com",
        },
    )
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2)[:2000])
    return data["data"]


def main() -> None:
    cfg = json.loads(CONFIG.read_text())
    token = cfg["user"]["accessToken"]
    exp = cfg["user"].get("tokenExpiresAt") or 0
    if time.time() > exp:
        raise SystemExit(
            f"Railway token expired (exp={exp}). Run: railway login\n"
            f"Then re-run this script."
        )
    project = cfg["projects"]["/home/woragis/dev/cuts"]["project"]
    environment = cfg["projects"]["/home/woragis/dev/cuts"]["environment"]

    me = gql(token, "{ me { email } }")
    print("logged in as", me["me"]["email"])

    services = gql(
        token,
        """
        query($id: String!) {
          project(id: $id) {
            services { edges { node { id name } } }
          }
        }
        """,
        {"id": project},
    )["project"]["services"]["edges"]
    by_name = {e["node"]["name"]: e["node"]["id"] for e in services}

    missing = [n for n in SERVICES if n not in by_name]
    if missing:
        print("WARN missing services:", missing)

    for name in SERVICES:
        sid = by_name.get(name)
        if not sid:
            continue
        gql(
            token,
            """
            mutation($input: VariableUpsertInput!) {
              variableUpsert(input: $input)
            }
            """,
            {
                "input": {
                    "projectId": project,
                    "environmentId": environment,
                    "serviceId": sid,
                    "name": "GEMINI_API_KEY",
                    "value": REF,
                }
            },
        )
        print("set", name, "GEMINI_API_KEY=", REF)

    print("done — redeploy worker-plan (and others) if they do not auto-reload env")


if __name__ == "__main__":
    main()
