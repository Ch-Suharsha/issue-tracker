from __future__ import annotations

import uvicorn


def run() -> None:
    uvicorn.run(
        "issue_triage.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )


if __name__ == "__main__":
    run()
