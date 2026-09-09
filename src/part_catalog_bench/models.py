from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExerciseStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionCategory(StrEnum):
    COMPONENT_IDENTIFICATION = "component_identification"
    SPATIAL_RELATIONSHIP = "spatial_relationship"
    CATALOG_NOTATION = "catalog_notation"
    ROUTED_SYSTEM_TRACING = "routed_system_tracing"
    CROSS_VIEW_MATCHING = "cross_view_matching"
    ASSEMBLY_STACK_TRACING = "assembly_stack_tracing"
    QUANTITY_REASONING = "quantity_reasoning"
    FUNCTIONAL_REASONING = "functional_reasoning"


class AnswerType(StrEnum):
    PART_NUMBER = "part_number"
    INTEGER = "integer"
    DATE = "date"
    BOOLEAN = "boolean"
    ORDERED_LIST = "ordered_list"
    ORDERED_PART_PATH = "ordered_part_path"
    UNORDERED_SET = "unordered_set"
    SHORT_TEXT = "short_text"
    COMPOUND = "compound"


class PartNumberFamily(StrEnum):
    BASIC = "basic"
    SERVICE = "service"
    ENGINEERING = "engineering"
    STANDARD = "standard"
    AUTO = "auto"


class PartPathStep(BaseModel):
    """One ordered traversal through one physical instance of a catalog part."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    part_number: str = Field(min_length=1)
    instance: int = Field(ge=1)
    pass_number: int = Field(alias="pass", serialization_alias="pass", ge=1)


class RubricCriterionGraderType(StrEnum):
    SEMANTIC = "semantic"
    CONTAINS_PART_NUMBER = "contains_part_number"


class RubricCriterionGrader(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RubricCriterionGraderType = RubricCriterionGraderType.SEMANTIC
    value: str | None = None
    family: PartNumberFamily = PartNumberFamily.AUTO

    @model_validator(mode="after")
    def require_matcher_value(self) -> RubricCriterionGrader:
        if self.type == RubricCriterionGraderType.CONTAINS_PART_NUMBER and not self.value:
            raise ValueError("contains_part_number rubric graders require a value")
        if self.type == RubricCriterionGraderType.SEMANTIC and self.value is not None:
            raise ValueError("semantic rubric graders do not accept a value")
        return self


class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    description: str = Field(min_length=3)
    points: float = Field(gt=0)
    required: bool = True
    grader: RubricCriterionGrader = Field(default_factory=RubricCriterionGrader)


class RubricCalibrationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(min_length=1)
    expected_score: float = Field(ge=0, le=1)


class RubricGradingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["rubric"] = "rubric"
    criteria: list[RubricCriterion] = Field(min_length=1)
    calibration_cases: list[RubricCalibrationCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_criterion_ids(self) -> RubricGradingSpec:
        ids = [criterion.id for criterion in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric criterion IDs must be unique")
        return self


class AnswerSpec(BaseModel):
    type: AnswerType
    value: Any = None
    aliases: list[Any] = Field(default_factory=list)
    family: PartNumberFamily = PartNumberFamily.AUTO
    item_type: AnswerType | None = None
    item_family: PartNumberFamily = PartNumberFamily.AUTO
    fields: dict[str, AnswerSpec] = Field(default_factory=dict)
    grading: RubricGradingSpec | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> AnswerSpec:
        if self.type == AnswerType.COMPOUND:
            if not self.fields:
                raise ValueError("compound answers require at least one field")
        elif self.value is None:
            raise ValueError(f"{self.type} answers require a value")
        if self.type in {AnswerType.ORDERED_LIST, AnswerType.UNORDERED_SET}:
            if not isinstance(self.value, list):
                raise ValueError(f"{self.type} answer value must be a list")
        if self.type == AnswerType.ORDERED_PART_PATH:
            if not isinstance(self.value, list) or not self.value:
                raise ValueError("ordered_part_path answer value must be a non-empty list")
            steps = [PartPathStep.model_validate(item) for item in self.value]
            seen: set[tuple[str, int, int]] = set()
            instances: dict[str, set[int]] = {}
            pass_counts: dict[tuple[str, int], int] = {}
            for step in steps:
                number = "".join(
                    character
                    for character in step.part_number.strip().upper()
                    if character not in " -"
                )
                key = (number, step.instance, step.pass_number)
                if key in seen:
                    raise ValueError(f"duplicate ordered_part_path step {key}")
                seen.add(key)
                known_instances = instances.setdefault(number, set())
                if step.instance not in known_instances:
                    expected_instance = len(known_instances) + 1
                    if step.instance != expected_instance:
                        raise ValueError(
                            f"part {number} new instances must appear in order; "
                            f"expected instance {expected_instance}"
                        )
                    known_instances.add(step.instance)
                pass_key = (number, step.instance)
                expected_pass = pass_counts.get(pass_key, 0) + 1
                if step.pass_number != expected_pass:
                    raise ValueError(
                        f"part {number} instance {step.instance} passes must appear in order; "
                        f"expected pass {expected_pass}"
                    )
                pass_counts[pass_key] = expected_pass
            self.value = [step.model_dump(mode="json", by_alias=True) for step in steps]
        if self.grading is not None and self.type != AnswerType.SHORT_TEXT:
            raise ValueError("rubric grading is supported only for short_text answers")
        return self


class Evidence(BaseModel):
    catalog_refs: list[str] = Field(default_factory=list)
    note: str | None = None


class NormalizedRect(BaseModel):
    """A top-left-origin rectangle expressed as fractions of the full page."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def stay_on_page(self) -> NormalizedRect:
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("normalized rectangle extends beyond the page")
        return self


