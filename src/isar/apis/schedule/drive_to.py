import logging
from typing import Optional

from fastapi import Depends, Query
from fastapi_utils.cbv import cbv
from injector import inject

from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.pose import Pose
from models.geometry.position import Position
from models.planning.step import DriveToPose


class DriveTo:
    @inject
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
        q: Optional[list] = Query(
            [0,0,0,1],
            alias="quaternion",
            description="Target orientation as a quaternion (x,y,z,w)",
            )
        ):

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            return response
        


        position: Position = Position(x=x, y=y, z=z, frame=Frame.Robot)
        orientation: Orientation = Orientation(x=q[0],y=q[1],z=q[2],w=q[3], frame=Frame.Robot)
        pose: Pose = Pose(position=position, orientation=orientation, frame = Frame.Robot)
        
        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission([step])

        response = self.scheduling_utilities.start_mission(mission=mission)
        self.logger.info(response)
        return response


