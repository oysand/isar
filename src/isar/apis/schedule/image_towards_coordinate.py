import logging
from typing import Optional

from fastapi import Depends, Query
from fastapi_utils.cbv import cbv

from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from models.geometry.frame import Frame
from models.geometry.position import Position
from models.planning.step import TakeImage


# Not implemented yet
class TakeImageOfObject:
    def __init__(self, scheduling_utilities: SchedulingUtilities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.scheduling_utilities = scheduling_utilities


    def get(self,
            x: Optional[float] = Query(
            None,
            alias="x-value",
            title="x-position",
            description="The target x coordinate",
            ),
        y: Optional[float] = Query(
            None, 
            alias="y-value",
            description="The target y coordinate",
            ),
        z: Optional[float] = Query(
            None, 
            alias="z-value",
            description="The target z coordinate",
            ),
        ):
        
        step: TakeImage = TakeImage(
            target=Position(x=x, y=y, z=z, frame=Frame.Robot)
        )
        mission: Mission = Mission([step])

        response = self.scheduling_utilities.start_mission(mission=mission)
        self.logger.info(response)
        return response


