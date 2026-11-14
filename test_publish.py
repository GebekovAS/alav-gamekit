"""Test of `tool.py publish` against a local fake of the ALAV Store catalog. Run: python test_publish.py

The fake follows Docs/DEVELOPER_PUBLISHING.md of the server (sections 2-4 and the review of 3.7). Nothing is sent
to alav.online. The administrator's decisions are made by approve() and reject() below.
"""
import hashlib
import http.server
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import uuid
import zlib
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = "mk_1a2b3c4d_" + "k" * 43
GENERIC = "При обработке запроса возникла непредвиденная ошибка"
APPS, FILES, UPLOADS, LOG = {}, {}, {}, []   # LOG: (method, path, headers) of every request
FAIL = {}                                    # "METHOD path-suffix" -> detail: answer 400 once
PENDING = []                                 # non-empty: the key's developer account is not approved yet
NO_PACKAGE = ("Для выпуска в ALAV Store версии нужен пакет для консоли: артефакт linux/arm64 (или any) в формате zip. "
              "Добавьте его к черновику и повторите выпуск")
FROZEN = "Версия на проверке: изменить её нельзя. Отзовите версию с проверки или удалите её"


def error(detail, path):
    return 400, {"type": "", "title": "Ошибка приложения", "status": 400, "detail": detail, "instance": path}


def app_json(app, versions=False):
    published = [v for v in app["versions"] if v["status"] == 1]
    out = {"id": app["id"], "name": app["name"], "category": app["category"], "packageId": app["packageId"],
           "author": {"id": "5b0c", "username": "My Studio"}, "currentIconFileId": app["icon"],
           "screenshotFileIds": [], "versionsCount": len(app["versions"]),
           "latestVersion": published[-1] if published else None, "createdAt": "2026-11-14T12:00:00Z", "updatedAt": None}
    if versions:
        out["versions"] = app["versions"][::-1]  # newest first
    return out


def multipart(body, content_type):
    boundary = content_type.split("boundary=")[1].encode()
    fields = {}
    for part in body.split(b"--" + boundary)[1:-1]:
        head, data = part.split(b"\r\n\r\n", 1)
        fields[re.search(rb'name="([^"]+)"', head).group(1).decode()] = data[:-2]
    return fields


