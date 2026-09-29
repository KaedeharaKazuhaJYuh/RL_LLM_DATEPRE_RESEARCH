"""Validate the project's display version and calculate the next release number."""

import argparse
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^5\.(0|[1-9][0-9]*)\.(0|05|[1-9][0-9]+)$")


def parse_display_version(value: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"invalid V5 display version: {value!r}")
    minor, patch = int(match[1]), int(match[2])
    if minor == 4 or 40 <= patch <= 49 or patch % 5:
        raise ValueError(f"reserved or off-sequence V5 version: {value!r}")
    return 5, minor, patch


def next_display_version(value: str) -> str:
    major, minor, patch = parse_display_version(value)
    patch += 5
    if patch >= 100:
        minor += 1
        if minor == 4:
            minor = 5
        patch = 0
    elif 40 <= patch <= 49:
        patch = 50
    return f"{major}.{minor}.{patch:02d}" if patch == 5 else f"{major}.{minor}.{patch}"


def package_version(value: str) -> str:
    major, minor, patch = parse_display_version(value)
    return f"{major}.{minor}.{patch}"


def check_repository(root: Path = ROOT) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    expected = package_version(version)
    with (root / "pyproject.toml").open("rb") as stream:
        actual = tomllib.load(stream)["project"]["version"]
    if actual != expected:
        raise ValueError(f"pyproject.toml version {actual!r} must be {expected!r}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    if not readme.startswith(f"# RL + LLM Data Analysis Agent — V{version}"):
        raise ValueError("README heading does not match VERSION")
    if "本项目的 GitHub 推送仍由用户自行完成。" in readme:
        raise ValueError("README contains a retired publishing note")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check release metadata")
    parser.add_argument("--next", action="store_true", help="show the next display version")
    args = parser.parse_args()
    version = check_repository()
    if args.next:
        print(f"V{next_display_version(version)}")
    else:
        print(f"V{version}: release metadata consistent")


if __name__ == "__main__":
    main()
