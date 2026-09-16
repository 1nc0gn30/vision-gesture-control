"""Cross-platform compatibility layer for vision-gesture-control.

Provides cross-platform support across Linux, Termux (Android), macOS, and Windows.
Includes UTF-8 stream configuration, atomic file operations, POSIX path conversion,
browser launcher utilities, and runtime environment diagnostics with zero external
dependencies.
"""

from __future__ import annotations

import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Stream & Encoding Configuration
# ---------------------------------------------------------------------------

def configure_utf8_streams() -> bool:
    """Configures stdout and stderr streams to use UTF-8 encoding safely.

    Returns:
        True if configuration succeeded or was already UTF-8, False otherwise.
    """
    success = True
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
            elif hasattr(stream, "detach") and hasattr(stream, "buffer"):
                # Fallback wrapper for streams lacking reconfigure
                setattr(
                    sys,
                    stream_name,
                    io.TextIOWrapper(
                        stream.buffer,
                        encoding="utf-8",
                        errors="replace",
                        line_buffering=True,
                    ),
                )
        except Exception:
            success = False
    return success


def safe_print(*args: Any, sep: str = " ", end: str = "\n", file: Optional[Any] = None) -> None:
    """Prints strings safely without throwing UnicodeEncodeError on restrictive terminals.

    Args:
        *args: Values to print.
        sep: String inserted between values.
        end: String appended after the last value.
        file: Target stream (defaults to sys.stdout).
    """
    target = file if file is not None else sys.stdout
    text = sep.join(str(arg) for arg in args) + end
    try:
        target.write(text)
        target.flush()
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", "utf-8") or "utf-8"
        encoded = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        target.write(encoded)
        target.flush()
    except Exception:
        # Fallback raw write
        try:
            sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Atomic File Operations
# ---------------------------------------------------------------------------

