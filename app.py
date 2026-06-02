#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import socket
import struct
import hashlib
import base64
import asyncio
import aiohttp
import logging
import ipaddress
from pathlib import Path
from aiohttp import web

# ─── 环境变量 ─────────────────────────────────────────────────────────────────
UUID     = os.environ.get('UUID', 'e71a01a5-a04b-443e-a2ea-4aea3c78b71d')
DOMAIN   = os.environ.get('DOMAIN', '')
SUB_PATH = os.environ.get('SUB_PATH', UUID[:23])
NAME     = os.environ.get('NAME', '')
WSPATH   = os.environ.get('WSPATH', UUID[:8])
PORT     = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3002)
DEBUG    = os.environ.get('DEBUG', '').lower() == 'true'

# ─── 全局状态 ──────────────────────────────────────────────────────────────────
CurrentDomain = DOMAIN
CurrentPort   = 443
Tls           = 'tls'
ISP           = ''

# ─── DNS & 屏蔽域名 ────────────────────────────────────────────────────────────
DNS_SERVERS = ['8.8.4.4', '1.1.1.1']
BLOCKED_DOMAINS = {
    'speedtest.net', 'fast.com', 'speedtest.cn', 'speed.cloudflare.com',
    'speedof.me', 'testmy.net', 'bandwidth.place', 'speed.io',
    'librespeed.org', 'speedcheck.org',
}

# ─── 个人生活网页路由映射（路径 → HTML文件名）────────────────────────────────────
LIFE_PAGES = {
    '/':            'index.html',
    '/cooking':     'cooking.html',
    '/fitness':     'fitness.html',
    '/travel':      'travel.html',
    '/mindfulness': 'mindfulness.html',
    '/home':        'home_decor.html',
}

# ─── 日志（生产环境静默）────────────────────────────────────────────────────────
logging.disable(logging.CRITICAL)
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ══════════════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════════════

def is_port_available(port: int, host: str = '0.0.0.0') -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(start: int, max_attempts: int = 100) -> int | None:
    for port in range(start, start + max_attempts):
        if is_port_available(port):
            return port
    return None


def is_blocked_domain(host: str) -> bool:
    if not host:
        return False
    h = host.lower()
    return any(h == b or h.endswith('.' + b) for b in BLOCKED_DOMAINS)


def read_html(filename: str) -> str | None:
    """从多个候选目录按顺序查找 HTML 文件，返回内容或 None。"""
    candidates = [
        Path(filename),
        Path('life_pages') / filename,
        Path(__file__).parent / filename,
        Path(__file__).parent / 'life_pages' / filename,
    ]
    for path in candidates:
        try:
            return path.read_text(encoding='utf-8')
        except (FileNotFoundError, OSError):
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 网络辅助
# ══════════════════════════════════════════════════════════════════════════════

async def get_isp() -> None:
    global ISP
    apis = [
        ('https://api.ip.sb/geoip',    lambda d: f"{d.get('country_code','')}-{d.get('isp','')}"),
        ('http://ip-api.com/json',      lambda d: f"{d.get('countryCode','')}-{d.get('org','')}"),
    ]
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        for url, extract in apis:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        ISP = extract(await resp.json()).replace(' ', '_')
                        return
            except Exception:
                continue
    ISP = 'Unknown'


async def get_ip() -> None:
    global CurrentDomain, Tls, CurrentPort
    if not DOMAIN or DOMAIN == 'your-domain.com':
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api-ipv4.ip.sb/ip',
                                       timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        CurrentDomain = (await resp.text()).strip()
                        Tls, CurrentPort = 'none', PORT
                        return
        except Exception:
            pass
        CurrentDomain, Tls, CurrentPort = 'change-your-domain.com', 'tls', 443
    else:
        CurrentDomain, Tls, CurrentPort = DOMAIN, 'tls', 443


async def resolve_host(host: str) -> str:
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    try:
        async with aiohttp.ClientSession() as session:
            url = f'https://dns.google/resolve?name={host}&type=A'
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('Status') == 0:
                        for answer in data.get('Answer', []):
                            if answer.get('type') == 1:
                                return answer['data']
    except Exception:
        pass
    return host


# ══════════════════════════════════════════════════════════════════════════════
# 双向流转发（公共逻辑）
# ══════════════════════════════════════════════════════════════════════════════

async def _forward(websocket, reader: asyncio.StreamReader,
                   writer: asyncio.StreamWriter) -> None:
    """在 WebSocket 和 TCP 流之间双向转发数据。"""

    async def ws_to_tcp():
        try:
            async for msg in websocket:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    writer.write(msg.data)
                    await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def tcp_to_ws():
        try:
            while chunk := await reader.read(4096):
                await websocket.send_bytes(chunk)
        except Exception:
            pass

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())


