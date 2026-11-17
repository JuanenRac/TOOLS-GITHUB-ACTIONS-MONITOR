#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""E5 - the two volumes: the mode of the files that hold secrets, a backup that leaves the secrets out, a restore into a new volume, a restart with the data in place, and the move of the same
volumes from the image of the previous version to the one under check."""
import json
import re
import sys
import zipfile

import audit_lib as lib

MODES = r'''
import json, os, stat
rows = []
for top in ("/data", "/config"):
    for folder, dirs, files in os.walk(top):
        for name in dirs + files:
            path = os.path.join(folder, name)
            try:
                info = os.lstat(path)
            except OSError:
                continue
            rows.append({"path": path, "mode": oct(stat.S_IMODE(info.st_mode)), "dir": stat.S_ISDIR(info.st_mode), "uid": info.st_uid})
print("AUDIT-JSON " + json.dumps(rows))
'''
SECRETISH = re.compile(r"(credential|token|secret|password|users|sessions|\.key$|\.pem$|hosts\.yml|audit_chain|audit-chain)", re.I)


def cli(s, name, token, *args, stdin=None):
    cmd = ["docker", "exec"] + (["-i"] if stdin is not None else []) + ["-e", "MONITOR_ACCESS_TOKEN=" + token, name, "python", "/app/bin/monitor_cli.py", *args]
    return s.run(cmd, input_text=stdin, timeout=120)


def account_state(s, name, token):
    code, out = cli(s, name, token, "accounts", "--json")
    try:
        data = json.loads(out)["data"]
        return {a["id"]: a["state"] for a in data["accounts"]}.get("default", "?")
    except (ValueError, KeyError, TypeError):
        return "?"


def start(s, what, image, config, data, mounts, env, extra=()):
    name, code, out = s.service(what, image, ["%s:/config" % config, "%s:/data" % data] + mounts, env, extra=list(extra))
    healthy = code == 0 and s.wait_healthy(name, 180)
    return name, healthy, out


def body(s):
    image = s.image()
    mounts, env, good = s.login_files()
    config, data = s.volume("config"), s.volume("data")
    name, healthy, out = start(s, "one", image, config, data, mounts, env)
    if not s.check("the container starts on two new volumes", healthy, s.logs(name)[-1000:]):
        return
    token = s.read_token(name)
    code, out = cli(s, name, token, "credential", "replace", "--account", "default", "--new-token-file", "-", stdin=good + "\n")
    s.check("a replacement of the login is kept (credential replace)", code == 0, out[-400:])
    s.docker("exec", name, "sh", "-c", "umask 077; echo audit-marker-1 > /data/state/audit_marker")

    # 1. the modes
    code, out = s.python_in(name, MODES, label="list the files of the volumes with their modes")
    match = re.search(r"AUDIT-JSON (\[.*\])", out)
    rows = json.loads(match.group(1)) if match else []
    s.check("the modes of the volumes could be listed", bool(rows), out[-300:])
    by_path = {r["path"]: r for r in rows}
    wrong = [r for r in rows if not r["dir"] and SECRETISH.search(r["path"].rsplit("/", 1)[-1]) and int(r["mode"], 8) & 0o077]
    s.check("every file that holds a secret (token, credential, users, sessions, keys) is 0600: nothing readable by group or others", not wrong, ", ".join("%s %s" % (r["path"], r["mode"]) for r in wrong))
    state_files = [r for r in rows if r["path"].startswith(("/data/state/", "/data/secrets/", "/data/gh/")) and not r["dir"] and int(r["mode"], 8) & 0o077]
    s.check("nothing in /data/state, /data/secrets or /data/gh is readable by group or others", not state_files, ", ".join("%s %s" % (r["path"], r["mode"]) for r in state_files))
    token_row = by_path.get("/data/state/access_token", {})
    s.check("the access token file is 0600", token_row.get("mode") == "0o600", json.dumps(token_row))
    s.check("the folders of the secrets and the state are 0700", all(by_path.get(p, {}).get("mode") == "0o700" for p in ("/data/secrets", "/data/state")), json.dumps([by_path.get(p) for p in ("/data/secrets", "/data/state")]))
    credential = by_path.get("/data/accounts/default/credential", {})
    s.check("the replaced login of the account is 0600", credential.get("mode") == "0o600", json.dumps(credential))
    s.check("everything in the volumes belongs to the user 10001", all(r["uid"] == 10001 for r in rows), ", ".join(r["path"] for r in rows if r["uid"] != 10001)[:400])
    other = sorted({r["mode"] for r in rows if not r["dir"] and r not in wrong})
    s.note("modes found on files in the volumes: %s" % ", ".join(other))

    # 2. the backup of the storage leaves the secrets out
    code, out = s.docker("exec", name, "python", "/app/tools/backup_storage.py", "backup", "/data/state/backup.zip", "--backend", "file", label="backup_storage.py backup")
    s.check("backup_storage.py backup writes and verifies a backup", code == 0, out[-500:])
    code, out = s.docker("exec", name, "python", "/app/tools/backup_storage.py", "verify", "/data/state/backup.zip", label="backup_storage.py verify")
    s.check("backup_storage.py verify accepts it", code == 0, out[-500:])
    local = s.work / "backup.zip"
    s.docker("cp", "%s:/data/state/backup.zip" % name, str(local))
    if local.is_file():
        try:
            with zipfile.ZipFile(local) as archive:
                blob = b"".join(archive.read(n) for n in archive.namelist())
                names = archive.namelist()
        except (OSError, zipfile.BadZipFile) as error:
            blob, names = b"", [str(error)]
        s.check("the backup does not contain the access token or the login of GitHub", token.encode() not in blob and good.encode() not in blob, "members: %s" % names[:8])
    else:
        s.check("the backup file could be copied out of the container", False, "")

    # 3. a copy of the two volumes, restored into two new ones
    for part, source in (("data", "/data"), ("config", "/config")):
        code = s.run_to_file(["docker", "exec", name, "tar", "czf", "-", "-C", source, "."], s.work / ("vol-%s.tgz" % part), label="tar of the %s volume" % part)
        s.check("a copy of the %s volume is made with tar" % part, code == 0, "")
    config2, data2 = s.volume("config2"), s.volume("data2")
    for volume, part, target in ((data2, "data", "/data"), (config2, "config", "/config")):
        code, out = s.docker("run", "--rm", "--label", lib.LABEL, "-v", "%s:%s" % (volume, target), "-v", "%s:/backup:ro" % s.work, "--entrypoint", "tar", image, "xzf", "/backup/vol-%s.tgz" % part, "-C", target,
                             label="restore the %s volume into a new one" % part)
        s.check("the %s volume is restored into a new volume" % part, code == 0, out[-400:])
    name2, healthy, out = start(s, "restored", image, config2, data2, mounts, env)
    s.check("a container on the restored volumes becomes healthy", healthy, s.logs(name2)[-800:])
    s.check("it has the same access token, the marker and the login mode", s.read_token(name2) == token and "audit-marker-1" in s.docker("exec", name2, "cat", "/data/state/audit_marker")[1]
            and s.docker("exec", name2, "stat", "-c", "%a", "/data/accounts/default/credential")[1].strip() == "600", "")
    s.docker("rm", "-f", name2)

    # 4. a restart keeps the data
    s.docker("restart", "-t", "20", name)
    s.check("after docker restart the container is healthy again", s.wait_healthy(name, 180), s.logs(name)[-800:])
    s.check("the access token, the marker and the account are still there", s.read_token(name) == token and "audit-marker-1" in s.docker("exec", name, "cat", "/data/state/audit_marker")[1]
            and account_state(s, name, token) == "ok", "state: %s" % account_state(s, name, token))
    s.docker("rm", "-f", name)

    # 5. the migration: the volumes of the previous image are taken by the image under check
    if not s.args.previous:
        s.note("no previous version was given (--previous): the migration between two images was not checked")
        return
    old_image = "docker-audit/monitor-previous:%s" % s.suffix
    old_version = "previous"
    if not s.build_image(s.args.previous, old_image, old_version):
        return
    config3, data3 = s.volume("config3"), s.volume("data3")
    old, healthy, out = start(s, "old", old_image, config3, data3, mounts, env)
    s.check("the PREVIOUS image starts on new volumes", healthy, s.logs(old)[-800:])
    old_token = s.read_token(old)
    s.docker("exec", old, "sh", "-c", "umask 077; echo audit-marker-2 > /data/state/audit_marker")
    cli(s, old, old_token, "credential", "replace", "--account", "default", "--new-token-file", "-", stdin=good + "\n")
    s.docker("stop", "-t", "30", old)
    s.docker("rm", old)
    new, healthy, out = start(s, "new", image, config3, data3, mounts, env)
    s.check("the image under check starts on the volumes of the previous one", healthy, s.logs(new)[-1200:])
    s.check("the access token, the marker, the replaced login and the account survive the move", s.read_token(new) == old_token and "audit-marker-2" in s.docker("exec", new, "cat", "/data/state/audit_marker")[1]
            and s.docker("exec", new, "stat", "-c", "%a", "/data/accounts/default/credential")[1].strip() == "600" and account_state(s, new, old_token) == "ok", "state: %s" % account_state(s, new, old_token))
    log = s.logs(new)
    s.check("the log of the first start on old volumes has no traceback or migration error", "Traceback" not in log and "migration failed" not in log.lower(), log[-800:])


if __name__ == "__main__":
    sys.exit(lib.main_of("E5", "Volumes: file modes, backup, restore, restart and migration between two images", body))
