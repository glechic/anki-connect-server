from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("anki-connect-server")
except PackageNotFoundError:
    __version__ = "0.0.0"

ANKICONNECT_API_VERSION = 6
