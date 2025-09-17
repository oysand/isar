from typing import TYPE_CHECKING, Callable, Optional

from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
from isar.models.events import Event, EventTimeoutError
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_mission_event_handler(
    state_machine: "StateMachine",
    event: Event[Mission],
    response: Event[MissionStartResponse],
) -> Optional[Callable]:
    mission: Optional[Mission] = event.consume_event()
    if mission:
        if not state_machine.battery_level_is_above_mission_start_threshold():
            try:
                response.trigger_event(
                    MissionStartResponse(
                        mission_id=mission.id,
                        mission_started=False,
                        mission_not_started_reason="Robot battery too low",
                    ),
                    timeout=1,  # This conflict can happen if two API requests are received at the same time
                )
            except EventTimeoutError:
                pass
            return None
        state_machine.start_mission(mission=mission)
        return state_machine.request_mission_start  # type: ignore
    return None


def return_home_event_handler(
    state_machine: "StateMachine", event: Event[bool]
) -> Optional[Callable]:
    if event.consume_event():
        state_machine.events.api_requests.return_home.response.put(True)
        return state_machine.request_return_home  # type: ignore
    return None


def stop_mission_event_handler(
    state_machine: "StateMachine", event: Event[str]
) -> Optional[Callable]:
    mission_id: str = event.consume_event()
    if mission_id is not None:
        if state_machine.current_mission.id == mission_id or mission_id == "":
            return state_machine.stop  # type: ignore
        else:
            state_machine.events.api_requests.stop_mission.response.put(
                ControlMissionResponse(
                    mission_id=mission_id,
                    mission_status=state_machine.current_mission.status,
                    mission_not_found=True,
                    task_id=state_machine.current_task.id,
                    task_status=state_machine.current_task.status,
                )
            )
    return None


def mission_started_event_handler(
    state_machine: "StateMachine",
    event: Event[bool],
) -> Optional[Callable]:
    if event.consume_event():
        state_machine.mission_ongoing = True
    return None


def mission_failed_event_handler(
    state_machine: "StateMachine",
    event: Event[Optional[ErrorMessage]],
) -> Optional[Callable]:
    mission_failed: Optional[ErrorMessage] = event.consume_event()
    if mission_failed is not None:
        state_machine.logger.warning(
            f"Failed to initiate mission "
            f"{str(state_machine.current_mission.id)[:8]} because: "
            f"{mission_failed.error_description}"
        )
        state_machine.current_mission.error_message = ErrorMessage(
            error_reason=mission_failed.error_reason,
            error_description=mission_failed.error_description,
        )
        return state_machine.mission_failed_to_start  # type: ignore
    return None


def task_status_failed_event_handler(
    state_machine: "StateMachine",
    handle_task_completed: Callable[[TaskStatus], Callable],
    event: Event[Optional[ErrorMessage]],
) -> Optional[Callable]:
    if not state_machine.mission_ongoing:
        return None

    task_failure: Optional[ErrorMessage] = event.consume_event()
    if task_failure is not None:
        if state_machine.current_task is None:
            state_machine.logger.warning(
                "Received task status failed event when no task was running"
            )
            return None
        state_machine.awaiting_task_status = False
        state_machine.current_task.error_message = task_failure
        state_machine.logger.error(
            f"Monitoring task {state_machine.current_task.id[:8]} failed "
            f"because: {task_failure.error_description}"
        )
        return _handle_new_task_status(
            state_machine, handle_task_completed, TaskStatus.Failed
        )

    elif (
        not state_machine.awaiting_task_status
        and state_machine.current_task is not None
    ):
        state_machine.events.state_machine_events.task_status_request.trigger_event(
            state_machine.current_task.id,
        )
        state_machine.awaiting_task_status = True
    return None


def task_status_event_handler(
    state_machine: "StateMachine",
    handle_task_completed: Callable[[TaskStatus], Callable],
    event: Event[Optional[TaskStatus]],
) -> Optional[Callable]:
    if not state_machine.mission_ongoing:
        return None

    status: Optional[TaskStatus] = event.consume_event()
    if status is not None:
        state_machine.awaiting_task_status = False
        return _handle_new_task_status(state_machine, handle_task_completed, status)

    elif (
        not state_machine.awaiting_task_status
        and state_machine.current_task is not None
    ):
        state_machine.events.state_machine_events.task_status_request.trigger_event(
            state_machine.current_task.id,
        )
        state_machine.awaiting_task_status = True
    return None


def _handle_new_task_status(
    state_machine: "StateMachine",
    handle_task_completed: Callable[[TaskStatus], Callable],
    status: TaskStatus,
) -> Optional[Callable]:
    if state_machine.current_task is None:
        state_machine.iterate_current_task()

    state_machine.current_task.status = status

    if state_machine.current_task.is_finished():
        state_machine.report_task_status(state_machine.current_task)
        state_machine.publish_task_status(task=state_machine.current_task)

        return handle_task_completed(status)
    return None


def robot_status_failed_event_handler(
    state_machine: "StateMachine",
    event: Event[Optional[ErrorMessage]],
) -> Optional[Callable]:
    robot_status_failure: Optional[ErrorMessage] = event.consume_event()

    if robot_status_failure is None:
        return None

    state_machine.logger.error(
        f"Robot status failed because: {robot_status_failure.error_description}"
    )
    state_machine.awaiting_robot_status = False
    return state_machine.robot_status_unknown  # type: ignore


def robot_status_event_handler(
    state_machine: "StateMachine",
    event: Event[Optional[RobotStatus]],
) -> Optional[Callable]:
    status: Optional[RobotStatus] = event.consume_event()
    if status is not None:
        state_machine.awaiting_robot_status = False
        return _handle_new_robot_status(state_machine, status)

    elif not state_machine.awaiting_robot_status:
        state_machine.events.state_machine_events.robot_status_request.trigger_event(
            True
        )
        state_machine.awaiting_robot_status = True
    return None


def _handle_new_robot_status(
    state_machine: "StateMachine",
    status: RobotStatus,
) -> Optional[Callable]:
    if status == RobotStatus.Home:
        if state_machine.is_home():
            return None
        return state_machine.robot_is_home  # type: ignore
    elif status == RobotStatus.Available:
        if state_machine.is_robot_standing_still():
            return None
        return state_machine.robot_is_standing_still  # type: ignore
    elif status == RobotStatus.BlockedProtectiveStop:
        if state_machine.is_blocked_protective_stop():
            return None
        return state_machine.robot_is_blocked_protective_stop  # type: ignore
    elif status == RobotStatus.Offline:
        if state_machine.is_offline():
            return None
        return state_machine.robot_is_offline  # type: ignore

    return state_machine.robot_status_unknown  # type: ignore
