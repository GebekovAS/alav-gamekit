"""alav - tiny game library for handheld consoles running ALAV Store. The same game runs in a PC window.

Python 3.11 standard library + SDL2 through ctypes.
Writing a game? Do not read this file: AGENTS.md has the rules and the whole API on one page.

    import alav as g

    def update(dt): ...
    def draw(): ...
    g.run(update, draw, "My Game")
"""
import array
import ctypes as C
import json
import math
import os
import random
import re
import errno
import ssl
import threading
import select
import socket
import sys
import time

W, H = 600, 440  # the logical screen: every game draws in these coordinates; SDL scales it to the real screen
GAME_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DEVICE = os.path.isdir("/storage/.config/emulationstation")
CHECK = int(os.environ.get("ALAV_CHECK", "0"))  # >0: headless self-test for that many frames
BOT = CHECK or bool(os.environ.get("ALAV_BOT"))  # random buttons instead of the pad


def _ipv4(s):
    parts = s.split(".")
    return len(parts) == 4 and all(p.isascii() and p.isdigit() and len(p) <= 3 and int(p) < 256 for p in parts)


_ROOM_ID = re.compile(r"[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{8}")
_JOIN_ENV = os.environ.get("ALAV_JOIN", "")
_JOIN = _JOIN_ENV if (_ipv4(_JOIN_ENV) or _JOIN_ENV.startswith("relay:")) else None
NET = "internet" if os.environ.get("ALAV_NET") == "internet" or (_JOIN or "").startswith("relay:") else "lan"
ROLE = os.environ.get("ALAV_ROLE") or ("join" if _JOIN else next((a for a in sys.argv[1:] if a in ("host", "join")), None))

WHITE, BLACK, GRAY = (255, 255, 255), (0, 0, 0), (128, 128, 128)
RED, GREEN, BLUE, YELLOW = (230, 60, 60), (70, 200, 90), (70, 130, 255), (250, 210, 60)

# Built-in pad as numbered on the R36T, the reference device (SDL joystick "play_joystick"), then the PC keyboard (SDL scancodes).
BUTTONS = {"B": 0, "A": 1, "X": 2, "Y": 3, "L1": 4, "R1": 5, "L2": 6, "R2": 7,
           "SELECT": 8, "START": 9, "UP": 14, "DOWN": 15, "LEFT": 16, "RIGHT": 17}
KEYS = {"UP": 82, "DOWN": 81, "LEFT": 80, "RIGHT": 79, "A": 27, "B": 29, "X": 22, "Y": 4,
        "L1": 20, "R1": 26, "L2": 30, "R2": 31, "START": 40, "SELECT": 42}

