"""Launch the standalone Customizer on this computer's loopback interface."""

from contextlib import ExitStack
import argparse
import errno
import os
import sys
import webbrowser
from http.client import HTTPConnection
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from .configuration import ConfigError, data_directory
from .folders import load_folder
from .desktop import message_page
from .http_service import ModelService


def main() -> int:
    parser = argparse.ArgumentParser(prog="LODEON-Customizer")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = "http://127.0.0.1:8765/"
    try:
        with ExitStack() as stack:
            default = data_directory()
            preference = default.parent / "settings-folder"
            data = args.data or default
            warning = ""
            try:
                if args.data is None and preference.is_file():
                    data = Path(os.fsdecode(preference.read_bytes()))
                    if not data.is_absolute() or not (data / "config.yml").is_file():
                        raise ConfigError("folder_unavailable")
                data = data.resolve()
                identity, models = load_folder(data)
            except (OSError, ValueError):
                if args.data is not None:
                    raise
                warning = "The saved folder is unavailable or its configuration is invalid. Choose a Core package or an empty folder to continue."
                data = Path(stack.enter_context(TemporaryDirectory()))
                identity, models = load_folder(data)
            server = stack.enter_context(ModelService(("127.0.0.1", 8765), models, data=data, identity=identity))
            server.folder_preference = None if args.data else preference
            server.folder_warning = warning
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
                notice.write(message_page("Customizer could not start", message).encode("utf-8"))
            webbrowser.open(Path(notice.name).as_uri())
        return 1


if __name__ == "__main__":
    sys.exit(main())
