"""Capture the outputs of the dashboard so a refactor can be checked for identical behaviour.

Usage (from the project root, with the venv):
    .venv/bin/python scripts/golden/capture.py --label p0 --snapshot ~/stock-benchmark-golden/fixtures/snapshot.json

Writes to ~/stock-benchmark-golden/<label>/ (outside the repository):
    pages/<name>        the body of every page and static asset
    pages/index.tsv     status, content type, cache header and body sha256 for each URL
    api/<name>.json     the body of every /api/v1 response
    api/index.tsv       status and body sha256 for each API URL

The snapshot file is copied into place before any request, and the network is disabled, so the
output depends only on the snapshot and the code. Pages that fetch live data (the terminal) store
the status and the error body hash, which is the same every run while the network is off.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def block_network() -> None:
    def refuse(*args, **kwargs):
        raise OSError("network is disabled for golden capture")
    socket.socket.connect = refuse
    socket.create_connection = refuse


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def static_name_list() -> list:
    folder = "frontend" if os.path.isdir("frontend") else "static"  # the folder moved in phase 2
    return sorted(name for name in os.listdir(folder) if os.path.isfile(os.path.join(folder, name)))


def page_url_list() -> list:
    return ["/", "/rules", "/indicators", "/strategies", "/strategies/fundamentals", "/terminal/AAPL"]


def api_url_list(symbol: str) -> list:
    return [
        "/api/v1/version", "/api/v1/rules", "/api/v1/strategies", "/api/v1/indicators",
        "/api/v1/snapshot", "/api/v1/snapshot?strategy_id=fundamentals",
        "/api/v1/fundamentals/" + symbol, "/api/v1/evaluations/fundamentals/" + symbol,
        "/api/v1/terminal/" + symbol,
    ]


def stable_body(url: str, response) -> bytes:
    """The part of a response that a refactor must not change.

    The terminal bars come from live prices, so only its status is kept. The server clock in the
    status block changes on every request, so it is removed from the other JSON bodies.
    """
    if "/terminal/" in url:
        return ("status {}\n".format(response.status_code)).encode("ascii")
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.content
    data = response.json()
    if isinstance(data, dict) and isinstance(data.get("status"), dict):
        data["status"].pop("server_time", None)
    return (json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n").encode("utf8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--snapshot", required=True, help="a frozen copy of data/latest_snapshot.json")
    parser.add_argument("--out", default=os.path.expanduser("~/stock-benchmark-golden"))
    args = parser.parse_args()

    block_network()
    from fastapi.testclient import TestClient
    from stock_benchmark_backend import refresh_scheduler, web_server

    # The server reads the snapshot path at request time, so pointing it at the frozen copy is enough.
    refresh_scheduler.SNAPSHOT_FILE_PATH = os.path.abspath(os.path.expanduser(args.snapshot))
    output = os.path.join(os.path.expanduser(args.out), args.label)
    shutil.rmtree(output, ignore_errors=True)
    os.makedirs(os.path.join(output, "pages"))
    os.makedirs(os.path.join(output, "api"))

    # No "with": entering the client would start the lifespan and the background refresh thread.
    client = TestClient(web_server.app)
    symbol = web_server.application_settings.watchlist_symbol_list[0]

    page_rows = []
    for url in page_url_list() + ["/" + name for name in static_name_list()]:
        response = client.get(url)
        name = re.sub(r"[^A-Za-z0-9._-]", "_", url.strip("/") or "index") + ".body"
        with open(os.path.join(output, "pages", name), "wb") as body_file:
            body_file.write(response.content)
        page_rows.append("\t".join([url, str(response.status_code), response.headers.get("content-type", ""),
                                    response.headers.get("cache-control", ""), sha256_of(response.content)]))
    with open(os.path.join(output, "pages", "index.tsv"), "w", encoding="utf8") as index_file:
        index_file.write("\n".join(page_rows) + "\n")

    api_rows = []
    for url in api_url_list(symbol):
        response = client.get(url)
        name = re.sub(r"[^A-Za-z0-9._-]", "_", url.replace("/api/v1/", "")) + ".json"
        body = stable_body(url, response)
        with open(os.path.join(output, "api", name), "wb") as body_file:
            body_file.write(body)
        api_rows.append("\t".join([url, str(response.status_code), sha256_of(body)]))
    with open(os.path.join(output, "api", "index.tsv"), "w", encoding="utf8") as index_file:
        index_file.write("\n".join(api_rows) + "\n")
    print("captured", label_summary(output))


def label_summary(output: str) -> str:
    pages = sum(1 for _ in open(os.path.join(output, "pages", "index.tsv"), encoding="utf8"))
    apis = sum(1 for _ in open(os.path.join(output, "api", "index.tsv"), encoding="utf8"))
    return "{} page rows, {} api rows in {}".format(pages, apis, output)


if __name__ == "__main__":
    main()
