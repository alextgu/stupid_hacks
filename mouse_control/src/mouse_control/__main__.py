"""CLI entry point for mouse control."""

from __future__ import annotations

import argparse
import logging
import sys
from .controller import MouseControlError, MouseController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control the mouse with WASD keys")
    parser.add_argument(
        "--step", type=int, default=20, help="Pixels to move per update (default: 20)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.04,
        help="Seconds between movement updates (default: 0.04)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (-v for info, -vv for debug)",
    )
    return parser


def configure_logging(verbose: int) -> None:
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    try:
        controller = MouseController(step=args.step, interval=args.interval)
    except (ValueError, MouseControlError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    try:
        controller.run()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrupted by user")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI invocation
    sys.exit(main())

