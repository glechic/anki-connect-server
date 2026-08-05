from typing import Any, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

type JsonPrimitive = bool | float | int | str | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class NoteInput(TypedDict):
    deckName: str
    modelName: str
    fields: dict[str, str]
    tags: NotRequired[list[str]]


class CardTemplateInput(TypedDict):
    Name: str
    Front: str
    Back: str


class ModelTemplateUpdate(TypedDict):
    name: str
    templates: dict[str, dict[str, str]]


class ModelStylingUpdate(TypedDict):
    name: str
    css: str


# ---------------------------------------------------------------------------
# Pydantic request-param models.
#
# Field names use the exact AnkiConnect wire casing (camelCase where the
# protocol uses camelCase) so the handler can be invoked directly with the
# validated model and so `Model(**params)` works without translation.
# ---------------------------------------------------------------------------


class _BaseParams(BaseModel):
    """Common base: forbid unknown keys so typos in action params surface as
    ValidationError instead of silently being ignored."""

    model_config = ConfigDict(extra="forbid")


class EmptyParams(_BaseParams):
    """For actions that take no parameters (version, deckNames, ...)."""


class CredentialsParams(_BaseParams):
    """Shared by sync / syncStatus / syncMedia."""

    endpoint: str | None = None
    username: str | None = None
    password: str | None = None


class GetDecksParams(_BaseParams):
    cards: list[int] = Field(default_factory=list)


class CreateDeckParams(_BaseParams):
    deck: str


class ChangeDeckParams(_BaseParams):
    cards: list[int] = Field(default_factory=list)
    deck: str = ""


class DeleteDecksParams(_BaseParams):
    decks: list[str] = Field(default_factory=list)
    cardsToo: bool = False


class GetDeckConfigParams(_BaseParams):
    deck: str = ""


class SaveDeckConfigParams(_BaseParams):
    config: dict[str, JsonValue] = Field(default_factory=dict)


class SetDeckConfigIdParams(_BaseParams):
    decks: list[str] = Field(default_factory=list)
    configId: int = 1


class CloneDeckConfigIdParams(_BaseParams):
    name: str = ""
    cloneFrom: int = 1


class RemoveDeckConfigIdParams(_BaseParams):
    configId: int = 1


class ModelNameParams(_BaseParams):
    """Shared by actions that only need a modelName."""

    modelName: str = ""


class CreateModelParams(_BaseParams):
    modelName: str = ""
    inOrderFields: list[str] = Field(default_factory=list)
    cardTemplates: list[dict[str, str]] = Field(default_factory=list)
    css: str = ""
    isCloze: bool = False


class ModelTemplateUpdateParams(_BaseParams):
    model: ModelTemplateUpdate


class ModelStylingUpdateParams(_BaseParams):
    model: ModelStylingUpdate


class NoteFieldUpdate(BaseModel):
    """A single field update inside updateNoteFields."""

    model_config = ConfigDict(extra="forbid")
    id: int
    fields: dict[str, str] = Field(default_factory=dict)


class AddNoteParams(_BaseParams):
    note: NoteInput


class AddNotesParams(_BaseParams):
    notes: list[NoteInput]


class UpdateNoteFieldsParams(_BaseParams):
    note: NoteFieldUpdate


class NotesIdsParams(_BaseParams):
    """Shared by actions keyed on a list of note ids."""

    notes: list[int] = Field(default_factory=list)


class AddTagsParams(_BaseParams):
    notes: list[int] = Field(default_factory=list)
    tags: str = ""


class FindNotesParams(_BaseParams):
    query: str


class FindCardsParams(_BaseParams):
    query: str


class CardsIdsParams(_BaseParams):
    """Shared by actions keyed on a list of card ids."""

    cards: list[int] = Field(default_factory=list)


class GetIntervalsParams(_BaseParams):
    cards: list[int] = Field(default_factory=list)
    complete: bool = False


class StoreMediaFileParams(_BaseParams):
    filename: str = ""
    data: str = ""


class FilenameParams(_BaseParams):
    """Shared by retrieveMediaFile / deleteMediaFile."""

    filename: str = ""


class ImportPackageParams(_BaseParams):
    path: str = ""


class ExportPackageParams(_BaseParams):
    deck: str = ""
    path: str = ""
    includeSched: bool = False


class MultiParams(_BaseParams):
    # actions is a list of heterogeneous action objects; the handler validates
    # each entry's shape per-action so it can report per-action errors instead
    # of failing the whole batch on one bad entry.
    actions: list[Any] = Field(default_factory=list)
