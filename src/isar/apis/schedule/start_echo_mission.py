


import logging
from http import HTTPStatus
from typing import Optional

from fastapi.param_functions import Query
from injector import inject

from isar.models.communication.messages.start_message import (
    StartMessage,
    StartMissionMessages,
)
from isar.models.mission import Mission
from isar.services.service_connections.echo.echo_service import EchoServiceInterface
from isar.services.utilities.scheduling_utilities import SchedulingUtilities


class StartEchoMission:
    @inject
    def __init__(
        self,
        echo_service: EchoServiceInterface,
        scheduling_utilities: SchedulingUtilities,
        *args,
        **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.echo_service = echo_service
        self.scheduling_utilities = scheduling_utilities


    def get(self,
        mission_id: Optional[int] = Query(
        None,
        alias="ID",
        title="Mission ID",
        description="ID-number for predefined mission")
        ):
        mission: Mission = self.echo_service.get_mission(mission_id=mission_id)

        if mission is None:
            message: StartMessage = StartMissionMessages.mission_not_found()
            return message, HTTPStatus.NOT_FOUND

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            return response

        response = self.scheduling_utilities.start_mission(mission=mission)

        self.logger.info(response)
        return response
