import logging
from http import HTTPStatus

from injector import inject

from isar.config import config
from isar.models.communication.messages import StopMessage, StopMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities


class StopMission():
    @inject 
    def __init__(self, queues: Queues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.queues = queues
        self.queue_timeout: int = config.getint("mission", "eqrobot_queue_timeout")
    def post(self):

        self.queues.stop_mission.input.put(True)

        try:
            message: StopMessage = QueueUtilities.check_queue(
                self.queues.stop_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            response = StopMissionMessages.queue_timeout(), HTTPStatus.REQUEST_TIMEOUT
            self.logger.error(response)
            return response
        response = message, HTTPStatus.OK
        self.logger.info(response)
        return response
