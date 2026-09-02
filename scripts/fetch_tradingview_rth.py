#!/usr/bin/env python3
"""Fetch TradingView regular-session bars with the Python standard library.

The anonymous TradingView chart WebSocket is an aggregation source, not an
exchange-certified feed. Output is restricted to 09:30-16:00 America/New_York.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import socket
import ssl
import struct
import time
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from us_watchlist import load_watchlist, public_metadata


TRADINGVIEW_WS = "wss://data.tradingview.com/socket.io/websocket?from=chart/local/"
NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

SYMBOLS = {
    "SPX": "SP:SPX", "NDX": "NASDAQ:NDX",
    "ES": "CME_MINI:ES1!", "NQ": "CME_MINI:NQ1!",
    "INTC": "NASDAQ:INTC", "NVDA": "NASDAQ:NVDA", "GOOG": "NASDAQ:GOOG",
    "MSFT": "NASDAQ:MSFT", "AAPL": "NASDAQ:AAPL", "SKHY": "NASDAQ:SKHY",
    "TSM": "NYSE:TSM", "SPCX": "NASDAQ:SPCX",
    "SPY": "AMEX:SPY", "QQQ": "NASDAQ:QQQ", "DIA": "AMEX:DIA", "IWM": "AMEX:IWM",
    "XLK": "AMEX:XLK", "SOXX": "NASDAQ:SOXX", "SMH": "NASDAQ:SMH",
    "XLF": "AMEX:XLF", "XLE": "AMEX:XLE", "XLV": "AMEX:XLV", "XLY": "AMEX:XLY",
    "XLP": "AMEX:XLP", "XLI": "AMEX:XLI", "XLU": "AMEX:XLU", "XLC": "AMEX:XLC",
    "XLB": "AMEX:XLB", "XLRE": "AMEX:XLRE",
    "VIX": "CBOE:VIX", "US10Y": "TVC:US10Y", "DXY": "TVC:DXY",
    "WTI": "NYMEX:CL1!", "GOLD": "COMEX:GC1!",
}


def tv_frame(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"))
    return f"~m~{len(body)}~m~{body}"


def tv_msg(method: str, params: list[Any]) -> str:
    return tv_frame({"m": method, "p": params})


def parse_tv_messages(buf: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    index = 0
    while index < len(buf):
        if not buf.startswith("~m~", index):
            break
        marker = buf.find("~m~", index + 3)
        if marker < 0:
            break
        try:
            size = int(buf[index + 3 : marker])
        except ValueError:
            break
        start, end = marker + 3, marker + 3 + size
        if end > len(buf):
            break
        raw, index = buf[start:end], end
        if raw.startswith("~h~"):
            continue
        try:
            messages.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return messages


class WebSocket:
    def __init__(self, url: str, timeout: float) -> None:
        self.url = urlparse(url)
        self.timeout = timeout
        self.sock: ssl.SSLSocket | None = None

    def connect(self) -> None:
        host = self.url.hostname
        if not host:
            raise ValueError("missing WebSocket host")
        path = self.url.path or "/"
        if self.url.query:
            path += "?" + self.url.query
        raw = socket.create_connection((host, self.url.port or 443), timeout=self.timeout)
        sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
            "Origin: https://www.tradingview.com\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(response[:400].decode("latin1", errors="replace"))
        sock.settimeout(self.timeout)
        self.sock = sock

    def send_text(self, text: str) -> None:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        data = text.encode("utf-8")
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header.extend([0x80 | 126])
            header.extend(struct.pack("!H", len(data)))
        else:
            header.extend([0x80 | 127])
            header.extend(struct.pack("!Q", len(data)))
        mask = os.urandom(4)
        header.extend(mask)
        self.sock.sendall(bytes(header) + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data)))

    def _recv_exact(self, size: int) -> bytes:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        chunks: list[bytes] = []
        while size:
            chunk = self.sock.recv(size)
            if not chunk:
                raise EOFError("WebSocket closed")
            chunks.append(chunk)
            size -= len(chunk)
        return b"".join(chunks)

    def recv_text(self) -> str:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        first = self._recv_exact(2)
        b1, b2 = first
        opcode, length = b1 & 0x0F, b2 & 0x7F
        masked = bool(b2 & 0x80)
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else b""
        data = self._recv_exact(length)
        if masked:
            data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
        if opcode == 0x8:
            raise EOFError("WebSocket closed")
        if opcode == 0x9:
            self._send_control(0x8A, data)
            return ""
        return data.decode("utf-8", errors="replace") if opcode == 0x1 else ""

    def _send_control(self, opcode: int, data: bytes) -> None:
        if self.sock is None:
            return
        mask = os.urandom(4)
        self.sock.sendall(bytes([opcode, 0x80 | len(data)]) + mask + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data)))

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None


def session_id(prefix: str) -> str:
    return prefix + "_" + "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(12))


def extract_bars(update: dict[str, Any], series_name: str) -> list[dict[str, Any]]:
    rows = ((update.get(series_name) or {}).get("s") or [])
    bars: list[dict[str, Any]] = []
    for row in rows:
        values = row.get("v") if isinstance(row, dict) else None
        if not isinstance(values, list) or len(values) < 5:
            continue
        stamp, open_, high, low, close = values[:5]
        volume = values[5] if len(values) > 5 else None
        dt = datetime.fromtimestamp(float(stamp), tz=UTC)
        bars.append({
            "timestamp": int(stamp), "time_utc": dt.isoformat(), "time_et": dt.astimezone(NY).isoformat(),
            "open": open_, "high": high, "low": low, "close": close, "volume": volume,
        })
    return bars


def fetch_symbol(symbol: str, resolution: str, countback: int, timeout: float) -> list[dict[str, Any]]:
    ws = WebSocket(TRADINGVIEW_WS, timeout)
    ws.connect()
    chart, quote, series, alias = session_id("cs"), session_id("qs"), "s1", "symbol_1"
    resolved = json.dumps({"symbol": symbol, "adjustment": "splits", "session": "regular"}, separators=(",", ":"))
    for message in [
        tv_msg("set_auth_token", ["unauthorized_user_token"]),
        tv_msg("chart_create_session", [chart, ""]),
        tv_msg("quote_create_session", [quote]),
        tv_msg("quote_set_fields", [quote, "ch", "chp", "lp", "volume", "short_name", "exchange"]),
        tv_msg("quote_add_symbols", [quote, symbol, {"flags": ["force_permission"]}]),
        tv_msg("resolve_symbol", [chart, alias, f"={resolved}"]),
        tv_msg("create_series", [chart, series, "s1", alias, resolution, countback]),
    ]:
        ws.send_text(message)
    bars: list[dict[str, Any]] = []
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            try:
                raw = ws.recv_text()
            except socket.timeout:
                continue
            if raw.startswith("~m~~h~"):
                ws.send_text(raw)
                continue
            for message in parse_tv_messages(raw):
                method, params = message.get("m"), message.get("p", [])
                if method == "timescale_update" and len(params) >= 2:
                    bars = extract_bars(params[1], series)
                elif method == "series_completed":
                    return bars
    finally:
        ws.close()
    return bars


def filter_rth_day(bars: list[dict[str, Any]], report_date: str) -> list[dict[str, Any]]:
    start, end = dtime(9, 30), dtime(16, 0)
    filtered = [bar for bar in bars if datetime.fromisoformat(bar["time_et"]).date().isoformat() == report_date and start <= datetime.fromisoformat(bar["time_et"]).time() <= end]
    return sorted(filtered, key=lambda bar: bar["timestamp"])


def previous_regular_close(bars: list[dict[str, Any]], report_date: str) -> float | None:
    prior = [bar for bar in bars if datetime.fromisoformat(bar["time_et"]).date().isoformat() < report_date and datetime.fromisoformat(bar["time_et"]).time() <= dtime(16, 0)]
    if not prior:
        return None
    close = sorted(prior, key=lambda bar: bar["timestamp"])[-1].get("close")
    return float(close) if isinstance(close, (int, float)) else None


def summarize(bars: list[dict[str, Any]], prior_close: float | None) -> dict[str, Any] | None:
    if not bars:
        return None
    open_, close = bars[0]["open"], bars[-1]["close"]
    volumes = [bar["volume"] for bar in bars if isinstance(bar.get("volume"), (int, float))]
    return {
        "bars": len(bars), "open": open_, "high": max(bar["high"] for bar in bars),
        "low": min(bar["low"] for bar in bars), "close": close, "change": close - open_,
        "change_pct": (close / open_ - 1) * 100 if open_ else None, "previous_close": prior_close,
        "day_change": close - prior_close if prior_close is not None else None,
        "day_change_pct": (close / prior_close - 1) * 100 if prior_close else None,
        "volume": sum(volumes) if volumes else None,
        "first_time_et": bars[0]["time_et"], "last_time_et": bars[-1]["time_et"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="U.S. report date, YYYY-MM-DD")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resolution", default="5")
    parser.add_argument("--countback", type=int, default=1200)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--symbols", nargs="*", help="Explicit base keys/symbols; omit to keep the legacy all-symbol default")
    parser.add_argument("--watchlist-part", choices=["stocks", "sectors", "all"], help="Append the effective local watchlist group")
    parser.add_argument("--watchlist-config", help="Optional one-run watchlist JSON; otherwise use the user-local default")
    args = parser.parse_args()
    try:
        watchlist = load_watchlist(args.watchlist_config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    configured_items = [
        row for group in ("stocks", "sectors") for row in watchlist[group]
        if isinstance(row, dict)
    ]
    configured_symbols = {str(row["ticker"]): str(row["tradingview_symbol"]) for row in configured_items}
    if args.symbols is None:
        requested = [] if args.watchlist_part else list(SYMBOLS)
    else:
        requested = list(args.symbols)
    if args.watchlist_part:
        groups = ("stocks", "sectors") if args.watchlist_part == "all" else (args.watchlist_part,)
        for group in groups:
            for row in watchlist[group]:
                ticker = str(row["ticker"])
                if ticker not in requested:
                    requested.append(ticker)

    result: dict[str, Any] = {
        "source": "TradingView anonymous chart websocket", "source_url": "https://www.tradingview.com/",
        "source_status": "public aggregated chart data; not exchange-certified", "resolution": args.resolution,
        "session": "regular", "rth_window_et": "09:30-16:00", "report_date": args.date,
        "generated_at": datetime.now().astimezone().isoformat(), "symbols": {},
        "us_watchlist": public_metadata(watchlist),
    }
    all_ok = True
    for key in requested:
        symbol = configured_symbols.get(key, SYMBOLS.get(key, key))
        try:
            raw = fetch_symbol(symbol, args.resolution, args.countback, args.timeout)
            rth = filter_rth_day(raw, args.date)
            result["symbols"][key] = {"tradingview_symbol": symbol, "summary": summarize(rth, previous_regular_close(raw, args.date)), "bars": rth}
            all_ok = all_ok and bool(rth)
        except Exception as exc:  # preserve per-symbol failure for audit
            all_ok = False
            result["symbols"][key] = {"tradingview_symbol": symbol, "error": repr(exc), "summary": None, "bars": []}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    print(json.dumps({
        "watchlist_source": watchlist["source"],
        "symbols": {key: value.get("summary") for key, value in result["symbols"].items()},
    }, ensure_ascii=False, indent=2))
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
