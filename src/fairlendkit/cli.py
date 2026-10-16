"""Command-line composition for the FairLendKit audit workflow."""

from __future__ import annotations

import argparse
import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
import tempfile
from typing import Sequence

import pandas as pd
from pydantic import ValidationError

from fairlendkit.api import run_audit
from fairlendkit.config import AuditConfig
from fairlendkit.data import DataValidationError
from fairlendkit.report.json import render_json

EXIT_INTERNAL = 1
EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_VALIDATION = 4
EXIT_OUTPUT = 5


class _CliParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"fairlendkit: error: {message}\n")


def _package_version() -> str:
    try:
        return version("fairlendkit")
    except PackageNotFoundError:
        return "0+unknown"


def _parser() -> argparse.ArgumentParser:
    parser = _CliParser(prog="fairlendkit")
    parser.add_argument("--version", action="version", version=_package_version())
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="run one reproducible audit")
    audit.add_argument("--data", required=True, type=Path)
    audit.add_argument("--config", required=True, type=Path)
    audit.add_argument("--output", required=True, type=Path)
    audit.add_argument(
        "--format",
        action="append",
        choices=("json",),
        dest="formats",
        help="output format; Milestone 4.1 currently supports json",
    )
    audit.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _run_audit_command(args)
    except (OSError, UnicodeError, json.JSONDecodeError, pd.errors.ParserError):
        _diagnostic("input could not be read or parsed")
        return EXIT_INPUT
    except (ValidationError, DataValidationError, TypeError, ValueError):
        _diagnostic("configuration or audit data failed validation")
        return EXIT_VALIDATION
    except _OutputError as error:
        _diagnostic(str(error))
        return EXIT_OUTPUT
    except Exception:
        _diagnostic("unexpected internal error")
        return EXIT_INTERNAL


def _run_audit_command(args: argparse.Namespace) -> int:
    _require_regular_file(args.data, "data")
    _require_regular_file(args.config, "config")
    with args.config.open("r", encoding="utf-8") as stream:
        raw_config = json.load(stream)
    config = AuditConfig.model_validate(raw_config)
    data = pd.read_csv(args.data, encoding="utf-8")
    result = run_audit(data, config)

    formats = tuple(dict.fromkeys(args.formats or ("json",)))
    if formats != ("json",):
        raise ValueError("unsupported output format selection")
    target = args.output / "audit-result.json"
    _publish_one(target, render_json(result), overwrite=args.overwrite)
    print(f"wrote {target}")
    return 0


def _require_regular_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise OSError(f"{label} path is not a regular file")


class _OutputError(Exception):
    """Expected safe-publication failure."""


def _publish_one(target: Path, content: bytes, *, overwrite: bool) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.is_dir():
            raise _OutputError("output path is not a directory")
        if target.exists() and not overwrite:
            raise _OutputError("output target exists; use --overwrite to replace it")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=f".{target.name}.", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    except _OutputError:
        raise
    except OSError as error:
        raise _OutputError("output could not be published safely") from error


def _diagnostic(message: str) -> None:
    print(f"fairlendkit: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
