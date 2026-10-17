from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

type JsonPrimitive = bool | float | int | str | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class NoteInput(TypedDict):
    deckName: str
    modelName: str
    fields: dict[str, str]
    tags: NotRequired[list[str]]
    options: NotRequired[dict[str, Any]]
    audio: NotRequired[Any]
    video: NotRequired[Any]
    picture: NotRequired[Any]


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


class ApiReflectParams(_BaseParams):
    """For apiReflect: which scopes to reflect, optionally filtered actions."""

    scopes: list[str] = Field(default_factory=list)
    actions: list[str] | None = None


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


class DeckIdParams(_BaseParams):
    """For actions keyed on a single deck id."""

    deckId: int


class ModelIdParams(_BaseParams):
    """For actions keyed on a single model id."""

    modelId: int


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


class ModelFieldAddParams(_BaseParams):
    modelName: str
    fieldName: str
    index: int | None = None


class ModelFieldRemoveParams(_BaseParams):
    modelName: str
    fieldName: str


class ModelFieldRenameParams(_BaseParams):
    modelName: str
    oldFieldName: str
    newFieldName: str


class ModelFieldRepositionParams(_BaseParams):
    modelName: str
    fieldName: str
    index: int


class ModelFieldSetFontParams(_BaseParams):
    modelName: str
    fieldName: str
    font: str


class ModelFieldSetFontSizeParams(_BaseParams):
    modelName: str
    fieldName: str
    fontSize: int


class ModelFieldSetDescriptionParams(_BaseParams):
    modelName: str
    fieldName: str
    description: str


class ModelTemplateAddParams(_BaseParams):
    modelName: str
    template: CardTemplateInput


class ModelTemplateRemoveParams(_BaseParams):
    modelName: str
    templateName: str


class ModelTemplateRenameParams(_BaseParams):
    modelName: str
    oldTemplateName: str
    newTemplateName: str


class ModelTemplateRepositionParams(_BaseParams):
    modelName: str
    templateName: str
    index: int


class FindAndReplaceInModelsParams(_BaseParams):
    # An empty modelName means every model in the collection.
    modelName: str = ""
    findText: str
    replaceText: str
    front: bool = True
    back: bool = True
    css: bool = True


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


class NoteUpdate(_BaseParams):
    """The note object of updateNote: id plus optional fields and/or tags."""

    model_config = ConfigDict(extra="forbid")
    id: int
    fields: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class UpdateNoteParams(_BaseParams):
    note: NoteUpdate


class NotesIdsParams(_BaseParams):
    """Shared by actions keyed on a list of note ids."""

    notes: list[int] = Field(default_factory=list)


class AddTagsParams(_BaseParams):
    notes: list[int] = Field(default_factory=list)
    tags: str = ""


class ReplaceTagsParams(_BaseParams):
    # replaceTags uses the upstream AnkiConnect wire names (snake_case).
    notes: list[int] = Field(default_factory=list)
    tag_to_replace: str
    replace_with_tag: str


class ReplaceTagsInAllNotesParams(_BaseParams):
    # replaceTagsInAllNotes uses the upstream AnkiConnect wire names (snake_case).
    tag_to_replace: str
    replace_with_tag: str


class GetNoteTagsParams(_BaseParams):
    """For getNoteTags, keyed on a single note id."""

    note: int


class UpdateNoteTagsParams(_BaseParams):
    # updateNoteTags uses the upstream AnkiConnect wire names (snake_case).
    note: int
    tags: list[str] | str


class FindNotesParams(_BaseParams):
    query: str


class FindCardsParams(_BaseParams):
    query: str


class CardsIdsParams(_BaseParams):
    """Shared by actions keyed on a list of card ids."""

    cards: list[int] = Field(default_factory=list)


class SuspendedParams(_BaseParams):
    """For the suspended action, keyed on a single card id."""

    card: int


class GetIntervalsParams(_BaseParams):
    cards: list[int] = Field(default_factory=list)
    complete: bool = False


class CardAnswer(BaseModel):
    """A single card answer inside answerCards (1=Again, 2=Hard, 3=Good, 4=Easy)."""

    model_config = ConfigDict(extra="forbid")
    cardId: int
    ease: Literal[1, 2, 3, 4]


class AnswerCardsParams(_BaseParams):
    answers: list[CardAnswer] = Field(default_factory=list)


class SetEaseFactorsParams(_BaseParams):
    cards: list[int] = Field(default_factory=list)
    easeFactors: list[int] = Field(default_factory=list)


class SetSpecificValueOfCardParams(_BaseParams):
    # warning_check uses the upstream AnkiConnect wire name (snake_case).
    card: int
    keys: list[str] = Field(default_factory=list)
    newValues: list[Any] = Field(default_factory=list)
    warning_check: bool = False


class CardReviewsParams(_BaseParams):
    """For cardReviews, keyed on a deck name and a starting review id."""

    deck: str
    startID: int


class DeckNameParams(_BaseParams):
    """For actions keyed on a single deck name (getLatestReviewID)."""

    deck: str = ""


class InsertReviewsParams(_BaseParams):
    """For insertReviews: raw revlog rows of 9 integers each."""

    reviews: list[list[int]] = Field(default_factory=list)


class GetDeckStatsParams(_BaseParams):
    decks: list[str] = Field(default_factory=list)


class GetCollectionStatsHTMLParams(_BaseParams):
    wholeCollection: bool = True


class GetMediaFilesNamesParams(_BaseParams):
    pattern: str = "*"


class StoreMediaFileParams(_BaseParams):
    """Upstream Anki-Connect accepts exactly one of data/url/path."""

    filename: str = ""
    data: str = ""
    url: str = ""
    path: str = ""


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
