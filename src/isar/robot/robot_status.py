import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.events import RobotServiceEvents
from isar.models.communication.queues.queue_utils import (
    trigger_event,
    update_shared_state,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
)
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):
    def __init__(
        self,
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        Thread.__init__(self, name="Robot status thread")

    def stop(self) -> None:
        return

    def run(self):
        failed_robot_status_error: Optional[ErrorMessage] = None
        request_status_failure_counter: int = 0

        while (
            request_status_failure_counter
            < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        ):
            if self.signal_thread_quitting.is_set():
                return

            try:
                robot_status = self.robot.robot_status()
                trigger_event(
                    self.robot_service_events.robot_status_updated, robot_status
                )
                return
            except (
                RobotCommunicationTimeoutException,
                RobotCommunicationException,
            ) as e:
                request_status_failure_counter += 1
                self.logger.error(
                    f"Failed to get robot status "
                    f"{request_status_failure_counter} times because: "
                    f"{e.error_description}"
                )

                failed_robot_status_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                continue
            except RobotException as e:
                failed_robot_status_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

        trigger_event(
            self.robot_service_events.robot_status_failed,
            failed_robot_status_error,
        )
