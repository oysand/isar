
from fastapi import APIRouter
from fastapi.param_functions import Depends
from injector import Inject, Injector, inject

from isar.apis.schedule.start_echo_mission import StartEchoMission
from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission

from .drive_to import DriveTo


def create_scheduler_router(injector : Injector) -> APIRouter:

    start_mission = injector.get(StartMission)
    start_echo_mission = injector.get(StartEchoMission)
    stop_mission = injector.get(StopMission)
    drive_to = injector.get(DriveTo)

    router = APIRouter(tags=["Scheduler"])

    router.add_api_route('/startmission', start_mission.get, methods=["GET"])
    router.add_api_route('/startechomission', start_echo_mission.get, methods=["GET"])
    router.add_api_route('/stopmission', stop_mission.post, methods=["POST"])
    router.add_api_route('/driveto', drive_to.get, methods=["GET"])

    return router

