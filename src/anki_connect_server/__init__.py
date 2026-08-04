from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("anki-connect-server")
except PackageNotFoundError:
    __version__ = "0.0.0"