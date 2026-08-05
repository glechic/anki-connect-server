from typing import NotRequired, TypedDict

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


class CardAnswerInput(TypedDict):
    cardId: int
    ease: int