if CHECK:
    # the console's SDL has no "dummy" driver, only KMSDRM and offscreen
    os.environ.setdefault("SDL_VIDEODRIVER", "offscreen" if DEVICE else "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _lib(name):
    try:
        return C.CDLL("lib%s-2.0.so.0" % name)  # the console
    except OSError:
        pass
    folder = os.environ.get("ALAV_SDL_DIR")  # set by tool.py, which downloads SDL2 when it is missing
    if not (folder and os.path.isdir(folder)):
        try:
            import sdl2dll
        except ImportError:
            sys.exit("SDL2 not found. Start the game through the tool, it downloads SDL2 itself:  "
                     "python tool.py run <slug>")
        folder = sdl2dll.get_dllpath()
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(folder)
    for f in os.listdir(folder):
        if f.lower().split(".")[0].split("-")[0] in (name.lower(), "lib" + name.lower()):
            return C.CDLL(os.path.join(folder, f))
    sys.exit("no %s library in %s" % (name, folder))


class _Rect(C.Structure):
    _fields_ = [("x", C.c_int), ("y", C.c_int), ("w", C.c_int), ("h", C.c_int)]


class _Color(C.Structure):
    _fields_ = [("r", C.c_uint8), ("g", C.c_uint8), ("b", C.c_uint8), ("a", C.c_uint8)]


class _Surface(C.Structure):
    _fields_ = [("flags", C.c_uint32), ("format", C.c_void_p), ("w", C.c_int), ("h", C.c_int)]


_sdl, _img, _ttf = _lib("SDL2"), _lib("SDL2_image"), _lib("SDL2_ttf")
_P, _I, _U32 = C.c_void_p, C.c_int, C.c_uint32
_SURF = C.POINTER(_Surface)
_RECT = C.POINTER(_Rect)


def _fn(lib, name, res, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = res, list(args)
    return f


_Init = _fn(_sdl, "SDL_Init", _I, _U32)
_InitSub = _fn(_sdl, "SDL_InitSubSystem", _I, _U32)
_Quit = _fn(_sdl, "SDL_Quit", None)
_GetError = _fn(_sdl, "SDL_GetError", C.c_char_p)
_ShowCursor = _fn(_sdl, "SDL_ShowCursor", _I, _I)
_CreateWindow = _fn(_sdl, "SDL_CreateWindow", _P, C.c_char_p, _I, _I, _I, _I, _U32)
_CreateRenderer = _fn(_sdl, "SDL_CreateRenderer", _P, _P, _I, _U32)
_LogicalSize = _fn(_sdl, "SDL_RenderSetLogicalSize", _I, _P, _I, _I)
_BlendMode = _fn(_sdl, "SDL_SetRenderDrawBlendMode", _I, _P, _I)
_DrawColor = _fn(_sdl, "SDL_SetRenderDrawColor", _I, _P, C.c_uint8, C.c_uint8, C.c_uint8, C.c_uint8)
_Clear = _fn(_sdl, "SDL_RenderClear", _I, _P)
_FillRect = _fn(_sdl, "SDL_RenderFillRect", _I, _P, _RECT)
_DrawRect = _fn(_sdl, "SDL_RenderDrawRect", _I, _P, _RECT)
_DrawLine = _fn(_sdl, "SDL_RenderDrawLine", _I, _P, _I, _I, _I, _I)
_CopyEx = _fn(_sdl, "SDL_RenderCopyEx", _I, _P, _P, _RECT, _RECT, C.c_double, _P, _I)
_Present = _fn(_sdl, "SDL_RenderPresent", None, _P)
_ReadPixels = _fn(_sdl, "SDL_RenderReadPixels", _I, _P, _P, _U32, _P, _I)
_OutputSize = _fn(_sdl, "SDL_GetRendererOutputSize", _I, _P, C.POINTER(C.c_int), C.POINTER(C.c_int))
_TexFromSurf = _fn(_sdl, "SDL_CreateTextureFromSurface", _P, _P, _SURF)
_DestroyTexture = _fn(_sdl, "SDL_DestroyTexture", None, _P)
_FreeSurface = _fn(_sdl, "SDL_FreeSurface", None, _SURF)
_SurfFrom = _fn(_sdl, "SDL_CreateRGBSurfaceWithFormatFrom", _SURF, _P, _I, _I, _I, _I, _U32)
_PollEvent = _fn(_sdl, "SDL_PollEvent", _I, _P)
_NumJoysticks = _fn(_sdl, "SDL_NumJoysticks", _I)
_JoyOpen = _fn(_sdl, "SDL_JoystickOpen", _P, _I)
_JoyButton = _fn(_sdl, "SDL_JoystickGetButton", C.c_uint8, _P, _I)
_JoyAxis = _fn(_sdl, "SDL_JoystickGetAxis", C.c_int16, _P, _I)
_KeyState = _fn(_sdl, "SDL_GetKeyboardState", C.POINTER(C.c_uint8), _P)
_RWFromFile = _fn(_sdl, "SDL_RWFromFile", _P, C.c_char_p, C.c_char_p)
_IMG_Load = _fn(_img, "IMG_Load", _SURF, C.c_char_p)
_IMG_SavePNG = _fn(_img, "IMG_SavePNG", _I, _SURF, C.c_char_p)
_TTF_Init = _fn(_ttf, "TTF_Init", _I)
_TTF_OpenFont = _fn(_ttf, "TTF_OpenFont", _P, C.c_char_p, _I)
_TTF_Render = _fn(_ttf, "TTF_RenderUTF8_Blended", _SURF, _P, C.c_char_p, _Color)

_RGBA32 = 0x16762004  # SDL_PIXELFORMAT_RGBA32 on little-endian CPUs (PC and the console)
_RATE = 22050

_ren = _joy = _mix = None
_running = False
_fonts, _texts, _images, _sounds = {}, {}, {}, {}
_now = dict.fromkeys(BUTTONS, False)
_before = dict(_now)
_draws = 0
_said = []  # check mode: the text drawn in the current frame, for the text view of screenshots
_net_peak = 0
_bot = random.Random(int(os.environ.get("ALAV_SEED", "1")))  # check-mode button masher


def _init(title):
    global _ren, _joy, _mix
    if _ren:
        return
    if _Init(0x20 | 0x200) != 0:  # video + joystick
        sys.exit("SDL_Init: " + _GetError().decode())
    _TTF_Init()
    if DEVICE:
        win = _CreateWindow(title.encode(), 0, 0, 0, 0, 0x1001)  # fullscreen desktop
    else:
        win = _CreateWindow(title.encode(), 0x2FFF0000, 0x2FFF0000, W if CHECK else W * 2,
                            H if CHECK else H * 2, 0x8 if CHECK else 0x20)  # hidden / resizable
    _ren = (None if CHECK else _CreateRenderer(win, -1, 0x2 | 0x4)) or _CreateRenderer(win, -1, 0x1)
    if not _ren:
        sys.exit("SDL_CreateRenderer: " + _GetError().decode())
    _LogicalSize(_ren, W, H)
    _BlendMode(_ren, 1)
    _ShowCursor(0)
    if _NumJoysticks() > 0:
        _joy = _JoyOpen(0)
    try:  # sound must never stop a game from starting
        mix = _lib("SDL2_mixer")
        if _InitSub(0x10) == 0 and _fn(mix, "Mix_OpenAudio", _I, _I, C.c_uint16, _I, _I)(_RATE, 0x8010, 1, 512) == 0:
            _fn(mix, "Mix_LoadWAV_RW", _P, _P, _I)
            _fn(mix, "Mix_QuickLoad_RAW", _P, C.c_char_p, _U32)
            _fn(mix, "Mix_PlayChannelTimed", _I, _I, _P, _I, _I)
            _fn(mix, "Mix_LoadMUS", _P, C.c_char_p)
            _fn(mix, "Mix_PlayMusic", _I, _P, _I)
            _mix = mix
    except (OSError, AttributeError, SystemExit):
        pass


# ---------------------------------------------------------------- drawing

def clear(color=BLACK):
    """Fill the whole screen. Call it first in draw()."""
    global _draws
    _draws += 1
    _DrawColor(_ren, color[0], color[1], color[2], 255)
    _Clear(_ren)


def rect(x, y, w, h, color, alpha=255, fill=True):
    """Rectangle with its top-left corner at (x, y). alpha 0..255. fill=False draws the outline."""
    global _draws
    _draws += 1
    _DrawColor(_ren, color[0], color[1], color[2], alpha)
    (_FillRect if fill else _DrawRect)(_ren, C.byref(_Rect(int(x), int(y), int(w), int(h))))


def line(x1, y1, x2, y2, color):
    global _draws
    _draws += 1
    _DrawColor(_ren, color[0], color[1], color[2], 255)
    _DrawLine(_ren, int(x1), int(y1), int(x2), int(y2))


def circle(x, y, r, color):
    """Filled circle with its centre at (x, y). Costs 2*r draw calls: keep r small."""
    global _draws
    x, y, r = int(x), int(y), int(r)
    _draws += 2 * r + 1
    _DrawColor(_ren, color[0], color[1], color[2], 255)
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(r * r - dy * dy))
        _DrawLine(_ren, x - dx, y + dy, x + dx, y + dy)


def text(s, x, y, color=WHITE, size=20, align="left"):
    """Draw text. align: "left", "center" or "right" relative to x. Returns the width in pixels."""
    global _draws
    s = str(s)
    if not s:
        return 0
    key = (s, size, color)
    item = _texts.get(key)
    if item is None:
        if len(_texts) > 200:  # text that changes every frame must not leak textures
            for tex, _, _ in _texts.values():
                _DestroyTexture(tex)
            _texts.clear()
        font = _fonts.get(size)
        if font is None:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font.ttf")
            font = _fonts[size] = _TTF_OpenFont(path.encode(), size)
            if not font:
                sys.exit("cannot open " + path)
        surf = _TTF_Render(font, s.encode(), _Color(color[0], color[1], color[2], 255))
        item = _texts[key] = (_TexFromSurf(_ren, surf), surf.contents.w, surf.contents.h)
        _FreeSurface(surf)
    tex, tw, th = item
    if align == "center":
        x -= tw / 2
    elif align == "right":
        x -= tw
    _draws += 1
    if CHECK:
        _said.append((s, int(x), int(y), tw, th))
    _CopyEx(_ren, tex, None, C.byref(_Rect(int(x), int(y), tw, th)), 0, None, 0)
    return tw


class Sprite:
    """A picture ready to draw. Make one with sprite() or image(); it has .w and .h in pixels."""

    def __init__(self, surf):
        self.w, self.h = surf.contents.w, surf.contents.h
        self.tex = _TexFromSurf(_ren, surf)
        _FreeSurface(surf)


def sprite(rows, palette):
    """Pixel art from text. Call it once (not every frame), after run() has started or at import.

    rows: list of equal-length strings, one character per pixel; "." and " " are transparent.
    palette: {"character": (r, g, b)}.
    """
    _init("ALAV game")
    w, h = len(rows[0]), len(rows)
    data = bytearray()
    for row in rows:
        if len(row) != w:
            raise ValueError("sprite rows must all have the same length: %r" % row)
        for ch in row:
            data += bytes(palette[ch]) + b"\xff" if ch not in ". " else b"\0\0\0\0"
    buf = (C.c_char * len(data)).from_buffer(data)
    return Sprite(_SurfFrom(buf, w, h, 32, w * 4, _RGBA32))


def image(name):
    """Load a PNG from the game's assets/ folder (cached). Returns a Sprite."""
    _init("ALAV game")
    if name not in _images:
        path = os.path.join(GAME_DIR, "assets", name)
        surf = _IMG_Load(path.encode())
        if not surf:
            raise FileNotFoundError("cannot load image " + path)
        _images[name] = Sprite(surf)
    return _images[name]


def draw(spr, x, y, scale=1, flip=False, angle=0, src=None):
    """Draw a Sprite with its top-left corner at (x, y).

    scale: size multiplier. flip: mirror left-right. angle: degrees clockwise.
    src: (x, y, w, h) part of the picture, for sprite sheets.
    """
    global _draws
    _draws += 1
    w, h = (src[2], src[3]) if src else (spr.w, spr.h)
    part = C.byref(_Rect(*src)) if src else None
    _CopyEx(_ren, spr.tex, part, C.byref(_Rect(int(x), int(y), int(w * scale), int(h * scale))),
            angle, None, 1 if flip else 0)


# ---------------------------------------------------------------- input

def down(button):
    """True while the button is held. Names: UP DOWN LEFT RIGHT A B X Y L1 R1 L2 R2 START SELECT."""
    return _now[button]


def pressed(button):
    """True only on the frame the button goes down."""
    return _now[button] and not _before[button]


def _read_input(frame):
    global _before
    _before = dict(_now)
    if BOT:  # random but repeatable button mashing
        if frame % 8 == 0:
            for b in _now:
                chance = 0 if b == "SELECT" and not CHECK else 0.05 if b == "SELECT" else 0.3 if b in ("UP", "DOWN", "LEFT", "RIGHT") else 0.2
                _now[b] = _bot.random() < chance
        return
    keys = _KeyState(None)
    for b in _now:
        _now[b] = bool(keys[KEYS[b]]) or bool(_joy and _JoyButton(_joy, BUTTONS[b]))
    if _joy:  # the left stick works as a d-pad too
        ax, ay = _JoyAxis(_joy, 0), _JoyAxis(_joy, 1)
        _now["LEFT"] |= ax < -16000
        _now["RIGHT"] |= ax > 16000
        _now["UP"] |= ay < -16000
        _now["DOWN"] |= ay > 16000


# ---------------------------------------------------------------- sound

def tone(freq, ms=100, freq2=None, volume=0.4, wave="square"):
    """Play a synthesized beep. freq2 slides the pitch (jump: 300 -> 600). wave: square, sine, noise."""
    if not _mix:
        return
    key = (freq, ms, freq2, volume, wave)
    item = _sounds.get(key)
    if item is None:
        n = int(_RATE * ms / 1000)
        rng = random.Random(1)
        buf = array.array("h")
        phase = 0.0
        for i in range(n):
            phase += (freq + ((freq2 or freq) - freq) * i / n) / _RATE
            if wave == "noise":
                v = rng.uniform(-1, 1)
            elif wave == "sine":
                v = math.sin(phase * 6.2832)
            else:
                v = 1 if phase % 1 < 0.5 else -1
            buf.append(int(v * volume * 32767 * min(1, (n - i) / (n * 0.3 + 1))))
        raw = buf.tobytes()
        item = _sounds[key] = (_mix.Mix_QuickLoad_RAW(raw, len(raw)), raw)  # keep raw alive
    _mix.Mix_PlayChannelTimed(-1, item[0], 0, -1)


def sound(name):
    """Play a WAV or OGG file from the game's assets/ folder."""
    if not _mix:
        return
    if name not in _sounds:
        path = os.path.join(GAME_DIR, "assets", name)
        chunk = _mix.Mix_LoadWAV_RW(_RWFromFile(path.encode(), b"rb"), 1)
        if not chunk:
            raise FileNotFoundError("cannot load sound " + path)
        _sounds[name] = (chunk, None)
    _mix.Mix_PlayChannelTimed(-1, _sounds[name][0], 0, -1)


def music(name):
    """Loop an OGG/MP3/WAV file from assets/ as background music."""
    if _mix:
        track = _mix.Mix_LoadMUS(os.path.join(GAME_DIR, "assets", name).encode())
        if not track:
            raise FileNotFoundError("cannot load music " + name)
        _mix.Mix_PlayMusic(track, -1)


# ---------------------------------------------------------------- helpers

def hit(a, b):
    """True when rectangles a and b overlap. Each is (x, y, w, h)."""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def save(data):
    """Store a dict (high score, progress) in save.json next to the game."""
    path = os.path.join(GAME_DIR, "save.json")
    if CHECK:
        return  # the self-test's random play must not overwrite real progress
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(path + ".tmp", path)


def load(default=None):
    """Read what save() stored; returns default (or {}) when nothing was saved yet."""
    try:
        with open(os.path.join(GAME_DIR, "save.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def quit():
    """Leave the game after this frame."""
    global _running
    _running = False


# ---------------------------------------------------------------- network

NET_PORT = 36036
_hosting = None  # the Net made by host(): run() answers the store lobby for it every frame
_SLUG = "abcdefghijklmnopqrstuvwxyz0123456789"  # a store slug is [a-z0-9][a-z0-9_-]{0,39}


def _lobby_reply(slug, title, players, max_players=None):
    """Answer to the store lobby probe b"ALAV?*": at most 250 bytes, or None when the folder is not a store slug."""
    if not (0 < len(slug) <= 40 and slug[0] in _SLUG and all(ch in _SLUG + "_-" for ch in slug)):
        return None
    title = title[:40]
    while True:
        info = {"slug": slug, "name": title, "players": players}
        if max_players:
            info["max"] = max_players
        data = b"ALAV!*" + json.dumps(info, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "replace")
        if len(data) <= 250:
            return data
        title = title[:-1]


# DNS has no non-blocking standard-library API. Only resolution uses a daemon
# worker; all socket I/O, TLS and protocol state stay on the game thread.
_relay_dns = {}
_relay_tls = None


def _relay_address():
    value = os.environ.get("ALAV_RELAY", "https://alav.online/play-relay")
    tls = value.startswith("https://")
    if tls:
        if not value.endswith("/play-relay"):
            raise ValueError("invalid relay path")
        value = value[8:-11]
        if ":" not in value:
            value += ":443"
    if not re.fullmatch(r"[a-zA-Z0-9.-]{1,253}:[0-9]{1,5}", value):
        raise ValueError("invalid relay address")
    host, port = value.rsplit(":", 1)
    if not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", part) for part in host.split(".")):
        raise ValueError("invalid relay hostname")
    if not 1 <= int(port) <= 65535:
        raise ValueError("invalid relay port")
    return host, int(port), tls


def _resolve_relay(key, result):
    try:
        result.append(socket.getaddrinfo(*key, type=socket.SOCK_STREAM)[0])
    except OSError:
        result.append(None)


class _RelayLink:
    """One bounded, non-blocking TCP/TLS/Upgrade/relay handshake."""
    def __init__(self, address, keyword, body):
        global _relay_tls
        self.address = address
        self.request = (keyword + " " + json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        if len(self.request) > 512:
            raise ValueError("oversize relay request")
        self.sock = None
        self.stage = "dns"
        self.rx = self.tx = b""
        self.deadline = time.monotonic() + 8
        key = address[:2]
        if key not in _relay_dns:
            result = _relay_dns[key] = []
            try:
                socket.inet_pton(socket.AF_INET, key[0])
                result.append((socket.AF_INET, socket.SOCK_STREAM, 0, "", key))
            except OSError:
                threading.Thread(target=_resolve_relay, args=(key, result), daemon=True).start()
        self.resolved = _relay_dns[key]
        if address[2] and _relay_tls is None:
            _relay_tls = ssl.create_default_context()

    def close(self):
        if self.sock:
            self.sock.close()
        self.stage = "closed"

    def _request(self):
        self.stage, self.tx = "reply", self.request

    def poll(self):
        if self.stage not in ("control", "ready") and time.monotonic() > self.deadline:
            raise OSError("relay handshake timeout")
        if self.stage == "dns":
            if not self.resolved:
                return []
            if self.resolved[0] is None:
                raise OSError("relay DNS failed")
            family, kind, proto, _, addr = self.resolved[0]
            self.sock = socket.socket(family, kind, proto)
            self.sock.setblocking(False)
            error = self.sock.connect_ex(addr)
            if error not in (0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, 10035):
                raise OSError(error, "relay connect")
            self.stage = "connect"
            self.connect_deadline = time.monotonic() + .3
        if self.stage == "connect":
            if time.monotonic() > self.connect_deadline:
                raise OSError("relay connect timeout")
            _, writable, errors = select.select([], [self.sock], [self.sock], 0)
            if not writable and not errors:
                return []
            if self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                raise OSError("relay connect failed")
            if self.address[2]:
                self.sock = _relay_tls.wrap_socket(self.sock, server_hostname=self.address[0], do_handshake_on_connect=False)
                self.stage = "tls"
            else:
                self._request()
        try:
            if self.stage == "tls":
                self.sock.do_handshake()
                host, port, _ = self.address
                authority = host if port == 443 else "%s:%d" % (host, port)
                self.tx = ("GET /play-relay HTTP/1.1\r\nHost: " + authority +
                           "\r\nUpgrade: alav-relay\r\nConnection: Upgrade\r\n\r\n").encode("ascii")
                self.stage = "upgrade"
            if self.tx:
                count = self.sock.send(self.tx)
                self.tx = self.tx[count:]
                if self.tx:
                    return []
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OSError("relay closed")
            self.rx += chunk
        except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
            return []
        if self.stage == "upgrade":
            if b"\r\n\r\n" not in self.rx:
                if len(self.rx) > 4096:
                    raise ValueError("oversize upgrade")
                return []
            header, self.rx = self.rx.split(b"\r\n\r\n", 1)
            rows = header.lower().split(b"\r\n")
            if (len(header) > 4096 or rows[0].split()[:2] != [b"http/1.1", b"101"] or
                    b"upgrade: alav-relay" not in rows or b"connection: upgrade" not in rows):
                raise ValueError("invalid upgrade")
            self._request()
            return []
        lines = []
        while b"\n" in self.rx:
            line, self.rx = self.rx.split(b"\n", 1)
            if len(line) > 511:
                raise ValueError("oversize relay line")
            keyword, _, payload = line.decode("utf-8").partition(" ")
            body = json.loads(payload) if payload else {}
            if not isinstance(body, dict):
                raise ValueError("invalid relay body")
            lines.append((keyword, body))
            # OK switches framing to the game's JSON stream. Preserve all bytes.
            if keyword == "OK":
                break
        if len(self.rx) > (262144 if lines and lines[-1][0] == "OK" else 511):
            raise ValueError("oversize relay buffer")
        return lines


class Net:
    """LAN or internet link between consoles. Make one with host() or join(); see AGENTS.md "Network games"."""

    def __init__(self, name, is_host, ip=None, max_players=None):
        global _hosting, NET
        if not name or name.startswith("*"):  # b"ALAV?*" is the store lobby probe
            raise ValueError("network game name must not be empty or start with '*'")
        if max_players is not None and not (type(max_players) is int and 2 <= max_players <= 99):
            raise ValueError("max_players must be a whole number from 2 to 99, or None for no limit")
        self.name, self.is_host, self.ip, self.max = name.encode(), is_host, ip, max_players
        self.peers = {}  # id -> [socket, unparsed bytes]; a client sees the host as id 0
        self._next_id, self._retry = 1, 0.0
        self._relay = None
        self._pending = []
        self._session = None
        self._closed = False
        target = ip or os.environ.get("ALAV_JOIN", "")
        self._internet = (os.environ.get("ALAV_NET") == "internet" if is_host else target.startswith("relay:"))
        self._relay_id = target[6:] if not is_host and self._internet else None
        self._address = None
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if is_host:
            self.srv = socket.socket()
            self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.srv.bind(("", NET_PORT))
            self.srv.listen(8)
            self.udp.bind(("", NET_PORT))
            self.slug = self.title = os.path.basename(GAME_DIR)  # what the store lobby is told
            try:
                with open(os.path.join(GAME_DIR, "game.json"), encoding="utf-8") as f:
                    self.title = str(json.load(f)["title"])
            except (OSError, ValueError, KeyError, TypeError):
                pass
            _hosting = self
        if self._internet:
            try:
                self._address = _relay_address()
                if is_host:
                    body = dict(slug=self.slug, name=self.title[:40], max=max_players or 8)
                    room = os.environ.get("ALAV_ROOM", "")
                    if _ROOM_ID.fullmatch(room):
                        body["id"] = room
                    if os.environ.get("ALAV_PRIVATE") == "1":
                        body["private"] = True
                    self._relay = _RelayLink(self._address, "HOST", body)
            except (OSError, ValueError):
                self._relay_failed()
        NET = "internet" if self._internet else "lan"

    @property
    def connected(self):
        """True while at least one other player is linked."""
        return bool(self.peers)

    def _add(self, sock, pid):
        global _net_peak
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setblocking(False)
        self.peers[pid] = [sock, b"", b""]
        _net_peak = max(_net_peak, len(self.peers))

    def _readable(self, sock):
        return bool(select.select([sock], [], [], 0)[0])

    def _drop(self, pid):
        peer = self.peers.pop(pid, None)
        if peer:
            peer[0].close()

    def close(self):
        global _hosting
        if self._closed:
            return
        self._closed = True
        for pid in list(self.peers):
            self._drop(pid)
        if self._relay:
            self._relay.close()
        for link in self._pending:
            link.close()
        self._pending.clear()
        self.udp.close()
        if self.is_host:
            self.srv.close()
        if _hosting is self:
            _hosting = None

    def _relay_failed(self):
        global NET
        if self._relay:
            self._relay.close()
            self._relay = None
        if self.is_host:
            for link in self._pending:
                link.close()
            self._pending.clear()
            self._internet = False
            NET = "lan"
            print("ALAV: relay unavailable; LAN hosting continues", file=sys.stderr)

    def _relay_find(self):
        if not self._internet:
            return
        if not self.is_host and not self.peers and not self._relay and time.monotonic() >= self._retry:
            self._retry = time.monotonic() + 3
            if self._address and _ROOM_ID.fullmatch(self._relay_id or ""):
                self._relay = _RelayLink(self._address, "JOIN", {"id": self._relay_id})
        link = self._relay
        if link:
            try:
                for keyword, body in link.poll():
                    if self.is_host and keyword == "SESSION" and not self._session:
                        sid = body.get("id")
                        if not isinstance(sid, str) or not _ROOM_ID.fullmatch(sid):
                            raise ValueError("invalid session")
                        self._session, link.stage = sid, "control"
                    elif self.is_host and self._session and keyword == "PING" and not body:
                        link.tx += b"PONG\n"
                    elif self.is_host and self._session and keyword == "CONN":
                        pair = body.get("pair")
                        if not isinstance(pair, str) or not re.fullmatch(r"[a-f0-9]{32}", pair):
                            raise ValueError("invalid pair")
                        # LAN players share the same capacity; leave an excess relay
                        # guest unpaired rather than disconnecting the entire room.
                        if len(self._pending) + len(self.peers) >= (self.max or 8) - 1:
                            continue
                        if any(item.pair == pair for item in self._pending):
                            raise ValueError("duplicate pair")
                        data = _RelayLink(self._address, "DATA", dict(id=self._session, pair=pair))
                        data.pair = pair
                        self._pending.append(data)
                    elif not self.is_host and keyword == "OK" and not body:
                        self._add(link.sock, 0)
                        self.peers[0][1] = link.rx
                        self._relay = None
                    else:
                        raise ValueError("relay refused or invalid response")
            except (OSError, ValueError, RecursionError):
                self._relay_failed()
        for data in self._pending[:]:
            try:
                for keyword, body in data.poll():
                    if keyword != "OK" or body:
                        raise ValueError("invalid data response")
                    self._add(data.sock, self._next_id)
                    self.peers[self._next_id][1] = data.rx
                    self._next_id += 1
                    self._pending.remove(data)
            except (OSError, ValueError, RecursionError):
                data.close()
                self._pending.remove(data)

    def _find(self):
        if self._closed:
            return
        self._relay_find()
        if self.is_host:
            while self._readable(self.srv):
                sock = self.srv.accept()[0]
                if self.max and len(self.peers) >= self.max - 1:  # the match is full
                    sock.close()
                    continue
                self._add(sock, self._next_id)
                self._next_id += 1
            while self._readable(self.udp):
                try:  # datagrams come from anyone on the network: a bad one must not stop the game
                    data, addr = self.udp.recvfrom(256)
                    if data == b"ALAV?*":  # the store lobby asks who is hosting
                        reply = _lobby_reply(self.slug, self.title, len(self.peers) + 1, self.max)
                        if reply:
                            self.udp.sendto(reply, addr)
                    elif data == b"ALAV?" + self.name:
                        self.udp.sendto(b"ALAV!" + self.name, addr)
                except OSError:
                    pass
        elif not self._internet and not self.peers and time.monotonic() >= self._retry:
            self._retry = time.monotonic() + 0.5
            try:
                if self.ip:
                    # shortcut: blocks up to 0.3 s per try when the host is unreachable
                    self._add(socket.create_connection((self.ip, NET_PORT), timeout=0.3), 0)
                    return
                targets = ["255.255.255.255", "127.0.0.1"]
                try:  # a PC with several network cards sends the plain broadcast to the wrong one
                    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    probe.connect(("192.0.2.1", 9))
                    targets.append(probe.getsockname()[0].rsplit(".", 1)[0] + ".255")  # shortcut: assumes a /24 network
                    probe.close()
                except OSError:
                    pass
                for target in targets:
                    try:
                        self.udp.sendto(b"ALAV?" + self.name, (target, NET_PORT))
                    except OSError:
                        pass
                while self._readable(self.udp):
                    data, addr = self.udp.recvfrom(256)
                    if data == b"ALAV!" + self.name:
                        self._add(socket.create_connection((addr[0], NET_PORT), timeout=0.3), 0)
                        return
            except OSError:
                pass

    def recv(self):
        """Call once per frame. Returns a list of (player_id, message) received since last time."""
        self._find()
        out = []
        for pid, peer in list(self.peers.items()):
            try:
                self._flush(peer)
            except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
                pass
            except (OSError, ValueError):
                self._drop(pid)
                continue
            try:
                # Bound work per peer per frame, including malicious streams.
                for _ in range(4):
                    if not self._readable(peer[0]) and not getattr(peer[0], "pending", lambda: 0)():
                        break
                    data = peer[0].recv(65536)
                    if not data:
                        raise OSError("closed")
                    peer[1] += data
                    if len(peer[1]) > 262144:
                        raise ValueError("oversize game buffer")
            except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
                pass
            except (OSError, ValueError):
                self._drop(pid)
                continue
            *lines, peer[1] = peer[1].split(b"\n")
            for ln in lines:
                try:
                    out.append((pid, json.loads(ln)))
                except (ValueError, RecursionError):
                    pass
        return out

    def _flush(self, peer):
        if len(peer[2]) > 262144:
            raise ValueError("slow peer")
        if peer[2]:
            count = peer[0].send(peer[2])
            peer[2] = peer[2][count:]

    def send(self, message, to=None):
        """Queue JSON for every linked player, or only player id `to`."""
        data = json.dumps(message, separators=(",", ":")).encode() + b"\n"
        for pid, peer in list(self.peers.items()):
            if to is None or to == pid:
                peer[2] += data
                try:
                    if len(peer[2]) > 262144:
                        raise ValueError("slow peer")
                    self._flush(peer)
                except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
                    pass
                except (OSError, ValueError):
                    self._drop(pid)


def host(name, max_players=None):
    """Start a network game others can join. name: any short id of your game, the same on both sides.

    max_players (you included): the store lobby shows the match as full and nobody above it gets in.
    """
    return Net(name, True, max_players=max_players)


def join(name, ip=None):
    """Find a host of the game `name` on the local network (or connect straight to ip).

    The store passes ALAV_JOIN=<host ip> or relay:<session id> and ROLE is "join".
    """
    return Net(name, False, ip or _JOIN)


# ---------------------------------------------------------------- main loop

def _screenshot(path):
    # the real screen may be larger than W x H (the picture is scaled up): read what is really there
    ow, oh = C.c_int(), C.c_int()
    _OutputSize(_ren, C.byref(ow), C.byref(oh))
    ow, oh = ow.value or W, oh.value or H
    buf = C.create_string_buffer(ow * oh * 4)
    _ReadPixels(_ren, C.byref(_Rect(0, 0, ow, oh)), _RGBA32, buf, ow * 4)
    surf = _SurfFrom(buf, ow, oh, 32, ow * 4, _RGBA32)
    _IMG_SavePNG(surf, path.encode())
    _FreeSurface(surf)
    raw = buf.raw
    if CHECK and (ow, oh) == (W, H):  # the same picture as text, for models that cannot look at images
        cells = [[raw[((r * 20 + 10) * W + c * 10 + 5) * 4:][:3] for c in range(W // 10)] for r in range(H // 20)]
        count = {}
        for row in cells:
            for px in row:
                count[px] = count.get(px, 0) + 1
        order = sorted(count, key=count.get, reverse=True)
        name = {px: ("." + "abcdefghijklmnopqrstuvwxyz")[i] if i < 27 else "#" for i, px in enumerate(order)}
        lines = ["The screen (%dx%d) as text: one character is 10x20 pixels, '.' is the background." % (W, H)]
        lines += ["".join(name[px] for px in row) for row in cells]
        lines.append("Colours: " + ", ".join("%s=(%d,%d,%d)" % ((name[px],) + tuple(px)) for px in order[:27]))
        lines.append("Text drawn in this frame (x, y = its top-left corner):")
        for s, x, y, tw, th in _said:
            inside = x >= 0 and y >= 0 and x + tw <= W and y + th <= H
            lines.append("  %r at x=%d y=%d, size %dx%d%s" % (s, x, y, tw, th, "" if inside else "   <-- PARTLY OFF SCREEN"))
        with open(path[:-4] + ".txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return len(set(raw[i:i + 3] for i in range(0, len(raw), 4 * 37)))


def run(update, draw, title="ALAV game"):
    """Run the game: every frame calls update(dt) (dt = seconds since the last frame), then draw().

    SELECT+START always quits, so a player can never get stuck in a game.
    """
    global _running, _draws
    _init(title)
    _running = True
    event = C.create_string_buffer(64)
    shots = os.environ.get("ALAV_SHOTS")
    shot = os.path.join(GAME_DIR, ".shot")
    frame, spent, most_draws, colors, times = 0, 0.0, 0, 0, []
    last = report = time.perf_counter()
    since = 0
    try:
        while _running:
            while _PollEvent(event):
                if C.c_uint32.from_buffer(event).value == 0x100:  # window closed
                    _running = False
            _read_input(frame)
            if _hosting:  # the store lobby must see a host whose game is paused and not calling recv()
                _hosting._find()
            if not CHECK and ((_now["SELECT"] and _now["START"]) or _KeyState(None)[41]):  # 41 = Esc
                break
            start = time.perf_counter()
            dt = 1 / 60 if CHECK else min(start - last, 0.05)  # a long hitch never teleports things
            last = start
            _draws = 0
            _said.clear()
            update(dt)
            draw()
            took = time.perf_counter() - start
            spent += took
            times.append(took)
            most_draws = max(most_draws, _draws)
            frame += 1
            since += 1
            if CHECK:
                if shots and frame in (CHECK // 10, CHECK // 2, CHECK):
                    colors = max(colors, _screenshot(os.path.join(shots, "frame%05d.png" % frame)))
                if frame >= CHECK:
                    break
                if os.environ.get("ALAV_PACE"):  # network checks need real time to pass
                    time.sleep(max(0, 1 / 60 - took))
            else:
                if DEVICE and frame % 30 == 0 and os.path.exists(shot):  # developer mode asks for a picture
                    os.remove(shot)
                    _screenshot(shot + ".tmp.png")
                    os.replace(shot + ".tmp.png", shot + ".png")
                _Present(_ren)
                if start - report >= 5:  # goes to the game log on the console
                    print("fps %.0f, work %.1f ms/frame, %d draw calls" %
                          (since / (start - report), spent / since * 1000, most_draws), flush=True)
                    report, since, spent, most_draws = start, 0, 0.0, 0
                    times.clear()
    finally:
        if CHECK:
            print("ALAV_CHECK " + json.dumps({
                # the median ignores one-off costs such as building a sound
                "frames": frame, "avg_ms": round(sorted(times)[len(times) // 2] * 1000, 3) if times else 0,
                "max_ms": round(max(times, default=0) * 1000, 3), "draws": most_draws, "colors": colors,
                "net_peers": _net_peak}), flush=True)
        _Quit()
