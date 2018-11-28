from enum import Enum, auto

# TODO
# THIS IS TAKEN FROM GOLEM CORE
# WILL BREAK IN CASE OF CHANGES IN GOLEM CORE
# DEFINE A SEPARATE MODULE FOR GOLEM DATA STRUCTURES

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