# ══════════════════════════════════════════════════════════════════════════════
# 代理协议处理
# ══════════════════════════════════════════════════════════════════════════════

class ProxyHandler:
    def __init__(self, uuid: str):
        self.uuid_bytes = bytes.fromhex(uuid)

    # ── 地址解析辅助 ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_addr(data: bytes, offset: int) -> tuple[str, int, int] | None:
        """
        解析地址类型 + 地址 + 端口（VLESS/Shadowsocks 格式）。
        返回 (host, port, new_offset) 或 None（解析失败）。
        atyp=1 IPv4，atyp=2 域名（VLESS），atyp=3 IPv6（VLESS），
              atyp=4 IPv6（SS），atyp=3 域名（SS 传入 is_ss=True 时）。
        """
        if offset >= len(data):
            return None
        atyp = data[offset]; offset += 1

        host = ''
        if atyp == 1:                          # IPv4
            if offset + 4 > len(data): return None
            host = '.'.join(str(b) for b in data[offset:offset+4])
            offset += 4
        elif atyp in (2, 3):                   # 域名 (VLESS=2, SS=3)
            if offset >= len(data): return None
            hl = data[offset]; offset += 1
            if offset + hl > len(data): return None
            host = data[offset:offset+hl].decode()
            offset += hl
        elif atyp in (3, 4):                   # IPv6 (VLESS=3, SS=4)
            if offset + 16 > len(data): return None
            host = ':'.join(f'{(data[j]<<8)+data[j+1]:04x}' for j in range(offset, offset+16, 2))
            offset += 16
        else:
            return None

        if offset + 2 > len(data): return None
        port = struct.unpack('!H', data[offset:offset+2])[0]
        return host, port, offset + 2

    # ── VLESS ─────────────────────────────────────────────────────────────────

    async def handle_vless(self, ws, data: bytes) -> bool:
        try:
            if len(data) < 18 or data[0] != 0:
                return False
            if data[1:17] != self.uuid_bytes:
                return False

            i = data[17] + 19          # skip addon length
            if i + 3 > len(data):
                return False

            port = struct.unpack('!H', data[i:i+2])[0]; i += 2
            atyp = data[i]; i += 1

            result = self._parse_addr(bytes([atyp]) + data[i:], 0)
            if result is None:
                return False
            host, _, rel_offset = result
            i += rel_offset - 1        # -1 因为我们已经跳过了 atyp

            if is_blocked_domain(host):
                await ws.close(); return False

            await ws.send_bytes(bytes([0, 0]))
            reader, writer = await asyncio.open_connection(await resolve_host(host), port)
            if i < len(data):
                writer.write(data[i:]); await writer.drain()
            await _forward(ws, reader, writer)
            return True
        except Exception as e:
            if DEBUG: logger.error(f"VLESS error: {e}")
            return False

    # ── Trojan ────────────────────────────────────────────────────────────────

    async def handle_trojan(self, ws, data: bytes) -> bool:
        try:
            if len(data) < 58:
                return False
            # 56 bytes password hex hash + 2 bytes CRLF
            i = 58
            if i + 3 > len(data):
                return False

            cmd = data[i]; i += 1
            if cmd != 1:
                return False

            result = self._parse_addr(data, i)
            if result is None:
                return False
            host, port, i = result

            if is_blocked_domain(host):
                await ws.close(); return False

            # skip CRLF after addr+port
            if i + 2 <= len(data):
                i += 2

            reader, writer = await asyncio.open_connection(await resolve_host(host), port)
            if i < len(data):
                writer.write(data[i:]); await writer.drain()
            await _forward(ws, reader, writer)
            return True
        except Exception as e:
            if DEBUG: logger.error(f"Trojan error: {e}")
            return False

    # ── Shadowsocks ───────────────────────────────────────────────────────────

    async def handle_shadowsocks(self, ws, data: bytes) -> bool:
        try:
            if len(data) < 7:
                return False
            result = self._parse_addr(data, 0)
            if result is None:
                return False
            host, port, offset = result

            if is_blocked_domain(host):
                await ws.close(); return False

            reader, writer = await asyncio.open_connection(await resolve_host(host), port)
            if offset < len(data):
                writer.write(data[offset:]); await writer.drain()
            await _forward(ws, reader, writer)
            return True
        except Exception as e:
            if DEBUG: logger.error(f"Shadowsocks error: {e}")
            return False


# ══════════════════════════════════════════════════════════════════════════════
# HTTP / WebSocket 处理器
# ══════════════════════════════════════════════════════════════════════════════

