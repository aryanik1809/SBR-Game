#!/usr/bin/env python3
"""Run the Luau tests with the plain Luau CLI.

    python3 tests/run.py [name ...] [dump]

The Roblox API isn't available outside Studio, so each module/test is copied to a temp folder with
`local Vector3, CFrame, ... = <mocks>` prepended on line 1 (keeps line numbers intact).
Needs the `luau` binary on PATH or in $LUAU.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUAU = os.environ.get("LUAU") or shutil.which("luau")
if not LUAU:
    sys.exit("luau CLI not found (set $LUAU)")

NAMES = ["Vector3", "CFrame", "Color3", "Enum", "Instance", "workspace", "Random", "Vector2"]


def main():
    argv = sys.argv[1:]
    dump = "dump" in argv
    extra = argv[argv.index("dump") + 1:] if dump else []
    args = [a for a in (argv[:argv.index("dump")] if dump else argv)]
    tmp = tempfile.mkdtemp(prefix="sbr_luau_")
    try:
        for sub in ("src/shared", "tests"):
            os.makedirs(os.path.join(tmp, sub))
            for f in os.listdir(os.path.join(ROOT, sub)):
                if not f.endswith(".luau"):
                    continue
                text = open(os.path.join(ROOT, sub, f)).read()
                # Roblox-style sibling requires -> plain relative requires
                text = re.sub(r'require\(script\.Parent\.(\w+)\)', r'require("./\1")', text)
                if f != "mock_roblox.luau":
                    mock = os.path.join(tmp, "tests", "mock_roblox")
                    rel = os.path.relpath(mock, os.path.join(tmp, sub))
                    rel = rel if rel.startswith(".") else "./" + rel
                    prelude = f'local __m = require("{rel}"); ' \
                              f'local {", ".join(NAMES)} = ' + ", ".join(f"__m.{n}" for n in NAMES) + "; "
                    text = prelude + text
                open(os.path.join(tmp, sub, f), "w").write(text)
        tests = sorted(f for f in os.listdir(os.path.join(tmp, "tests")) if f.endswith("_test.luau"))
        if args:
            tests = [t for t in tests if any(a in t for a in args)]
        rc = 0
        for t in tests:
            cmd = [LUAU, os.path.join(tmp, "tests", t)] + (["-a", "dump"] + extra if dump else [])
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp)
            if dump:
                sys.stdout.write(r.stdout)
            else:
                print(f"== {t}")
                print((r.stdout + r.stderr).rstrip())
            rc |= r.returncode
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
