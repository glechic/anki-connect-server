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