def route(method, path, query, body, headers):
    if headers.get("X-Api-Key") != KEY or headers.get("Authorization"):
        return 401, None
    for rule, detail in list(FAIL.items()):
        if rule == "%s %s" % (method, path.rsplit("/", 1)[-1]):
            del FAIL[rule]
            return error(detail, path)
    data = json.loads(body) if body and headers.get("Content-Type") == "application/json" else None
    if (method, path) == ("GET", "/api/v2/applications/mine"):
        page, size = int(query.get("page", ["1"])[0]), int(query.get("pageSize", ["20"])[0])
        apps = list(APPS.values())
        return 200, {"applications": [app_json(a, True) for a in apps[(page - 1) * size:page * size]],
                     "total": len(apps), "page": page, "pageSize": size}
    if (method, path) == ("POST", "/api/v2/applications"):
        if data.get("category") not in ("ALAV Store Игры", "ALAV Store Приложения"):
            return error("Недопустимая категория", path)
        if not re.fullmatch(r"ALAV\.[A-Za-z0-9][A-Za-z0-9_-]{0,39}", data.get("packageId") or ""):
            return error("Недопустимый packageId", path)
        if any(a["packageId"].lower() == data["packageId"].lower() for a in APPS.values()):
            return error("Пакет уже существует", path)
        app = {"id": str(uuid.uuid4()), "name": data["name"], "category": data["category"],
               "packageId": data["packageId"], "icon": None, "versions": []}  # iconFileId is ignored here
        APPS[app["id"]] = app
        return 201, dict(app_json(app), author=None)
    if (method, path) == ("POST", "/api/v1/Files/upload/init"):
        upload = dict(data, uploadId=str(uuid.uuid4()), chunks={})
        UPLOADS[upload["uploadId"]] = upload
        return 200, {k: upload[k] for k in ("uploadId", "fileName", "fileSize", "totalChunks", "chunkSize")}
    if (method, path) == ("POST", "/api/v1/Files/upload/chunk"):
        form = multipart(body, headers["Content-Type"])
        if set(form) != {"uploadId", "chunkIndex", "totalChunks", "fileName", "chunkSize", "isTemporary", "chunk"} \
                or int(form["chunkSize"]) != len(form["chunk"]) or form["isTemporary"] != b"false":
            return error("Некорректная часть файла", path)
        UPLOADS[form["uploadId"].decode()]["chunks"][int(form["chunkIndex"])] = form["chunk"]
        return 200, {"uploadId": form["uploadId"].decode(), "chunkIndex": int(form["chunkIndex"]),
                     "isComplete": False, "fileMetadata": None}
    if (method, path) == ("POST", "/api/v1/Files/upload/complete"):
        upload = UPLOADS.pop(data["uploadId"])
        content = b"".join(upload["chunks"][i] for i in range(upload["totalChunks"]))
        if len(content) != data["fileSize"] or data["isTemporary"] is not False:
            return error("Хранилище отклонило файл", path)
        file_id = str(uuid.uuid4())
        FILES[file_id] = content
        return 200, {"id": file_id, "fileName": data["fileName"], "contentType": data["contentType"],
                     "size": len(content), "created": "2026-11-14T12:00:00Z", "uploadedBy": None, "isTemporary": False}
    if PENDING:  # a developer who is not approved yet: every developer route answers 403 with an empty body
        return 403, None
    found = re.fullmatch(r"/api/v2/applications/([^/]+)(?:/versions(?:/([^/]+)(?:/(artifacts|publish))?)?)?", path)
    app = APPS.get(found.group(1)) if found else None
    if not app:
        return 401, None  # a key works only on the developer routes
    tail = path[len("/api/v2/applications/" + app["id"]):]
    ver = next((v for v in app["versions"] if v["id"] == found.group(2)), None)
    if (method, tail) == ("PUT", ""):
        app["name"] = data.get("name", app["name"])
        app["icon"] = data.get("iconFileId", app["icon"])
        return 200, app_json(app)
    if (method, tail) == ("POST", "/versions"):
        if not re.fullmatch(r"\d+\.\d+\.\d+", data.get("version") or "") or not data.get("description") \
                or len(data["description"]) > 500 or data.get("fileId") not in FILES or not data.get("fileName"):
            return 400, {"title": "One or more validation errors occurred.", "status": 400,
                         "errors": {"Version": ["The Version field is required."]}}
        if any(v["version"] == data["version"] for v in app["versions"]):
            return error(GENERIC, path)
        if data.get("publishImmediately"):  # a new version has no console package yet
            return error(NO_PACKAGE, path)
        ver = {"id": str(uuid.uuid4()), "applicationBaseId": app["id"], "version": data["version"],
               "description": data["description"], "longDescription": data.get("longDescription"), "iconFileId": None,
               "fileId": data["fileId"], "fileName": data["fileName"], "fileSize": data["fileSize"], "rating": 0,
               "downloadsCount": 0, "status": 0, "publishedAt": None,
               "deprecatedAt": None, "submittedAt": None, "rejectionReason": None,
               "createdAt": "2026-11-14T12:05:00Z", "updatedAt": None, "releaseNotes": None,
               "minimumOsVersion": None, "tags": data.get("tags", []), "channel": data.get("channel", "stable"),
               "isMandatory": False, "rolloutPercent": 100, "_artifacts": []}
        app["versions"].append(ver)
        return 201, ver
    if not ver:
        return error(GENERIC, path)
    if (method, found.group(3)) == ("POST", "artifacts"):
        if ver["status"] == 4:
            return error(FROZEN, path)
        content = FILES[data["fileId"]]
        artifact = {"id": str(uuid.uuid4()), "platform": data["platform"], "arch": data.get("arch", "any"),
                    "format": data.get("format", "zip"), "fileName": ver["fileName"], "fileSize": len(content),
                    "sha256": hashlib.sha256(content).hexdigest().upper(), "minimumOsVersion": None, "downloadsCount": 0,
                    "downloadPath": path + "/x/download", "_fileId": data["fileId"]}
        ver["_artifacts"].append(artifact)
        return 201, artifact
    if (method, found.group(3)) == ("PATCH", "publish"):
        if ver["status"] == 4:
            return 200, ver  # already in review: a no-op with the same answer
        if ver["status"] != 0:
            return error(GENERIC, path)
        if not any((a["platform"], a["format"]) == ("linux", "zip") and a["arch"] in ("arm64", "any")
                   for a in ver["_artifacts"]):
            return error(NO_PACKAGE, path)
        # A developer's release is held: nothing is deprecated or made public until the administrator approves.
        ver.update(status=4, submittedAt="2026-11-14T12:10:00Z", rejectionReason=None)
        return 200, ver
    if (method, found.group(3)) == ("DELETE", None):
        if ver["status"] == 1:
            return error(GENERIC, path)
        app["versions"].remove(ver)
        return 204, None
    return 401, None


def approve(ver):
    """The administrator approves a version in review: it is published, the previous one is deprecated."""
    app = APPS[ver["applicationBaseId"]]
    assert ver["status"] == 4
    for other in app["versions"]:
        if other["status"] == 1 and other["channel"] == ver["channel"]:
            other["status"] = 2
    ver.update(status=1, publishedAt="2026-11-14T13:00:00Z", submittedAt=None)


