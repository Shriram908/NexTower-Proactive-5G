"""Convenience wrapper; the package CLI remains the single experiment implementation."""

from nextower.cli import main

raise SystemExit(main(["benchmark", *__import__("sys").argv[1:]]))
