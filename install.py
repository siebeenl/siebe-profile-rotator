import sys
import os
import subprocess


def banner(text):
    print("\n" + "=" * 52)
    print(f"  {text}")
    print("=" * 52)

def ok(t):   print(f"  [OK]    {t}")
def fail(t): print(f"  [FAIL]  {t}")
def info(t): print(f"  [INFO]  {t}")




def check_python() -> bool:
    banner("Checking Python version")
    major, minor = sys.version_info[:2]
    info(f"Python {major}.{minor} detected  ({sys.executable})")
    if major < 3 or (major == 3 and minor < 9):
        fail(f"Python 3.9+ required. You have {major}.{minor}.")
        info("Download from: https://www.python.org/downloads/")
        return False
    ok(f"Python {major}.{minor} — supported.")
    return True




def check_pip() -> bool:
    banner("Checking pip")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        fail("pip not found.")
        info("Try: python -m ensurepip --upgrade")
        return False
    ok(result.stdout.strip())
    info("Upgrading pip...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True
    )
    ok("pip up to date.")
    return True




PACKAGES = [
    ("aiohttp", "3.11.18"),
]

def install_packages() -> bool:
    banner("Installing dependencies")
    all_ok = True
    for package, version in PACKAGES:
        pkg_str = f"{package}=={version}"
        info(f"Installing {pkg_str}...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_str],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            ok(f"{pkg_str} installed.")
        else:
            info(f"Pinned version failed — trying latest {package}...")
            r2 = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True
            )
            if r2.returncode == 0:
                ok(f"{package} (latest) installed.")
            else:
                fail(f"Could not install {package}.")
                print(r2.stderr)
                all_ok = False
    return all_ok




def verify_imports() -> bool:
    banner("Verifying imports")
    try:
        import aiohttp
        ok(f"aiohttp {aiohttp.__version__}")
    except ImportError as e:
        fail(f"aiohttp import failed: {e}")
        return False
    try:
        import asyncio, itertools, logging, random, signal, traceback
        ok("Standard library — all OK")
    except ImportError as e:
        fail(f"stdlib import failed: {e}")
        return False
    return True




def check_files() -> bool:
    banner("Checking project files")
    required = ["main.py", "config.py"]
    all_ok = True
    for f in required:
        if os.path.isfile(f):
            ok(f"{f} found.")
        else:
            fail(f"{f} MISSING — must be in the same folder as install.py")
            all_ok = False
    return all_ok




def check_config() -> bool:
    banner("Checking config.py")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", "config.py")
        cfg  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cfg)
    except Exception as e:
        fail(f"config.py failed to load: {e}")
        return False

    errors = []

    if not hasattr(cfg, "STATUSES") or not cfg.STATUSES:
        errors.append("STATUSES is missing or empty")
    else:
        ok(f"STATUSES — {len(cfg.STATUSES)} entries")

    if not hasattr(cfg, "ROTATION_INTERVAL"):
        errors.append("ROTATION_INTERVAL is missing")
    elif not isinstance(cfg.ROTATION_INTERVAL, (int, float)) or cfg.ROTATION_INTERVAL < 1:
        errors.append(f"ROTATION_INTERVAL must be >= 1 (got {cfg.ROTATION_INTERVAL!r})")
    else:
        ok(f"ROTATION_INTERVAL — {cfg.ROTATION_INTERVAL}s")

    if not hasattr(cfg, "STATUS_TYPE"):
        errors.append("STATUS_TYPE is missing")
    elif cfg.STATUS_TYPE not in ("online", "idle", "dnd", "invisible"):
        errors.append(f"STATUS_TYPE '{cfg.STATUS_TYPE}' invalid")
    else:
        ok(f"STATUS_TYPE — {cfg.STATUS_TYPE}")

    for i, s in enumerate(getattr(cfg, "STATUSES", [])):
        if not isinstance(s, dict) or "text" not in s:
            errors.append(f"STATUSES[{i}] must have at least a 'text' key")

    if errors:
        for e in errors:
            fail(e)
        return False
    return True




def main():
    print()
    print("  Siebe Custom Status Rotator — Installer")

    steps = [
        ("Python version",   check_python),
        ("pip",              check_pip),
        ("Install packages", install_packages),
        ("Verify imports",   verify_imports),
        ("Project files",    check_files),
        ("config.py",        check_config),
    ]

    results = {}
    for name, fn in steps:
        try:
            results[name] = fn()
        except Exception as e:
            fail(f"Unexpected error in '{name}': {e}")
            results[name] = False

    banner("Summary")
    all_passed = True
    for name, passed in results.items():
        tag = "OK  " if passed else "FAIL"
        print(f"  [{tag}]  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  All good! Start the bot with:  python main.py")
    else:
        print("  Fix the issues above, then re-run install.py")

    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
