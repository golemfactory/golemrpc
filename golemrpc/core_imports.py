from enum import Enum, auto, IntEnum


# TODO
# Imported from golem core
# Will break on changes in golem core.
# Define a separate module for golem data structures


class Operation(Enum):

    @staticmethod
    def task_related() -> bool:
        return False

    @staticmethod
    def subtask_related() -> bool:
        return False

    @staticmethod
    def unnoteworthy() -> bool:
        return False

    def is_completed(self) -> bool:
        pass


class TaskOp(Operation):
    """Ops that result in storing of task level information"""

    @staticmethod
    def task_related() -> bool:
        return True

    def is_completed(self) -> bool:
        return self in [
            TaskOp.FINISHED,
            TaskOp.NOT_ACCEPTED,
            TaskOp.TIMEOUT,
            TaskOp.RESTARTED,
            TaskOp.ABORTED]

    WORK_OFFER_RECEIVED = auto()
    CREATED = auto()
    STARTED = auto()
    FINISHED = auto()
    NOT_ACCEPTED = auto()
    TIMEOUT = auto()
    RESTARTED = auto()
    ABORTED = auto()
    RESTORED = auto()


class SubtaskOp(Operation):
    """Ops that result in storing of subtask level information;
    subtask_id needs to be set for them"""

    @staticmethod
    def subtask_related() -> bool:
        return True

    ASSIGNED = auto()
    RESULT_DOWNLOADING = auto()
    NOT_ACCEPTED = auto()
    FINISHED = auto()
    FAILED = auto()
    TIMEOUT = auto()
    RESTARTED = auto()
    VERIFYING = auto()

    def is_completed(self) -> bool:
        return self not in (
            SubtaskOp.ASSIGNED,
            SubtaskOp.RESULT_DOWNLOADING,
            SubtaskOp.RESTARTED,
            SubtaskOp.VERIFYING
        )


class VerificationMethod():
    NO_VERIFICATION = "None"
    EXTERNALLY_VERIFIED = "External"


class SubtaskVerificationState(IntEnum):
    UNKNOWN_SUBTASK = 0
    WAITING = 1
    IN_PROGRESS = 2
    VERIFIED = 3
    WRONG_ANSWER = 4
    NOT_SURE = 5
    TIMEOUT = 6
