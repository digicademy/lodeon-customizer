"""Launch the standalone Customizer on this computer's loopback interface."""

import argparse
import errno
import sys
import webbrowser
from http.client import HTTPConnection
from pathlib import Path
from tempfile import NamedTemporaryFile

from .configuration import ConfigError, data_directory, initialize
from .http_service import ModelService
from .profiles import LocalModels


def main() -> int:
    parser = argparse.ArgumentParser(prog="LODEON Customizer")
    parser.add_argument("--data", type=Path, default=data_directory())
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = "http://127.0.0.1:8765/"
    try:
        identity = initialize(args.data)
        models = LocalModels.load(args.data / "config.yml", identity)
        with ModelService(("127.0.0.1", 8765), models, data=args.data, identity=identity) as server:
            if not args.no_browser:
                webbrowser.open(url)
            server.serve_forever()
        return 0
    except (ConfigError, OSError, ValueError) as error:
        if isinstance(error, OSError) and (error.errno == errno.EADDRINUSE or getattr(error, "winerror", None) == 10013):
            message = "Port 8765 is already in use."
            conn = HTTPConnection("127.0.0.1", 8765, timeout=2)
            try:
                conn.request("GET", "/")
                if conn.getresponse().getheader("X-LODEON-Customizer") == "desktop":
                    if not args.no_browser:
                        webbrowser.open(url)
                    return 0
            except OSError:
                pass
            finally:
                conn.close()
        else:
            message = "Check config.yml and the permissions of the Customizer data folder."
        if sys.stderr:
            print(message, file=sys.stderr)
        if not args.no_browser:
            with NamedTemporaryFile(suffix=".html", delete=False) as notice:
                notice.write(("<title>LODEON Customizer</title><h1>LODEON Customizer</h1><p>" + message + "</p>").encode())
            webbrowser.open(Path(notice.name).as_uri())
        return 1


if __name__ == "__main__":
    sys.exit(main())
