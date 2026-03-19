import os
from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from config import Config
from anki_wrapper import AnkiWrapper


mcp = FastMCP("Anki Connect MCP Server")

_collection_path = os.environ.get("ANKI_COLLECTION_PATH", "")
_wrapper: Optional[AnkiWrapper] = None


def get_wrapper() -> AnkiWrapper:
    global _wrapper
    if _wrapper is None:
        Config.validate()
        _wrapper = AnkiWrapper(Config.COLLECTION_PATH)
    return _wrapper


@mcp.tool
def get_deck_names() -> list[str]:
    """Get all deck names in the collection."""
    return get_wrapper().deck_names()


@mcp.tool
def get_deck_names_and_ids() -> dict[str, int]:
    """Get all deck names with their IDs."""
    return get_wrapper().deck_names_and_ids()


@mcp.tool
def create_deck(deck: str) -> int:
    """Create a new deck with the given name."""
    return get_wrapper().create_deck(deck)


@mcp.tool
def delete_decks(decks: list[str], cards_too: bool = False) -> bool:
    """Delete one or more decks. Set cardsToo to True to also delete cards."""
    get_wrapper().delete_decks(decks, cards_too)
    return True


@mcp.tool
def get_model_names() -> list[str]:
    """Get all note model names."""
    return get_wrapper().model_names()


@mcp.tool
def get_model_field_names(model_name: str) -> list[str]:
    """Get all field names for a specific model."""
    return get_wrapper().model_field_names(model_name)


@mcp.tool
def add_note(deck_name: str, model_name: str, fields: dict[str, str], tags: list[str] = None) -> Optional[int]:
    """Add a new note to the collection.
    
    Args:
        deck_name: Name of the deck to add the note to
        model_name: Name of the note model (e.g., "Basic", "Cloze")
        fields: Dictionary of field names to values
        tags: Optional list of tags to add
    """
    note = {
        "deckName": deck_name,
        "modelName": model_name,
        "fields": fields,
    }
    if tags:
        note["tags"] = tags
    return get_wrapper().add_note(note)


@mcp.tool
def find_notes(query: str) -> list[int]:
    """Find notes matching the given search query.
    
    Examples of queries:
    - "deck:Default" - notes in Default deck
    - "tag:important" - notes with tag "important"
    - "note:Basic" - notes using Basic model
    """
    return get_wrapper().find_notes(query)


@mcp.tool
def get_notes_info(notes: list[int]) -> list[dict]:
    """Get detailed information about specific notes."""
    return get_wrapper().notes_info(notes)


@mcp.tool
def delete_notes(notes: list[int]) -> bool:
    """Delete notes by their IDs."""
    get_wrapper().delete_notes(notes)
    return True


@mcp.tool
def find_cards(query: str) -> list[int]:
    """Find cards matching the given search query."""
    return get_wrapper().find_cards(query)


@mcp.tool
def get_cards_info(cards: list[int]) -> list[dict]:
    """Get detailed information about specific cards."""
    return get_wrapper().cards_info(cards)


@mcp.tool
def suspend_cards(cards: list[int]) -> bool:
    """Suspend one or more cards."""
    return get_wrapper().suspend(cards)


@mcp.tool
def unsuspend_cards(cards: list[int]) -> bool:
    """Unsuspend one or more cards."""
    return get_wrapper().unsuspend(cards)


@mcp.tool
def are_suspended(cards: list[int]) -> list[bool]:
    """Check if cards are suspended."""
    return get_wrapper().are_suspended(cards)


@mcp.tool
def are_due(cards: list[int]) -> list[bool]:
    """Check if cards are due for review."""
    return get_wrapper().are_due(cards)


@mcp.tool
def get_card_intervals(cards: list[int], complete: bool = False) -> list[Any]:
    """Get intervals for cards. Set complete=True for all intervals."""
    return get_wrapper().get_intervals(cards, complete)


@mcp.tool
def get_all_tags() -> list[str]:
    """Get all tags in the collection."""
    return get_wrapper().get_tags()


@mcp.tool
def add_tags(notes: list[int], tags: str) -> bool:
    """Add tags to notes. Tags should be space-separated."""
    get_wrapper().add_tags(notes, tags)
    return True


@mcp.tool
def remove_tags(notes: list[int], tags: str) -> bool:
    """Remove tags from notes. Tags should be space-separated."""
    get_wrapper().remove_tags(notes, tags)
    return True


@mcp.tool
def get_media_dir_path() -> str:
    """Get the path to the media directory."""
    return get_wrapper().get_media_dir_path()


@mcp.tool
def store_media_file(filename: str, data: str) -> bool:
    """Store a media file. Data should be base64 encoded."""
    get_wrapper().store_media_file(filename, data)
    return True


@mcp.tool
def retrieve_media_file(filename: str) -> Optional[str]:
    """Retrieve a media file. Returns base64 encoded data."""
    return get_wrapper().retrieve_media_file(filename)


@mcp.tool
def delete_media_file(filename: str) -> bool:
    """Delete a media file."""
    get_wrapper().delete_media_file(filename)
    return True


@mcp.tool
def import_package(path: str) -> dict:
    """Import an .apkg file."""
    return get_wrapper().import_package(path)


@mcp.tool
def export_package(deck: str, path: str, include_sched: bool = False) -> bool:
    """Export a deck to an .apkg file."""
    get_wrapper().export_package(deck, path, include_sched)
    return True


@mcp.tool
def sync() -> str:
    """Sync collection with AnkiWeb or custom sync server."""
    return get_wrapper().sync_to_ankiweb()


@mcp.tool
def sync_media() -> str:
    """Sync only media files with AnkiWeb."""
    return get_wrapper().sync_media_only()


@mcp.tool
def get_sync_status() -> dict:
    """Get sync status from AnkiWeb."""
    return get_wrapper().sync_status()


@mcp.tool
def get_api_version() -> int:
    """Get the AnkiConnect API version."""
    return 6


@mcp.tool
def change_deck(cards: list[int], deck: str) -> bool:
    """Move cards to a different deck."""
    get_wrapper().change_deck(cards, deck)
    return True


@mcp.tool
def cards_to_notes(cards: list[int]) -> list[int]:
    """Convert card IDs to note IDs."""
    return get_wrapper().cards_to_notes(cards)


@mcp.tool
def get_deck_config(deck: str) -> dict:
    """Get deck configuration."""
    return get_wrapper().get_deck_config(deck)


@mcp.tool
def get_model_templates(model_name: str) -> dict:
    """Get card templates for a model."""
    return get_wrapper().model_templates(model_name)


@mcp.tool
def get_model_styling(model_name: str) -> dict:
    """Get CSS styling for a model."""
    return get_wrapper().model_styling(model_name)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        mcp.run()
    else:
        mcp.run(transport="stdio")