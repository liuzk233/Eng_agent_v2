from enum import StrEnum


class StoryStyle(StrEnum):
    web_novel = "web_novel"
    science_fiction = "science_fiction"
    exam_reading = "exam_reading"


class GenerationStatus(StrEnum):
    queued = "queued"
    running = "running"
    reviewing = "reviewing"
    retrying = "retrying"
    completed = "completed"
    fallback_completed = "fallback_completed"
    failed_internal = "failed_internal"


class ReviewResult(StrEnum):
    passed = "passed"
    retry_required = "retry_required"
    fallback_accepted = "fallback_accepted"


class TargetWordSource(StrEnum):
    manual = "manual"
    library = "library"