class NormalizedPoint(BaseModel):
    """A point expressed as fractions of the full page from its top-left corner."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class RegionAnnotation(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    label: str = Field(min_length=1, max_length=12)
    page_ref: str = Field(min_length=3)
    rect: NormalizedRect | None = None
    polygon: list[NormalizedPoint] | None = None
    description: str | None = None
    color: str = Field(default="#ffcc00", pattern=r"^#[0-9a-fA-F]{6}$")

    @model_validator(mode="after")
    def require_one_geometry(self) -> RegionAnnotation:
        if (self.rect is None) == (self.polygon is None):
            raise ValueError("annotation requires exactly one of rect or polygon")
        if self.polygon is not None:
            unique = {(point.x, point.y) for point in self.polygon}
            if len(self.polygon) < 3 or len(unique) < 3:
                raise ValueError("annotation polygon requires at least three distinct points")
            doubled_area = abs(
                sum(
                    point.x * self.polygon[(index + 1) % len(self.polygon)].y
                    - point.y * self.polygon[(index + 1) % len(self.polygon)].x
                    for index, point in enumerate(self.polygon)
                )
            )
            if doubled_area < 0.000002:
                raise ValueError("annotation polygon requires a non-zero enclosed area")
        return self


class ContextPage(BaseModel):
    ref: str = Field(min_length=3)
    crop: NormalizedRect | None = None
    note: str | None = None


class Question(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    prompt: str = Field(min_length=3)
    category: QuestionCategory
    difficulty: Difficulty
    difficulty_note: str | None = None
    annotations: list[RegionAnnotation] = Field(default_factory=list)
    answer: AnswerSpec
    evidence: Evidence = Field(default_factory=Evidence)
    weight: float = Field(default=1.0, gt=0)


class ExerciseContext(BaseModel):
    catalog_refs: list[str] = Field(default_factory=list)
    pages: list[ContextPage] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    annotations: list[RegionAnnotation] = Field(default_factory=list)
    note: str | None = None

    @model_validator(mode="after")
    def require_context(self) -> ExerciseContext:
        if not self.catalog_refs and not self.pages and not self.assets:
            raise ValueError("context requires at least one catalog reference or asset")
        refs = self.catalog_refs + [page.ref for page in self.pages]
        if len(refs) != len(set(refs)):
            raise ValueError("context catalog references must be unique")
        return self


class Exercise(BaseModel):
    schema_version: int = 1
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    status: ExerciseStatus
    title: str
    source_id: str
    context: ExerciseContext
    questions: list[Question] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_removed_vehicle_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict) and "vehicle" in data:
            raise ValueError(
                "vehicle metadata is no longer supported; put relevant details in the "
                "question prompt"
            )
        return data

    @model_validator(mode="after")
    def unique_question_ids(self) -> Exercise:
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question IDs must be unique within an exercise")
        refs = set(self.context.catalog_refs) | {page.ref for page in self.context.pages}
        annotations = [*self.context.annotations]
        for question in self.questions:
            annotations.extend(question.annotations)
        unknown = sorted({annotation.page_ref for annotation in annotations} - refs)
        if unknown:
            raise ValueError(f"annotations refer to pages outside exercise context: {unknown}")
        shared_keys = {
            (annotation.page_ref, annotation.id) for annotation in self.context.annotations
        }
        if len(shared_keys) != len(self.context.annotations):
            raise ValueError("shared annotation IDs must be unique per page")
        for question in self.questions:
            question_keys = [
                (annotation.page_ref, annotation.id) for annotation in question.annotations
            ]
            if len(question_keys) != len(set(question_keys)) or shared_keys.intersection(
                question_keys
            ):
                raise ValueError(
                    f"annotation IDs must be unique per page in question {question.id!r}"
                )
        return self


class Prediction(BaseModel):
    exercise_id: str
    question_id: str
    answer: Any = None
    raw_response: str | None = None
    error: str | None = None
    provider: str | None = None
    requested_model: str | None = None
    response_model: str | None = None
    provider_response: dict[str, Any] = Field(default_factory=dict)
    grading: dict[str, Any] | None = None
    latency_seconds: float | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    prompt_sha256: str | None = None
    asset_sha256: dict[str, str] = Field(default_factory=dict)
    reused_from: dict[str, Any] | None = None


def load_exercise(path: Path) -> Exercise:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Exercise.model_validate(data)


def load_exercises(path: Path) -> list[tuple[Path, Exercise]]:
    paths = (
        [path]
        if path.is_file()
        else sorted(
            item
            for item in [*path.rglob("*.yaml"), *path.rglob("*.yml")]
            if ".trash" not in item.parts
        )
    )
    return [(item, load_exercise(item)) for item in paths]
