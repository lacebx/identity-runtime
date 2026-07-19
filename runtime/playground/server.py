"""
IdentityOS Playground Server.

Launches the Playground on http://localhost:8000/playground
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    print("  \u25B6 IdentityOS Playground")
    print("  \u2500" * 40)
    print("  Open http://localhost:8000/playground")
    print()
    uvicorn.run(
        "runtime.playground.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
