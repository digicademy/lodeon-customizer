import os
import sys

from lodeon_customizer.cli import main

if __name__ == "__main__":
    if sys.platform == "linux" and getattr(sys, "frozen", False):
        # Desktop programs started by the app need the host's library search path.
        if "LD_LIBRARY_PATH_ORIG" in os.environ:
            os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
    raise SystemExit(main())