def atomic_write_bytes(filepath: Union[str, Path], data: bytes) -> None:
    """Atomically writes raw bytes to a file using a temporary file replacement.

    Args:
        filepath: Destination path for the file.
        data: Raw bytes to write.

    Raises:
        OSError: If writing or renaming fails.
    """
    path = Path(filepath).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_name = f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}.{uuid.uuid4().hex[:8]}"
    temp_path = path.parent / temp_name

    try:
        with open(temp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def atomic_write_text(
    filepath: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> None:
    """Atomically writes text to a file using UTF-8 or specified encoding.

    Args:
        filepath: Destination path for the file.
        content: String content to write.
        encoding: Character encoding (default 'utf-8').
        errors: Error handling mode.
    """
    data = content.encode(encoding=encoding, errors=errors)
    atomic_write_bytes(filepath, data)


def atomic_write_json(
    filepath: Union[str, Path],
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    encoding: str = "utf-8",
) -> None:
    """Atomically writes serializable Python data to a JSON file.

    Args:
        filepath: Destination path for the file.
        data: Python object to serialize.
        indent: JSON indentation spaces.
        ensure_ascii: Whether to escape non-ASCII characters.
        sort_keys: Whether to sort dictionary keys.
        encoding: Character encoding.
    """
    json_str = json.dumps(
        data,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
    ) + "\n"
    atomic_write_text(filepath, json_str, encoding=encoding)


# ---------------------------------------------------------------------------
# POSIX Path Conversions & Sanitization
# ---------------------------------------------------------------------------

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def to_posix_path(path: Union[str, Path]) -> str:
    """Normalizes any path (Windows backslashes, mixed slashes) into POSIX format.

    Args:
        path: Path string or Path object.

    Returns:
        Normalized path string with forward slashes.
    """
    path_str = str(path).strip()
    if not path_str:
        return ""
    # Normalize backslashes to forward slashes
    posix = path_str.replace("\\", "/")
    # Collapse consecutive slashes while preserving leading double slashes (for UNC)
    if posix.startswith("//"):
        posix = "//" + re.sub(r"/+", "/", posix[2:])
    else:
        posix = re.sub(r"/+", "/", posix)
    return posix


def from_posix_path(path: str) -> str:
    """Converts a POSIX path string to native operating system format.

    Args:
        path: POSIX path string.

    Returns:
        Native path string using system separator.
    """
    if not path:
        return ""
    if os.sep == "\\":
        return path.replace("/", "\\")
    return path


def resolve_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
) -> str:
    """Resolves relative paths, user paths (~), and symlinks to normalized POSIX string.

    Args:
        path: Target path to resolve.
        base_dir: Optional base directory for relative paths.

    Returns:
        Absolute normalized POSIX path string.
    """
    p = Path(path).expanduser()
    if not p.is_absolute() and base_dir is not None:
        p = (Path(base_dir).expanduser() / p).resolve()
    else:
        p = p.resolve()
    return to_posix_path(p)


def sanitize_filename(name: str, replacement: str = "_", max_length: int = 255) -> str:
    """Sanitizes illegal characters for cross-platform filesystem compatibility.

    Cross-platform safe across Linux, Windows, macOS, and Android.

    Args:
        name: Proposed file name or folder name.
        replacement: Character to replace forbidden symbols with.
        max_length: Maximum allowed filename length.

    Returns:
        Sanitized filename string.
    """
    if not name:
        return "unnamed"

    # Strip illegal characters
    cleaned = _INVALID_FILENAME_CHARS.sub(replacement, name)

    # Windows reserved filenames check
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    stem = cleaned.split(".")[0].upper()
    if stem in reserved:
        cleaned = f"_{cleaned}"

    # Strip trailing periods and spaces (illegal on Windows)
    cleaned = cleaned.rstrip(". ")

    if not cleaned:
        cleaned = "unnamed"

    # Truncate length if needed
    if len(cleaned) > max_length:
        ext_idx = cleaned.rfind(".")
        if ext_idx != -1 and len(cleaned) - ext_idx < 16:
            ext = cleaned[ext_idx:]
            cleaned = cleaned[: max_length - len(ext)] + ext
        else:
            cleaned = cleaned[:max_length]

    return cleaned


# ---------------------------------------------------------------------------
# Platform Diagnostics & Environment Detection
# ---------------------------------------------------------------------------

def is_termux() -> bool:
    """Detects whether running inside a Termux Android environment."""
    prefix = os.environ.get("PREFIX", "")
    termux_ver = os.environ.get("TERMUX_VERSION", "")
    data_dir = os.environ.get("ANDROID_DATA", "")
    return (
        bool(termux_ver)
        or "com.termux" in prefix
        or "/data/data/com.termux" in prefix
        or "/data/data/com.termux" in data_dir
        or os.path.exists("/data/data/com.termux")
    )


def is_wsl() -> bool:
    """Detects whether running inside Windows Subsystem for Linux (WSL)."""
    if "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ:
        return True
    try:
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                return "microsoft" in content or "wsl" in content
    except Exception:
        pass
    return False


def is_android() -> bool:
    """Detects whether running on Android (via Termux, Pydroid, or native)."""
    if is_termux():
        return True
    if hasattr(sys, "getandroidapilevel"):
        return True
    if "ANDROID_ROOT" in os.environ or "ANDROID_BOOTLOGO" in os.environ:
        return True
    return False


def is_macos() -> bool:
    """Detects macOS platform."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Detects Windows platform."""
    return sys.platform.startswith("win") or os.name == "nt"


def is_linux() -> bool:
    """Detects generic Linux platform (excluding Termux/Android)."""
    return sys.platform.startswith("linux") and not is_android()


def is_headless() -> bool:
    """Detects whether running in a headless environment without a display server."""
    # Check display server variables on Linux/macOS
    if is_windows():
        return False
    if is_macos():
        # macOS generally has a window server unless in SSH session
        return "SSH_CONNECTION" in os.environ and "DISPLAY" not in os.environ

    has_x11 = bool(os.environ.get("DISPLAY"))
    has_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    is_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))

    if is_ci:
        return not (has_x11 or has_wayland)

    if not (has_x11 or has_wayland):
        return True

    return False


def get_terminal_size(default: Tuple[int, int] = (80, 24)) -> Tuple[int, int]:
    """Returns the current terminal width and height safely.

    Args:
        default: Fallback tuple (columns, lines).

    Returns:
        Tuple of (columns, lines).
    """
    try:
        cols, lines = shutil.get_terminal_size(fallback=default)
        return (cols, lines)
    except Exception:
        return default


