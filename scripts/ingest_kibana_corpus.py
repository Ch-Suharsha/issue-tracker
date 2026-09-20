#!/usr/bin/env python3
"""CLI wrapper for eval corpus ingest."""

from issue_triage.eval.run import main

if __name__ == "__main__":
    raise SystemExit(main(["ingest"] + __import__("sys").argv[1:]))