async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    if f'/{WSPATH}' not in request.path:
        await ws.close(); return ws

    proxy = ProxyHandler(UUID.replace('-', ''))
    try:
        first = await asyncio.wait_for(ws.receive(), timeout=5)
        if first.type != aiohttp.WSMsgType.BINARY:
            await ws.close(); return ws

        d = first.data
        if len(d) > 17 and d[0] == 0 and await proxy.handle_vless(ws, d):
            return ws
        if len(d) >= 58 and await proxy.handle_trojan(ws, d):
            return ws
        if d and d[0] in (1, 3, 4) and await proxy.handle_shadowsocks(ws, d):
            return ws

        await ws.close()
    except asyncio.TimeoutError:
        await ws.close()
    except Exception as e:
        if DEBUG: logger.error(f"WS handler error: {e}")
        await ws.close()

    return ws


async def life_page_handler(request: web.Request) -> web.Response:
    """处理所有个人生活类 HTML 页面请求。"""
    path = request.path
    filename = LIFE_PAGES.get(path)
    if filename:
        content = read_html(filename)
        if content:
            return web.Response(text=content, content_type='text/html')
        # 文件缺失时返回简洁的占位页面
        return web.Response(
            text=_placeholder_html(path.lstrip('/').capitalize() or 'Home'),
            content_type='text/html',
        )
    return web.Response(status=404, text='Not Found\n')


async def sub_handler(request: web.Request) -> web.Response:
    """生成代理订阅内容。"""
    await get_isp()
    await get_ip()

    name_part   = f"{NAME}-{ISP}" if NAME else ISP
    tls_param   = 'tls' if Tls == 'tls' else 'none'
    ss_tls_flag = 'tls;' if Tls == 'tls' else ''

    vless_url = (
        f"vless://{UUID}@{CurrentDomain}:{CurrentPort}"
        f"?encryption=none&security={tls_param}&sni={CurrentDomain}"
        f"&fp=chrome&type=ws&host={CurrentDomain}&path=%2F{WSPATH}#{name_part}"
    )
    trojan_url = (
        f"trojan://{UUID}@{CurrentDomain}:{CurrentPort}"
        f"?security={tls_param}&sni={CurrentDomain}"
        f"&fp=chrome&type=ws&host={CurrentDomain}&path=%2F{WSPATH}#{name_part}"
    )
    ss_pwd = base64.b64encode(f"none:{UUID}".encode()).decode()
    ss_url = (
        f"ss://{ss_pwd}@{CurrentDomain}:{CurrentPort}"
        f"?plugin=v2ray-plugin;mode%3Dwebsocket;host%3D{CurrentDomain}"
        f";path%3D%2F{WSPATH};{ss_tls_flag}sni%3D{CurrentDomain}"
        f";skip-cert-verify%3Dtrue;mux%3D0#{name_part}"
    )
    payload = base64.b64encode(f"{vless_url}\n{trojan_url}\n{ss_url}".encode()).decode()
    return web.Response(text=payload + '\n', content_type='text/plain')


def _placeholder_html(title: str) -> str:
    """当 HTML 文件未找到时返回的简洁占位页面。"""
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        f'<title>{title} · Everyday Life</title>'
        f'<style>body{{font-family:sans-serif;display:flex;align-items:center;'
        f'justify-content:center;height:100vh;margin:0;background:#f5f0e8;color:#3d2b1f;}}'
        f'</style></head><body>'
        f'<div style="text-align:center"><h1>{title}</h1>'
        f'<p style="opacity:.6">Place <code>{title.lower()}.html</code> in the app directory.</p>'
        f'<a href="/" style="color:#c4622d">← Home</a></div></body></html>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# 应用入口
# ══════════════════════════════════════════════════════════════════════════════

def build_app() -> web.Application:
    app = web.Application()

    # ── 个人生活网页路由 ──────────────────────────────────────────────────────
    for path in LIFE_PAGES:
        app.router.add_get(path, life_page_handler)

    # ── 订阅路由 ───────────────────────────────────────────────────────────────
    app.router.add_get(f'/{SUB_PATH}', sub_handler)

    # ── WebSocket 代理路由 ─────────────────────────────────────────────────────
    app.router.add_get(f'/{WSPATH}', websocket_handler)

    return app


async def main() -> None:
    actual_port = PORT
    if not is_port_available(actual_port):
        actual_port = find_available_port(actual_port + 1)
        if actual_port is None:
            sys.exit(1)

    app = build_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', actual_port).start()

    try:
        await asyncio.Future()          # 永久运行
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
