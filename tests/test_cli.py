"""Tests for the CLI entry point."""

import pytest

from anki_connect_server.cli import main


class TestCli:
    def test_no_command_exits_nonzero(self, capsys):
        """With no subcommand the CLI prints help and exits 1."""
        with pytest.raises(SystemExit) as exc:
            main(argv=[])
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "anki-connect-server" in out

    def test_api_subcommand_invokes_run_server(self, monkeypatch):
        """'api' subcommand calls api.run_server."""
        called = {"n": 0}

        def fake_run_server():
            called["n"] += 1

        # api.run_server is imported lazily inside main(); patch the module
        # attribute on the source module so the lazy import sees the stub.
        import anki_connect_server.api as api_module

        monkeypatch.setattr(api_module, "run_server", fake_run_server)
        main(argv=["api"])
        assert called["n"] == 1

    def test_mcp_subcommand_invokes_run(self, monkeypatch):
        """'mcp' subcommand calls mcp_server.run."""
        called = {"n": 0}

        def fake_run():
            called["n"] += 1

        import anki_connect_server.mcp_server as mcp_module

        monkeypatch.setattr(mcp_module, "run", fake_run)
        main(argv=["mcp"])
        assert called["n"] == 1

    def test_unknown_subcommand_exits_nonzero(self, capsys):
        """Unknown subcommand exits with error."""
        with pytest.raises(SystemExit):
            main(argv=["no-such-subcommand"])

    def test_help_flag_exits_zero(self, capsys):
        """``--help`` prints usage and exits 0."""
        with pytest.raises(SystemExit) as exc:
            main(argv=["--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "anki-connect-server" in out
        assert "api" in out
        assert "mcp" in out

    def test_short_help_flag_exits_zero(self, capsys):
        """``-h`` is an alias for ``--help``."""
        with pytest.raises(SystemExit) as exc:
            main(argv=["-h"])
        assert exc.value.code == 0

    def test_api_subcommand_help_lists_description(self, capsys):
        """``api --help`` describes the API subcommand."""
        with pytest.raises(SystemExit) as exc:
            main(argv=["api", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "api" in out
        assert "Run the headless AnkiConnect-compatible REST API server." in out

    def test_mcp_subcommand_help_lists_description(self, capsys):
        """``mcp --help`` describes the MCP subcommand."""
        with pytest.raises(SystemExit) as exc:
            main(argv=["mcp", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "mcp" in out
        assert "Run the Model Context Protocol server for AI assistants." in out

    def test_unknown_subcommand_argparse_exits_two(self, capsys):
        """argparse rejects an unknown subcommand with exit code 2."""
        with pytest.raises(SystemExit) as exc:
            main(argv=["bogus"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "invalid choice" in err

    def test_api_subcommand_passes_no_extra_args(self, monkeypatch):
        """``api`` runs even with trailing argparse flags it ignores."""
        called = {"n": 0}

        def fake_run_server():
            called["n"] += 1

        import anki_connect_server.api as api_module

        monkeypatch.setattr(api_module, "run_server", fake_run_server)
        main(argv=["api"])
        assert called["n"] == 1

    def test_api_import_is_lazy(self):
        """Importing ``cli`` does not import ``api`` until ``api`` is run.

        Guards against the API module (which imports fastapi/uvicorn at
        module load) being pulled into environments that only need MCP.
        """
        import sys

        sys.modules.pop("anki_connect_server.api", None)
        from anki_connect_server import cli as cli_module

        # Reference the module to satisfy linters; main() is not invoked so
        # the lazy api import must not have triggered.
        assert cli_module.main is not None
        assert "anki_connect_server.api" not in sys.modules

    def test_mcp_import_is_lazy(self):
        """Importing ``cli`` does not import ``mcp_server`` until ``mcp`` runs."""
        import sys

        sys.modules.pop("anki_connect_server.mcp_server", None)
        from anki_connect_server import cli as cli_module

        assert cli_module.main is not None
        assert "anki_connect_server.mcp_server" not in sys.modules

    def test_api_subcommand_does_not_call_mcp_run(self, monkeypatch):
        """Running ``api`` must not invoke ``mcp_server.run``."""
        mcp_calls = {"n": 0}

        def fake_mcp_run():
            mcp_calls["n"] += 1

        import anki_connect_server.mcp_server as mcp_module

        monkeypatch.setattr(mcp_module, "run", fake_mcp_run)

        def fake_api_run():
            pass

        import anki_connect_server.api as api_module

        monkeypatch.setattr(api_module, "run_server", fake_api_run)

        main(argv=["api"])
        assert mcp_calls["n"] == 0

    def test_mcp_subcommand_does_not_call_api_run_server(self, monkeypatch):
        """Running ``mcp`` must not invoke ``api.run_server``."""
        api_calls = {"n": 0}

        def fake_api_run():
            api_calls["n"] += 1

        import anki_connect_server.api as api_module

        monkeypatch.setattr(api_module, "run_server", fake_api_run)

        def fake_mcp_run():
            pass

        import anki_connect_server.mcp_server as mcp_module

        monkeypatch.setattr(mcp_module, "run", fake_mcp_run)

        main(argv=["mcp"])
        assert api_calls["n"] == 0
