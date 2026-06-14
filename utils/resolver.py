import base64
import hashlib
import random
import re
import socket
import string
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import questionary
import requests
import urllib3
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from rich.console import Console

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()

_active_proxy_server = None


class ThreadedHTTPServer(object):
    def __init__(self, host, port, handler_class):
        self.server = HTTPServer((host, port), handler_class)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def get_free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class AbyssProxyHandler(BaseHTTPRequestHandler):
    fd_url = ""
    regular_url = ""
    part_size = 0
    key_str = ""
    total_size = 0

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if not self.path.startswith("/stream"):
            self.send_error(404)
            return

        range_header = self.headers.get("Range")
        start = 0
        end = self.total_size - 1
        is_partial = False

        if range_header:
            is_partial = True
            try:
                range_str = range_header.split("=")[1]
                parts = range_str.split("-")
                start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = int(parts[1])
            except Exception:
                pass

        if start >= self.total_size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{self.total_size}")
            self.end_headers()
            return

        end = min(end, self.total_size - 1)
        content_length = end - start + 1

        if is_partial:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{self.total_size}")
        else:
            self.send_response(200)

        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        try:
            curr_pos = start
            if curr_pos < self.part_size:
                fetch_end = min(end, self.part_size - 1)
                block_offset = (curr_pos // 16) * 16
                skip_bytes = curr_pos % 16

                fd_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://abyssplayer.com/",
                    "Range": f"bytes={block_offset}-{fetch_end}",
                }

                fd_res = requests.get(self.fd_url, headers=fd_headers, timeout=15)
                enc_data = fd_res.content

                hex_md5 = hashlib.md5(self.key_str.encode("utf-8")).hexdigest()
                key_bytes = hex_md5.encode("utf-8")
                iv_bytes = key_bytes[:16]

                initial_counter = int.from_bytes(iv_bytes, byteorder="big")
                block_counter = initial_counter + (curr_pos // 16)
                block_iv = block_counter.to_bytes(16, byteorder="big")

                backend = default_backend()
                cipher = Cipher(
                    algorithms.AES(key_bytes), modes.CTR(block_iv), backend=backend
                )
                decryptor = cipher.decryptor()
                dec_data = decryptor.update(enc_data) + decryptor.finalize()

                self.wfile.write(dec_data[skip_bytes:])
                curr_pos = fetch_end + 1

            if curr_pos <= end:
                reg_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://abyssplayer.com/",
                    "Range": f"bytes={curr_pos}-{end}",
                }
                reg_res = requests.get(
                    self.regular_url, headers=reg_headers, stream=True, timeout=15
                )
                for chunk in reg_res.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        self.wfile.write(chunk)
        except Exception:
            pass


def select_m3u8_resolution(url, referer=None, user_agent=None):
    if not url:
        return url

    if not (".m3u8" in url or "/cf-master." in url):
        return url

    try:
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        if referer:
            headers["Referer"] = referer

        res = requests.get(url, headers=headers, timeout=10, verify=False)
        if res.status_code != 200:
            return url

        content = res.text
        if not content.startswith("#EXTM3U"):
            return url

        lines = content.splitlines()
        streams = []

        master_parsed = urlparse(url)
        master_query = dict(parse_qsl(master_parsed.query))

        current_info = {}
        for line in lines:
            line = line.strip()
            if line.startswith("#EXT-X-STREAM-INF:"):
                res_match = re.search(r"RESOLUTION=(\d+x\d+)", line)
                resolution = res_match.group(1) if res_match else None
                bw_match = re.search(r"BANDWIDTH=(\d+)", line)
                bandwidth = int(bw_match.group(1)) if bw_match else None
                name_match = re.search(r'NAME="([^"]+)"', line)
                name = name_match.group(1) if name_match else None

                current_info = {
                    "resolution": resolution,
                    "bandwidth": bandwidth,
                    "name": name,
                }
            elif line and not line.startswith("#") and current_info:
                sub_url = urljoin(url, line)

                sub_parsed = urlparse(sub_url)
                if not sub_parsed.query and master_query:
                    sub_list = list(sub_parsed)
                    sub_list[4] = urlencode(master_query)
                    sub_url = urlunparse(sub_list)

                current_info["url"] = sub_url
                streams.append(current_info)
                current_info = {}

        if not streams:
            return url

        choices = []
        choices.append({"name": "Auto (Default)", "value": url})

        def get_height(s):
            if s.get("resolution"):
                try:
                    return int(s["resolution"].split("x")[1])
                except Exception:
                    pass
            return 0

        streams.sort(key=get_height, reverse=True)

        for s in streams:
            label = ""
            if s.get("resolution"):
                label += f"{s['resolution'].split('x')[1]}p ({s['resolution']})"
            else:
                label += f"Stream ({s.get('bandwidth', 'Unknown Bandwidth')})"
            if s.get("name"):
                label += f" - {s['name']}"
            choices.append({"name": label, "value": s["url"]})

        if len(choices) <= 2:
            return url

        choice = questionary.select("Select video resolution:", choices=choices).ask()

        if choice:
            return choice

    except Exception:
        pass

    return url


