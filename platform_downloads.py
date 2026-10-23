from __future__ import annotations

import ipaddress
import logging
import os
import shutil
import socket
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger(__name__)
PLATFORM_SHORTLINK_HOSTS = {"fb.watch", "vm.tiktok.com", "vt.tiktok.com"}

EMBEDDED_YOUTUBE_COOKIES = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	1807423494	__Secure-BUCKET	CNoD
.youtube.com	TRUE	/	TRUE	1807423496	__Secure-ROLLOUT_TOKEN	CKqe2_yd9LW88QEQuOyev6m2lwMYteyCwKm2lwM%3D
.youtube.com	TRUE	/	TRUE	1807423494	__Secure-YNID	CvYBCAUSqAEB8QZuZhneCJwGXOhGpSf2mh3Vsiy4BkerehFcA_83nSuGV5lYpNSDxny8oefgdaVnchhFSFdjjDsYvkkym3yyUncFgzt1plNbqcrFNPsssJaDR8JHyWAsbMcweamyJANMsP4BoDtUk-8bMS8WE3gaNbkXNt3a8p85mjbNyWrPqWmDbYTr9goRF54XvRdHU3PjgAOHZwkCORhZ-sC12y-DKqmfo639yU8oBTJFAd6pnU-GGBX3vaqWVW9xID7t7Ziinwr-OojhPpTXNnSt_3rpYo410QV3HY1jVKhilYmbSexFGpJt62wwZFmPTUviO-sL
.youtube.com	TRUE	/	TRUE	1812995364	PREF	tz=Asia.Calcutta&f4=4000000
.youtube.com	TRUE	/	TRUE	1807509445	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgQg%3D%3D
.youtube.com	TRUE	/	TRUE	1807509445	VISITOR_INFO1_LIVE	op9W4TkXUes
.youtube.com	TRUE	/	FALSE	1826903408	HSID	AeW5L1QYNvulCRQaP
.youtube.com	TRUE	/	FALSE	1826903408	APISID	e8gM2Kisf5B55UBT/AdpH0fFp_fE5-1FV3
.youtube.com	TRUE	/	TRUE	1826903408	SAPISID	BH0RNVipQzE6y4u6/AaMU5jBG8zJ-s655r
.youtube.com	TRUE	/	FALSE	1826903408	SID	g.a000DwlsHGwkLAaPtcdD4mAHwX66viaa5H1Tgkhcoq_VUpKO9a3xuQqD5PJDhEuS-KKmo9apswACgYKAfoSARASFQHGX2Mi4rAOsNNZCfbQYKQ5HMbi6BoVAUF8yKoyr_COey2y8YGI3XG8JWtl0076
.youtube.com	TRUE	/	TRUE	1826903408	SSID	A0ajl6Z8Q4Z1tTr2u
.youtube.com	TRUE	/	TRUE	1826903408	__Secure-1PAPISID	BH0RNVipQzE6y4u6/AaMU5jBG8zJ-s655r
.youtube.com	TRUE	/	TRUE	1826903408	__Secure-1PSID	g.a000DwlsHGwkLAaPtcdD4mAHwX66viaa5H1Tgkhcoq_VUpKO9a3xJqgCpQGpCf6VdrLi-T63EQACgYKAdwSARASFQHGX2MiDD9IZibWbl-5aSowd-IsyBoVAUF8yKo1vC_lqurZOKdPqvXt_LCh0076
.youtube.com	TRUE	/	TRUE	1826903408	__Secure-3PAPISID	BH0RNVipQzE6y4u6/AaMU5jBG8zJ-s655r
.youtube.com	TRUE	/	TRUE	1826903408	__Secure-3PSID	g.a000DwlsHGwkLAaPtcdD4mAHwX66viaa5H1Tgkhcoq_VUpKO9a3xkZ7mzgqnsXEnWk4fOmrQlQACgYKAfASARASFQHGX2MiK09Zi3tOj-tKdGrwccdKGxoVAUF8yKr5G9B1jZWZKEw5uBOTjDHX0076
.youtube.com	TRUE	/	FALSE	1823883771	SIDCC	AKEyXzV4cnyycGPDVpVH0xJsghSHGVM_jbPx0yeSYPSZ1R0U-4UjWgRaaLhQa7RWW0igmVGX
.youtube.com	TRUE	/	TRUE	1823883771	__Secure-1PSIDCC	AKEyXzW_HEfuaXHN4y2T3gW6rBPqpUPeWfI9u6m6U63FIFMNTkzw4ikdnpYK018cEqsv4iGv
.youtube.com	TRUE	/	TRUE	1823883771	__Secure-1PSIDTS	sidts-CjYBkldj_5WN41iaw7C-p292ntZJkGnJlnCPbb0TqbhprOQx1MjXLOpUdW_H008DcgeIX8PC1SQQAA
.youtube.com	TRUE	/	TRUE	1823883771	__Secure-3PSIDCC	AKEyXzXf9LZXgqomSYW0SbYJSfAwrbPEh8QEyJkqTzH7-_dvi2f-6M_60HBztkmu2aLjFbmveA
.youtube.com	TRUE	/	TRUE	1823883771	__Secure-3PSIDTS	sidts-CjYBkldj_5WN41iaw7C-p292ntZJkGnJlnCPbb0TqbhprOQx1MjXLOpUdW_H008DcgeIX8PC1SQQAA
"""

def get_youtube_cookies_path() -> str | None:
    candidate_paths = [
        os.getenv("YTDLP_COOKIES_FILE", "").strip(),
        "cookies.txt",
        "./cookies.txt",
        str(Path(__file__).parent / "cookies.txt"),
        "/tmp/cookies.txt",
    ]
    for cp in candidate_paths:
        if cp and Path(cp).is_file() and Path(cp).stat().st_size > 0:
            return str(Path(cp).resolve())
    try:
        fallback = Path("cookies.txt")
        fallback.write_text(EMBEDDED_YOUTUBE_COOKIES.strip() + "\n", encoding="utf-8")
        return str(fallback.resolve())
    except Exception:
        try:
            tmp_path = Path("/tmp/cookies.txt")
            tmp_path.write_text(EMBEDDED_YOUTUBE_COOKIES.strip() + "\n", encoding="utf-8")
            return str(tmp_path)
        except Exception:
            return None

PLATFORM_HOST_HINTS = {
    "facebook.com", "fb.watch", "youtube.com", "youtu.be", "instagram.com",
    "tiktok.com", "twitter.com", "x.com", "reddit.com", "twitch.tv",
}


@lru_cache(maxsize=512)
def _matching_platform_extractor(url: str):
    """Return a yt-dlp extractor for a platform page, excluding its catch-all IE."""
    try:
        from yt_dlp.extractor import gen_extractor_classes
    except ImportError as exc:  # pragma: no cover - covered by deployment dependency
        raise RuntimeError("Falta yt-dlp; instala las dependencias del bot.") from exc

    for extractor_class in gen_extractor_classes():
        try:
            if extractor_class.ie_key() == "Generic":
                continue
            if extractor_class.suitable(url):
                return extractor_class.ie_key()
        except Exception:
            continue
    return None


def is_supported_platform_url(url: str) -> bool:
    """Whether yt-dlp has a site-specific extractor for this URL."""
    if _matching_platform_extractor(url) is not None:
        return True
    host = (urlsplit(url).hostname or "").rstrip(".").lower()
    return any(host == domain or host.endswith("." + domain) for domain in PLATFORM_HOST_HINTS)


def is_play_store_page(url: str) -> bool:
    """Return whether URL is an app listing, not a direct APK resource."""
    parts = urlsplit(url)
    host = (parts.hostname or "").rstrip(".").lower()
    return host == "play.google.com" and parts.path.rstrip("/").startswith("/store/apps/details")


def _check_public_dns_target(url: str) -> None:
    """Reject private/local targets before handing a platform URL to yt-dlp."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Solo se admiten enlaces HTTP/HTTPS válidos.")
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("No se admiten hosts locales.")
    try:
        address = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        try:
            addresses = socket.getaddrinfo(
                host,
                parts.port or (443 if parts.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise ValueError("No se pudo validar el host del enlace.") from exc
        resolved = {ipaddress.ip_address(item[4][0].split("%", 1)[0]) for item in addresses}
        if not resolved or any(not address.is_global for address in resolved):
            raise ValueError("El enlace resuelve a una dirección privada o no pública.")
    else:
        if not address.is_global:
            raise ValueError("No se admiten direcciones IP privadas.")


def download_platform_video(
    url: str,
    output_dir: str | Path,
    *,
    max_bytes: int,
    max_duration_seconds: int = 24 * 60 * 60,
    progress_hook=None,
    is_cancelled=None,
) -> tuple[Path, str, int]:
    """Download one public video through yt-dlp and return (path, name, size).

    The caller owns and must remove output_dir after uploading the returned file.
    yt-dlp can handle only the public sources and extractors it currently supports;
    it cannot bypass logins, private posts, DRM, or platform restrictions.
    """
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as exc:  # pragma: no cover - covered by deployment dependency
        raise RuntimeError("Falta yt-dlp; instala las dependencias del bot.") from exc

    if not is_supported_platform_url(url):
        raise ValueError("La plataforma de este enlace no está soportada por yt-dlp.")
    _check_public_dns_target(url)

    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()

    def check_progress(data):
        if max_duration_seconds > 0 and time.monotonic() - started_at > max_duration_seconds:
            raise DownloadError("Se agotó el tiempo máximo de descarga.")
        if is_cancelled and is_cancelled():
            raise DownloadError("Descarga cancelada.")
        downloaded = int(data.get("downloaded_bytes") or 0)
        if max_bytes > 0 and downloaded > max_bytes:
            raise DownloadError(f"El vídeo supera el límite de {max_bytes} bytes.")
        if progress_hook and data.get("status") == "downloading":
            total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
            progress_hook(downloaded, total)

    base_options = {
        # Prefer MP4 where available, but retain the platform's best video if it
        # only offers another format. ffmpeg merges separate video/audio streams.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": str(folder / "%(title).160B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "max_filesize": max_bytes,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,
        "progress_hooks": [check_progress],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "cachedir": False,
        "writeinfojson": False,
        "writethumbnail": False,
        # YouTube actualmente requiere ejecutar el desafío JavaScript para
        # resolver firmas y formatos. Docker instala Node.js y yt-dlp-ejs.
        "js_runtimes": {"node": {}},
    }
    cookie_path = get_youtube_cookies_path()
    if cookie_path:
        base_options["cookiefile"] = cookie_path
    base_options["extractor_args"] = {
        "youtube": {
            "player_client": ["android", "web", "mweb"]
        }
    }

    profiles = [
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": url,
        },
        {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                "Chrome/131.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": url,
        },
    ]
    last_error = "No se pudo extraer el vídeo."
    for attempt, headers in enumerate(profiles):
        if attempt:
            for old_file in folder.iterdir():
                if old_file.is_file():
                    old_file.unlink(missing_ok=True)
                elif old_file.is_dir():
                    shutil.rmtree(old_file, ignore_errors=True)
        options = {**base_options, "http_headers": headers}
        try:
            with YoutubeDL(options) as downloader:
                downloader.extract_info(url, download=True)
        except DownloadError as exc:
            if is_cancelled and is_cancelled():
                raise RuntimeError("Descarga cancelada.") from exc
            last_error = str(exc).strip() or last_error
            continue
        candidates = [
            path for path in folder.iterdir()
            if path.is_file() and not path.name.endswith((".part", ".ytdl"))
        ]
        if candidates:
            break
    else:
        message = last_error
        if "empty media" in message.lower() or "no media" in message.lower():
            message = (
                "La plataforma no entregó ningún medio. Comprueba que el vídeo sea público; "
                "si Facebook pide iniciar sesión, configura YTDLP_COOKIES_FILE con cookies autorizadas."
            )
        elif "sign in to confirm" in message.lower() or "not a bot" in message.lower():
            message = (
                "YouTube bloqueó esta solicitud automática. Configura YTDLP_COOKIES_FILE "
                "con cookies autorizadas de YouTube y vuelve a intentarlo."
            )
        raise ValueError(message[:300])

    candidates = [
        path for path in folder.iterdir()
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    ]
    if not candidates:
        raise ValueError("La plataforma no produjo ningún archivo de vídeo descargable.")
    if len(candidates) > 1:
        # No playlists are requested; choose the largest completed media object
        # if a site happens to leave a sidecar behind despite disabled metadata.
        candidates.sort(key=lambda path: path.stat().st_size, reverse=True)
    video_path = candidates[0]
    size = video_path.stat().st_size
    if size <= 0:
        raise ValueError("La plataforma devolvió un archivo vacío.")
    if max_bytes > 0 and size > max_bytes:
        raise ValueError(f"El vídeo supera el límite de {max_bytes} bytes.")
    return video_path, video_path.name, size
