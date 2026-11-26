# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Signs the files of a release with an Ed25519 key and checks a signed set. It never reads, holds or prints the private key: the PATH of the key file is handed to `openssl`, which does the signing.

  python tools/sign_release.py sign   FOLDER --key FILE      writes <name>.ed25519.sig for SHA256SUMS and for every file SHA256SUMS names
  python tools/sign_release.py verify FOLDER                 every signature against the release key of the product, and every file against SHA256SUMS

A signature is one line of base64 holding the 64 bytes of Ed25519 over the BYTES of the file. `verify` needs no network and no openssl. Exit codes: 0 good, 1 not good, 2 usage.
"""
import argparse
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))      # works also under `py -3 -I`
from github_actions_monitor.security import keyring, release_verify      # noqa: E402


def listed_files(folder):
    """SHA256SUMS and the names it lists (SystemExit when it is not there or not clean)."""
    sums = folder / release_verify.SUMS_NAME
    if not sums.is_file():
        raise SystemExit("SIGN=FAIL there is no SHA256SUMS in " + str(folder))
    listed, bad = release_verify.parse_sums(sums.read_text(encoding="ascii"))
    if bad or not listed:
        raise SystemExit("SIGN=FAIL SHA256SUMS is not a clean list of files")
    for name, expected in listed.items():
        if not (folder / name).is_file() or release_verify.sha256_of(folder / name) != expected:
            raise SystemExit("SIGN=FAIL a file of SHA256SUMS is missing or differs: " + name)
    return [release_verify.SUMS_NAME, *sorted(listed)]


def openssl_signature(key_path, path, openssl="openssl"):
    """The 64 bytes openssl makes for the file. The key is only named to openssl."""
    with tempfile.TemporaryDirectory(prefix="sign_") as scratch:
        out = Path(scratch) / "signature"
        done = subprocess.run([openssl, "pkeyutl", "-sign", "-inkey", str(key_path), "-rawin", "-in", str(path), "-out", str(out)], capture_output=True, timeout=120,
                              creationflags=0x08000000 if os.name == "nt" else 0)
        if done.returncode != 0 or not out.is_file():      # what openssl says is not repeated: it could quote the key file
            raise SystemExit("SIGN=FAIL openssl could not sign " + Path(path).name)
        signature = out.read_bytes()
    if len(signature) != 64:
        raise SystemExit("SIGN=FAIL the key is not an Ed25519 key")
    return signature


def sign(folder, key_path, openssl="openssl"):
    folder = Path(folder)
    if not Path(key_path).is_file():
        raise SystemExit("SIGN=FAIL there is no key file")
    names = listed_files(folder)
    for name in names:
        text = base64.b64encode(openssl_signature(key_path, folder / name, openssl)).decode("ascii") + "\n"
        (folder / (name + keyring.SIGNATURE_SUFFIX)).write_text(text, encoding="ascii", newline="\n")
    return names


def verify(folder, keys=None):
    """[problem] of a signed set; empty list = every listed file matches and every signature is of the release key."""
    folder = Path(folder)
    report = release_verify.verify_release(folder, keys=keys)
    problems = []
    if report["signature"] != keyring.VALID:
        problems.append("SHA256SUMS: signature " + report["signature"])
    problems += [f"{name}: {state}" for name, state in report["files"].items() if state != "ok"]
    problems += ["SHA256SUMS: a line is not clean" for _ in report["bad_lines"]]
    if not report["files"]:
        problems.append("SHA256SUMS lists no file")
    for name in report["files"]:
        result, _ = keyring.verify_file(folder / name, scope="release", keys=keys)
        if result != keyring.VALID:
            problems.append(f"{name}: signature {result}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sign_release.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("sign", "verify"))
    parser.add_argument("folder")
    parser.add_argument("--key", help="the file of the private key (sign only); it is given to openssl and never read here")
    args = parser.parse_args(argv)
    if args.action == "sign":
        if not args.key:
            parser.error("sign needs --key")
        names = sign(args.folder, args.key)
        print("SIGN=OK " + str(len(names)) + " files signed")
    problems = verify(args.folder)      # a set signed with another key than the one in the product fails here, before anybody publishes it
    if problems:
        print("VERIFY=FAIL " + "; ".join(problems))
        return 1
    print("VERIFY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
