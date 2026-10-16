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
from fairlendkit.report.csv import render_metrics_csv
from fairlendkit.report.html import render_html
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


class _StoreOnce(argparse.Action):
    """Reject ambiguous repetition of a singleton path option."""

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"argument {option_string}: may not be repeated")
        setattr(namespace, self.dest, values)


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
    audit.add_argument("--data", required=True, type=Path, action=_StoreOnce)
    audit.add_argument("--config", required=True, type=Path, action=_StoreOnce)
    audit.add_argument("--output", required=True, type=Path, action=_StoreOnce)
    audit.add_argument(
        "--format",
        action="append",
        choices=("json", "csv", "html"),
        dest="formats",
        help="output format; may be repeated (default: all)",
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

    formats = tuple(dict.fromkeys(args.formats or ("json", "csv", "html")))
    renderers = {
        "json": ("audit-result.json", render_json),
        "csv": ("metrics.csv", render_metrics_csv),
        "html": ("report.html", render_html),
    }
    artifacts = {
        args.output / renderers[format_name][0]: renderers[format_name][1](result)
        for format_name in formats
    }
    _publish_many(artifacts, overwrite=args.overwrite)
    print(f"wrote {len(artifacts)} artifact(s) to {args.output}")
    return 0


def _require_regular_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise OSError(f"{label} path is not a regular file")


class _OutputError(Exception):
    """Expected safe-publication failure."""


def _publish_many(artifacts: dict[Path, bytes], *, overwrite: bool) -> None:
    if not artifacts:
        raise _OutputError("no output artifacts were selected")
    parents = {target.parent for target in artifacts}
    if len(parents) != 1:
        raise _OutputError("selected artifacts must share one output directory")
    output = next(iter(parents))
    temporary: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    published: list[Path] = []
    try:
        output.mkdir(parents=True, exist_ok=True)
        if not output.is_dir():
            raise _OutputError("output path is not a directory")
        conflicts = [target for target in artifacts if target.exists()]
        if conflicts and not overwrite:
            raise _OutputError("output target exists; use --overwrite to replace it")
        if any(target.is_symlink() or not target.is_file() for target in conflicts):
            raise _OutputError("an output target exists but is not a regular file")
        for target, content in artifacts.items():
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=output, prefix=f".{target.name}.new.", delete=False
            ) as stream:
                temporary[target] = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        for target in conflicts:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=output, prefix=f".{target.name}.old.", delete=False
            ) as stream:
                backup = Path(stream.name)
            backup.unlink()
            os.replace(target, backup)
            backups[target] = backup
        for target in artifacts:
            os.replace(temporary[target], target)
            temporary.pop(target)
            published.append(target)
        for backup in backups.values():
            backup.unlink(missing_ok=True)
    except _OutputError:
        raise
    except OSError as error:
        for target in reversed(published):
            target.unlink(missing_ok=True)
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)
        raise _OutputError("output could not be published safely") from error
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
        for path in backups.values():
            path.unlink(missing_ok=True)


def _diagnostic(message: str) -> None:
    print(f"fairlendkit: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