def reject(ver, reason):
    """The administrator rejects a version in review: a draft again, with the reason for its author."""
    assert ver["status"] == 4
    ver.update(status=0, submittedAt=None, rejectionReason=reason)


class Fake(http.server.BaseHTTPRequestHandler):
    def handle_one(self):
        url = urlparse(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        LOG.append((self.command, url.path, dict(self.headers)))
        status, answer = route(self.command, url.path, parse_qs(url.query), body, self.headers)
        data = json.dumps(answer).encode("utf-8") if answer is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = handle_one

    def log_message(self, *args):
        pass


def png(width, height):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\0" + b"\x40\x80\xc0" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def publish(game, *flags, key=KEY):
    """Run the command; return (exit code, output, requests it sent as 'METHOD path')."""
    del LOG[:]
    env = dict(os.environ, ALAV_STORE_URL=URL, PYTHONIOENCODING="utf-8")
    env.pop("ALAV_KEY", None)
    if key:
        env["ALAV_KEY"] = key
    run = subprocess.run([sys.executable, os.path.join(ROOT, "tool.py"), "publish", game, *flags], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    assert KEY not in run.stdout, "the key leaked into the output"
    assert "Traceback" not in run.stdout, run.stdout
    for _, _, headers in LOG:  # the key goes in X-Api-Key and nowhere else
        assert headers.get("X-Api-Key") == key and "Authorization" not in headers, headers
    return run.returncode, run.stdout, [re.sub(r"[0-9a-f-]{36}", "{id}", "%s %s" % r[:2]) for r in LOG]


def set_version(game, version, **more):
    with open(os.path.join(game, "game.json"), "w", encoding="utf-8") as f:
        json.dump(dict({"title": "Pub Test", "version": version}, **more), f, ensure_ascii=False)


UPLOAD = ["POST /api/v1/Files/upload/init", "POST /api/v1/Files/upload/chunk", "POST /api/v1/Files/upload/complete"]
VERSIONS = "/api/v2/applications/{id}/versions"


def main():
    global URL
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    URL = "http://127.0.0.1:%d" % server.server_port
    tmp = tempfile.mkdtemp()
    game = os.path.join(tmp, "pubtest")
    dist = os.path.join(ROOT, "dist")  # the kit used as its own workspace; with .workspace the zip lives elsewhere
    try:
        shutil.copytree(os.path.join(ROOT, "examples", "minimal"), game)
        set_version(game, "1.0.0", description="A test game", genre="Аркады")

        code, out, sent = publish(game)
        assert code != 0 and "icon.png" in out and not sent, out               # no icon: refused before any request
        with open(os.path.join(game, "icon.png"), "wb") as f:
            f.write(png(256, 256))
        code, out, sent = publish(game)
        assert code != 0 and "256x256" in out and not sent, out                # oversized icon
        with open(os.path.join(game, "icon.png"), "wb") as f:
            f.write(png(64, 64))

        code, out, sent = publish(game, key="")
        assert code != 0 and "https://alav.online/developers" in out and not sent, out   # missing key
        code, out, sent = publish(game, key="mk_wrong")
        assert code != 0 and "401" in out and not APPS, out                    # a wrong key creates nothing

        code, out, sent = publish(game)                                        # first publish: app + draft
        assert code == 0 and "draft" in out and "--release" in out, out
        assert sent == ["GET /api/v2/applications/mine", "POST /api/v2/applications", *UPLOAD,
                        "PUT /api/v2/applications/{id}", *UPLOAD, "POST " + VERSIONS,
                        "POST " + VERSIONS + "/{id}/artifacts"], sent
        app, = APPS.values()
        ver, = app["versions"]
        assert (app["packageId"], app["category"], app["name"]) == ("ALAV.pubtest", "ALAV Store Игры", "Pub Test")
        assert FILES[app["icon"]] == png(64, 64)
        assert ver["status"] == 0 and ver["tags"] == ["ALAV Store", "Игры", "Аркады"] and ver["description"] == "A test game"
        zip_path = os.path.join(dist, "ALAV-pubtest-1.0.0-linux-arm64.zip")
        assert os.path.isfile(zip_path), "the test expects the kit to be its own workspace (no .workspace file)"
        with open(zip_path, "rb") as f:
            local = f.read()
        artifact, = ver["_artifacts"]
        assert hashlib.sha256(FILES[artifact["_fileId"]]).hexdigest() == hashlib.sha256(local).hexdigest()
        assert (artifact["platform"], artifact["arch"], artifact["format"]) == ("linux", "arm64", "zip")
        assert ver["fileSize"] == len(local) and ver["fileName"] == os.path.basename(zip_path)

        PENDING.append(True)                                                   # the account lost its approval
        code, out, sent = publish(game, "--release")
        assert code != 0 and "403" in out and "approved" in out and ver["status"] == 0, out
        del PENDING[:]

        code, out, sent = publish(game, "--release")                           # the draft goes to review, no upload
        assert code == 0 and "sent for review" in out and "after the administrator approves" in out, out
        assert "published:" not in out, out
        assert sent == ["GET /api/v2/applications/mine", "PATCH " + VERSIONS + "/{id}/publish"], sent
        assert ver["status"] == 4 and app_json(app)["latestVersion"] is None    # nothing is public yet

        for flags in ((), ("--release",)):                                     # a rerun while in review: just waits
            code, out, sent = publish(game, *flags)
            assert code == 0 and "still waiting" in out and sent == ["GET /api/v2/applications/mine"], out
        assert ver["status"] == 4 and len(app["versions"]) == 1

        reject(ver, "Нет описания управления")                                 # rejected: the reason is shown,
        code, out, sent = publish(game)                                        # a plain publish replaces the draft
        assert code == 0 and "rejected" in out and "Нет описания управления" in out and "draft" in out, out
        assert "DELETE " + VERSIONS + "/{id}" in sent and "PATCH " + VERSIONS + "/{id}/publish" not in sent, sent
        ver, = app["versions"]
        assert ver["status"] == 0 and ver["rejectionReason"] is None           # a new draft of the current build
        reject_again = publish(game, "--release")
        assert reject_again[0] == 0 and ver["status"] == 4, reject_again[1]
        reject(ver, "Ещё раз")                                                 # --release after a rejection uploads
        code, out, sent = publish(game, "--release")                           # the current build, then submits it
        assert code == 0 and "Ещё раз" in out and "sent for review" in out and "POST " + VERSIONS in sent, out
        ver, = app["versions"]
        assert ver["status"] == 4 and ver["rejectionReason"] is None

        approve(ver)                                                           # the administrator approves
        code, out, sent = publish(game)                                        # the same version again
        assert code != 0 and "already published" in out and sent == ["GET /api/v2/applications/mine"], out

        with open(os.path.join(game, "big.bin"), "wb") as f:                   # makes the zip span two chunks
            f.write(os.urandom(6 * 1024 * 1024))
        set_version(game, "1.0.1")
        code, out, sent = publish(game, "--release")                           # an update of an approved app
        assert code == 0 and "sent for review" in out, out                     # is reviewed as well
        assert "POST /api/v2/applications" not in sent and sent.count("POST /api/v1/Files/upload/chunk") == 3, sent
        # Until the approval the published version stays the one in the store.
        assert len(APPS) == 1 and [(v["version"], v["status"]) for v in app["versions"]] == [("1.0.0", 1), ("1.0.1", 4)]
        assert app_json(app)["latestVersion"]["version"] == "1.0.0"
        approve(app["versions"][1])
        assert [(v["version"], v["status"]) for v in app["versions"]] == [("1.0.0", 2), ("1.0.1", 1)]
        with open(os.path.join(dist, "ALAV-pubtest-1.0.1-linux-arm64.zip"), "rb") as f:
            assert FILES[app["versions"][1]["_artifacts"][0]["_fileId"]] == f.read()
        os.remove(os.path.join(game, "big.bin"))

        set_version(game, "1.0.2")
        assert publish(game)[0] == 0
        first_draft = app["versions"][2]["id"]
        code, out, sent = publish(game)                                        # a draft again: the old one is replaced
        assert code == 0 and "DELETE " + VERSIONS + "/{id}" in sent and "draft" in out, out
        assert len(app["versions"]) == 3 and app["versions"][2]["id"] != first_draft and app["versions"][2]["status"] == 0

        set_version(game, "1.0.3")
        FAIL["POST versions"] = GENERIC                                        # the server's 400 is shown cleanly
        code, out, sent = publish(game)
        assert code != 0 and "400" in out and GENERIC in out, out
        FAIL["POST artifacts"] = "Файл не найден"                              # no half-made draft is left behind
        code, out, sent = publish(game)
        assert code != 0 and "400" in out and "Файл не найден" in out and sent[-1] == "DELETE " + VERSIONS + "/{id}", out
        assert len(app["versions"]) == 3
    finally:
        server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(os.path.join(dist, "pubtest"), ignore_errors=True)
        for name in os.listdir(dist) if os.path.isdir(dist) else ():
            if name.startswith("ALAV-pubtest-"):
                os.remove(os.path.join(dist, name))
    print("OK")


if __name__ == "__main__":
    main()
