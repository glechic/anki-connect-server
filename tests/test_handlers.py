"""Tests for API handlers using real AnkiWrapper."""

import os

import pytest


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, anki_wrapper):
        """Test version handler."""
        from api.handlers import handle_version, API_VERSION
        result = await handle_version(anki_wrapper, {})
        assert result == API_VERSION

    @pytest.mark.asyncio
    async def test_handle_deck_names(self, anki_wrapper):
        """Test deckNames handler."""
        from api.handlers import handle_deck_names
        anki_wrapper.create_deck("Spanish")
        result = await handle_deck_names(anki_wrapper, {})
        assert "Default" in result
        assert "Spanish" in result

    @pytest.mark.asyncio
    async def test_handle_deck_names_and_ids(self, anki_wrapper):
        """Test deckNamesAndIds handler."""
        from api.handlers import handle_deck_names_and_ids
        deck_id = anki_wrapper.create_deck("TestDeck")
        result = await handle_deck_names_and_ids(anki_wrapper, {})
        assert "TestDeck" in result
        assert result["TestDeck"] == deck_id

    @pytest.mark.asyncio
    async def test_handle_create_deck(self, anki_wrapper):
        """Test createDeck handler."""
        from api.handlers import handle_create_deck
        result = await handle_create_deck(anki_wrapper, {"deck": "NewDeck"})
        assert result > 0

    @pytest.mark.asyncio
    async def test_handle_get_decks(self, anki_wrapper):
        """Test getDecks handler."""
        from api.handlers import handle_get_decks
        result = await handle_get_decks(anki_wrapper, {"cards": []})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handle_delete_decks(self, anki_wrapper):
        """Test deleteDecks handler."""
        from api.handlers import handle_delete_decks
        anki_wrapper.create_deck("ToDelete")
        await handle_delete_decks(anki_wrapper, {"decks": ["ToDelete"]})
        assert "ToDelete" not in anki_wrapper.deck_names()

    @pytest.mark.asyncio
    async def test_handle_change_deck(self, anki_wrapper):
        """Test changeDeck handler."""
        from api.handlers import handle_change_deck
        anki_wrapper.create_deck("Target")
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_id = anki_wrapper.find_cards("Test")[0]
        await handle_change_deck(anki_wrapper, {"cards": [card_id], "deck": "Target"})


class TestModelHandlers:
    """Test model-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_model_names(self, anki_wrapper):
        """Test modelNames handler."""
        from api.handlers import handle_model_names
        result = await handle_model_names(anki_wrapper, {})
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_field_names(self, anki_wrapper):
        """Test modelFieldNames handler."""
        from api.handlers import handle_model_field_names
        result = await handle_model_field_names(anki_wrapper, {"modelName": "Basic"})
        assert "Front" in result
        assert "Back" in result


class TestNoteHandlers:
    """Test note-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_add_note(self, anki_wrapper):
        """Test addNote handler."""
        from api.handlers import handle_add_note
        result = await handle_add_note(anki_wrapper, {
            "note": {
                "deckName": "Default",
                "modelName": "Basic",
                "fields": {"Front": "Test", "Back": "Answer"}
            }
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_add_notes(self, anki_wrapper):
        """Test addNotes handler."""
        from api.handlers import handle_add_notes
        result = await handle_add_notes(anki_wrapper, {
            "notes": [
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Note1", "Back": "Answer1"}
                },
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Note2", "Back": "Answer2"}
                }
            ]
        })
        assert len(result) == 2
        assert result[0] is not None
        assert result[1] is not None


class TestTagHandlers:
    """Test tag-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_tags(self, anki_wrapper):
        """Test getTags handler."""
        from api.handlers import handle_get_tags
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "TagTest", "Back": "Test"},
            "tags": ["testtag"]
        })
        result = await handle_get_tags(anki_wrapper, {})
        assert "testtag" in result


class TestMediaHandlers:
    """Test media-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_media_dir_path(self, anki_wrapper):
        """Test getMediaDirPath handler."""
        from api.handlers import handle_get_media_dir_path
        result = await handle_get_media_dir_path(anki_wrapper, {})
        assert result is not None
        assert len(result) > 0


class TestDispatch:
    """Test dispatch function."""

    @pytest.mark.asyncio
    async def test_dispatch_unknown_action(self, anki_wrapper):
        """Test dispatch with unknown action."""
        from api.handlers import dispatch
        with pytest.raises(ValueError, match="Unsupported action"):
            await dispatch("unknownAction", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_dispatch_valid_action(self, anki_wrapper):
        """Test dispatch with valid action."""
        from api.handlers import dispatch
        result = await dispatch("deckNames", {}, anki_wrapper)
        assert isinstance(result, list)


class TestSyncHandlers:
    """Test sync-related handlers."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get("ANKICONNECT_ANKIWEB_USER"),
        reason="ANKICONNECT_ANKIWEB_USER not set"
    )
    async def test_handle_sync_status(self, anki_wrapper):
        """Test syncStatus handler."""
        from api.handlers import handle_sync_status
        result = await handle_sync_status(anki_wrapper, {})
        assert "server" in result

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get("ANKICONNECT_ANKIWEB_USER"),
        reason="ANKICONNECT_ANKIWEB_USER not set"
    )
    async def test_handle_sync_media(self, anki_wrapper):
        """Test syncMedia handler."""
        from api.handlers import handle_sync_media
        result = await handle_sync_media(anki_wrapper, {})
        assert result is not None