def get_system_diagnostics() -> Dict[str, Any]:
    """Gathers comprehensive runtime system diagnostics.

    Returns:
        Dictionary containing platform, OS, terminal, and runtime information.
    """
    cols, lines = get_terminal_size()
    return {
        "platform": sys.platform,
        "os_name": os.name,
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "python_version": platform.python_version(),
        "python_executable": to_posix_path(sys.executable),
        "cpu_count": os.cpu_count() or 1,
        "is_termux": is_termux(),
        "is_wsl": is_wsl(),
        "is_android": is_android(),
        "is_macos": is_macos(),
        "is_windows": is_windows(),
        "is_linux": is_linux(),
        "is_headless": is_headless(),
        "terminal_size": {"columns": cols, "lines": lines},
        "encoding": {
            "stdout": getattr(sys.stdout, "encoding", "unknown"),
            "stderr": getattr(sys.stderr, "encoding", "unknown"),
            "filesystem": sys.getfilesystemencoding(),
            "default": sys.getdefaultencoding(),
        },
    }


def diagnostics_summary() -> str:
    """Formats system diagnostics into a clean human-readable diagnostic report string."""
    diag = get_system_diagnostics()
    env_flags = []
    if diag["is_termux"]:
        env_flags.append("Termux")
    if diag["is_wsl"]:
        env_flags.append("WSL")
    if diag["is_android"]:
        env_flags.append("Android")
    if diag["is_macos"]:
        env_flags.append("macOS")
    if diag["is_windows"]:
        env_flags.append("Windows")
    if diag["is_linux"]:
        env_flags.append("Linux")
    if diag["is_headless"]:
        env_flags.append("Headless")

    flags_str = ", ".join(env_flags) if env_flags else "Standard"

    lines = [
        "=== Vision Gesture Control: System Diagnostics ===",
        f"OS / System     : {diag['system']} {diag['release']} ({diag['machine']})",
        f"Python Version  : {diag['python_version']} ({diag['python_executable']})",
        f"Environment     : {flags_str}",
        f"CPUs Available  : {diag['cpu_count']}",
        f"Terminal Size   : {diag['terminal_size']['columns']}x{diag['terminal_size']['lines']}",
        f"Stdout Encoding : {diag['encoding']['stdout']}",
        "==================================================",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Browser Opening & Command Execution
# ---------------------------------------------------------------------------

def open_url(url: str, new_tab: bool = True, background: bool = False) -> bool:
    """Opens a URL in the user's default browser across diverse platforms.

    Supports Linux (xdg-open), Termux Android (termux-open-url), macOS (open),
    Windows (start / startfile), and standard Python webbrowser fallback.

    Args:
        url: The web URL or local file URI to open.
        new_tab: Whether to attempt opening in a new tab.
        background: Whether to attempt background opening (platform dependent).

    Returns:
        True if the browser command was dispatched successfully, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    # 1. Termux Android
    if is_termux():
        for cmd in ("termux-open-url", "termux-open"):
            if shutil.which(cmd):
                try:
                    res = subprocess.run([cmd, url], capture_output=True, timeout=5)
                    if res.returncode == 0:
                        return True
                except Exception:
                    pass

    # 2. Android am start fallback
    if is_android() and shutil.which("am"):
        try:
            res = subprocess.run(
                ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                capture_output=True,
                timeout=5,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. WSL wslview
    if is_wsl() and shutil.which("wslview"):
        try:
            res = subprocess.run(["wslview", url], capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 4. macOS open
    if is_macos() and shutil.which("open"):
        try:
            cmd_args = ["open"]
            if background:
                cmd_args.append("-g")
            cmd_args.append(url)
            res = subprocess.run(cmd_args, capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 5. Linux xdg-open
    if is_linux() and shutil.which("xdg-open"):
        try:
            res = subprocess.run(["xdg-open", url], capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 6. Windows startfile / cmd.exe start
    if is_windows():
        if hasattr(os, "startfile"):
            try:
                os.startfile(url)  # type: ignore[attr-defined]
                return True
            except Exception:
                pass
        try:
            res = subprocess.run(["cmd.exe", "/c", "start", "", url], capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 7. Standard Library webbrowser fallback
    try:
        new_mode = 2 if new_tab else 0
        return bool(webbrowser.open(url, new=new_mode, autoraise=not background))
    except Exception:
        return False