def resolve_server_url(url):
    """Attempt to resolve redirectors or extract direct video links from player pages."""
    if not url:
        return url

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # 1. Resolve redirectors/shorteners
    redirectors = [
        "bit.ly",
        "pndk.to",
        "safelink",
        "inshorturl",
        "shrtm",
        "tinyurl",
        "ouo.io",
        "rebrand.ly",
    ]
    if any(r in url for r in redirectors):
        try:
            console.print(f"[yellow]Resolving redirect:[/yellow] {url}")
            res = requests.head(
                url,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": ua},
            )
            url = res.url
            console.print(f"[green]Resolved to:[/green] {url}")
        except Exception as e:
            console.print(f"[red]Failed to resolve redirect:[/red] {e}")

    # 2. Server-specific handling

    # A. Rumble
    if "rumble.com" in url:
        try:
            match = re.search(r"rumble\.com/(?:embed/|v/)?(v[a-zA-Z0-9]+)", url)
            if match:
                v_id = match.group(1)
                console.print(
                    f"[yellow]Resolving Rumble embed video ID:[/yellow] {v_id}"
                )
                api_url = f"https://rumble.com/embedJS/u3/?request=video&ver=2&v={v_id}"
                res = requests.get(
                    api_url,
                    headers={
                        "User-Agent": ua,
                        "Referer": "https://anichin.moe/",
                    },
                    timeout=10,
                )
                data = res.json()
                hls_url = data.get("hls", {}).get("url") or data.get("ua", {}).get(
                    "hls", {}
                ).get("auto", {}).get("url")
                if hls_url:
                    console.print(f"[green]Resolved Rumble HLS URL:[/green] {hls_url}")
                    return select_m3u8_resolution(
                        hls_url, referer="https://rumble.com/", user_agent=ua
                    )
        except Exception as e:
            console.print(f"[red]Rumble resolution failed:[/red] {e}")

    # B. D-Tube
    if "d.tube" in url:
        try:
            match = re.search(r"d\.tube/(?:embed/|\?v=)?([a-zA-Z0-9-]+)", url)
            if match:
                video_id = match.group(1)
                dtube_hls = f"https://nas1.d.tube/videos/{video_id}/master.m3u8"
                console.print(f"[green]Resolved D-Tube HLS URL:[/green] {dtube_hls}")
                return select_m3u8_resolution(
                    dtube_hls, referer="https://play.d.tube/", user_agent=ua
                )
        except Exception as e:
            console.print(f"[red]D-Tube resolution failed:[/red] {e}")

    # C. Doodstream / playmogo / etc.
    dood_domains = ["dood", "playmogo.com", "mogohtml.xyz", "ds2play.com"]
    if any(d in url for d in dood_domains):
        try:
            parsed = urlparse(url)
            base_host = f"{parsed.scheme}://{parsed.netloc}"

            console.print(f"[yellow]Resolving Doodstream mirror URL:[/yellow] {url}")
            headers = {
                "User-Agent": ua,
                "Referer": "https://anichin.moe/",
            }

            res = requests.get(url, headers=headers, timeout=10)
            html = res.text

            pass_match = re.search(r"\$\.get\('(/pass_md5/[^'\"]+)'", html)
            if pass_match:
                pass_url_path = pass_match.group(1)
                pass_url = f"{base_host}{pass_url_path}"
                token = pass_url_path.split("/")[-1]

                pass_headers = {"User-Agent": headers["User-Agent"], "Referer": url}
                pass_res = requests.get(pass_url, headers=pass_headers, timeout=10)
                base_url = pass_res.text

                if base_url and base_url != "RELOAD":
                    chars = string.ascii_letters + string.digits
                    rand_str = "".join(random.choice(chars) for _ in range(10))
                    expiry = int(time.time() * 1000)
                    resolved_url = f"{base_url}{rand_str}?token={token}&expiry={expiry}"
                    console.print(
                        f"[green]Resolved Doodstream video URL:[/green] {resolved_url}"
                    )
                    return resolved_url
        except Exception as e:
            console.print(f"[red]Doodstream resolution failed:[/red] {e}")

    # D. Abyss Player (abyssplayer.com / New Player)
    if "abyssplayer.com" in url or "abyss.to" in url:
        try:
            console.print("[yellow]Analyzing Abyss Player page...[/yellow]")
            headers = {
                "User-Agent": ua,
                "Referer": "https://anichin.moe/",
            }
            res = requests.get(url, headers=headers, timeout=15)
            html = res.text

            datas_match = re.search(r"const datas\s*=\s*\"([^\"]+)\"", html)
            if not datas_match:
                console.print("[red]Abyss Player datas payload not found.[/red]")
                return url

            binary_json = base64.b64decode(datas_match.group(1))
            dict_data = json_loads(binary_json.decode("latin1"))

            user_id = dict_data["user_id"]
            slug = dict_data["slug"]
            md5_id = dict_data["md5_id"]
            media_bytes = dict_data["media"].encode("latin1")

            key_str = f"{user_id}:{slug}:{md5_id}"
            hex_md5 = hashlib.md5(key_str.encode("utf-8")).hexdigest()
            key_bytes = hex_md5.encode("utf-8")
            iv_bytes = key_bytes[:16]

            backend = default_backend()
            cipher = Cipher(
                algorithms.AES(key_bytes), modes.CTR(iv_bytes), backend=backend
            )
            decryptor = cipher.decryptor()
            decrypted_text = (
                decryptor.update(media_bytes) + decryptor.finalize()
            ).decode("utf-8")

            import json

            media_json = json.loads(decrypted_text)

            sources = media_json.get("mp4", {}).get("sources", [])
            frist_datas = media_json.get("mp4", {}).get("fristDatas", [])

            if not sources:
                console.print(
                    "[red]No video sources found in Abyss Player payload.[/red]"
                )
                return url

            if len(sources) > 1:
                choices = [
                    f"{s.get('label', 'Unknown')} ({s.get('codec', 'h264')})"
                    for s in sources
                ]
                choice = questionary.select(
                    "Select video quality:", choices=choices
                ).ask()
                if not choice:
                    selected_source = sources[0]
                else:
                    idx = choices.index(choice)
                    selected_source = sources[idx]
            else:
                selected_source = sources[0]

            res_id = selected_source.get("res_id")
            matching_fd = None
            for fd in frist_datas:
                if fd.get("res_id") == res_id:
                    matching_fd = fd
                    break

            if not matching_fd:
                full_url = selected_source["url"] + "/" + selected_source["path"]
                console.print(
                    f"[yellow]No .fd chunk info found, using direct URL:[/yellow] {full_url}"
                )
                return full_url

            fd_url = matching_fd["url"]
            regular_url = selected_source["url"] + "/" + selected_source["path"]
            part_size = matching_fd["partSize"]
            stream_key = selected_source["path"].split("/")[-1]
            total_size = selected_source["size"]

            port = get_free_port()

            class ActiveAbyssProxyHandler(AbyssProxyHandler):
                pass

            ActiveAbyssProxyHandler.fd_url = fd_url
            ActiveAbyssProxyHandler.regular_url = regular_url
            ActiveAbyssProxyHandler.part_size = part_size
            ActiveAbyssProxyHandler.key_str = stream_key
            ActiveAbyssProxyHandler.total_size = total_size

            proxy_server = ThreadedHTTPServer(
                "127.0.0.1", port, ActiveAbyssProxyHandler
            )
            proxy_server.start()

            global _active_proxy_server
            _active_proxy_server = proxy_server

            proxy_url = f"http://127.0.0.1:{port}/stream"
            console.print(
                f"[green]Local decryption proxy started on port {port}[/green]"
            )
            return proxy_url

        except Exception as e:
            console.print(f"[red]Failed to resolve Abyss Player stream:[/red] {e}")
            return url

    # E. RPMShare / RPMvid (rpmvid.com)
    if "rpmvid.com" in url or "rpmshare" in url.lower():
        try:
            parsed_url = urlparse(url)
            hash_part = url.split("#")[-1] if "#" in url else ""
            video_id = hash_part.split("&")[0].split("?")[0]
            if video_id:
                console.print(
                    f"[yellow]Resolving RPMShare video ID:[/yellow] {video_id}"
                )
                api_url = f"https://{parsed_url.netloc}/api/v1/video?id={video_id}&w=1920&h=1080&r=anichin.moe"
                res = requests.get(
                    api_url,
                    headers={
                        "User-Agent": ua,
                        "Referer": f"https://{parsed_url.netloc}/",
                    },
                    timeout=10,
                )
                enc_hex = res.text.strip()
                enc_bytes = bytes.fromhex(enc_hex)

                key = b"kiemtienmua911ca"
                iv = b"1234567890oiuytr"

                backend = default_backend()
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
                decryptor = cipher.decryptor()

                dec_data = decryptor.update(enc_bytes) + decryptor.finalize()

                pad_len = dec_data[-1]
                if 1 <= pad_len <= 16:
                    dec_data = dec_data[:-pad_len]

                import json

                data = json.loads(dec_data.decode("utf-8"))
                source_url = data.get("source")
                if source_url:
                    console.print(
                        f"[green]Resolved RPMShare source URL:[/green] {source_url}"
                    )
                    return select_m3u8_resolution(
                        source_url,
                        referer=f"https://{parsed_url.netloc}/",
                        user_agent=ua,
                    )
        except Exception as e:
            console.print(f"[red]RPMShare resolution failed:[/red] {e}")

    # Pixeldrain direct download link is usually faster
    if "pixeldrain.com/u/" in url:
        url = url.replace("/u/", "/api/file/") + "?download"
        return url

    # Extract direct links from known problematic player pages
    player_hosts = [
        "streamlare",
        "streamwish",
        "voe.sx",
        "turbovidhls.com",
        "turbovid",
        "turboviplay.com",
    ]
    if any(p in url for p in player_hosts):
        try:
            console.print(
                "[yellow]Analyzing player page for direct video sources...[/yellow]"
            )
            res = requests.get(
                url,
                timeout=10,
                headers={
                    "Referer": "https://anichin.moe/",
                    "User-Agent": ua,
                },
            )

            patterns = [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
                r'file\s*:\s*["\'](https?://[^"\']+)["\']',
                r'src\s*:\s*["\'](https?://[^"\']+)["\']',
                r'source\s*src=["\'](https?://[^"\']+)["\']',
            ]

            for pattern in patterns:
                match = re.search(pattern, res.text, re.IGNORECASE)
                if match:
                    direct_url = match.group(1).replace("\\/", "/")
                    if direct_url.startswith("//"):
                        direct_url = "https:" + direct_url
                    if any(
                        ext in direct_url.lower()
                        for ext in [".js", ".css", ".png", ".jpg", ".woff"]
                    ):
                        continue
                    console.print(f"[green]Found direct source:[/green] {direct_url}")
                    hls_referer = "https://anichin.moe/"
                    if "d.tube" in direct_url:
                        hls_referer = "https://play.d.tube/"
                    elif "rumble.com" in direct_url:
                        hls_referer = "https://rumble.com/"
                    return select_m3u8_resolution(
                        direct_url, referer=hls_referer, user_agent=ua
                    )
        except Exception as e:
            console.print(f"[red]Analysis failed:[/red] {e}")

    # Auto-resolve HLS resolutions if it's a master playlist
    if url and (".m3u8" in url or "/cf-master." in url):
        hls_referer = "https://anichin.moe/"
        if "rpmvid.com" in url or "/urp/" in url or "185.237." in url:
            hls_referer = "https://anichin.rpmvid.com/"
        elif "rumble.com" in url:
            hls_referer = "https://rumble.com/"
        elif "d.tube" in url:
            hls_referer = "https://play.d.tube/"

        url = select_m3u8_resolution(url, referer=hls_referer, user_agent=ua)

    return url


def json_loads(text):
    import json

    return json.loads(text)


def play_or_view(url, action):
    global _active_proxy_server
    url = resolve_server_url(url)

    referer = "https://anichin.moe/"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    if action == "Play with MPV":
        console.print(f"[bold green]Starting MPV for:[/bold green] {url}")
        cmd = ["mpv", f"--referrer={referer}", f"--user-agent={ua}", url]
        try:
            subprocess.run(cmd)
        except FileNotFoundError:
            console.print("[red]Error: MPV not found.[/red]")
        finally:
            if _active_proxy_server:
                console.print(
                    "[yellow]Stopping local decryption proxy server...[/yellow]"
                )
                _active_proxy_server.stop()
                _active_proxy_server = None
    elif action == "View URL":
        console.print(f"\n[bold cyan]Resolved Video URL:[/bold cyan]\n{url}\n")
        input("Press Enter to continue...")
        if _active_proxy_server:
            _active_proxy_server.stop()
            _active_proxy_server = None
