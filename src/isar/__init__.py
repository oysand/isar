
import logging
import logging.config
from threading import Thread

import yaml
from fastapi import FastAPI
from injector import Injector

from isar.apis.schedule.router import create_scheduler_router
from isar.config import config
from isar.services.utilities.json_service import EnhancedJSONEncoder
from isar.state_machine.state_machine import main

from .modules import (
    APIModule,
    CoordinateModule,
    QueuesModule,
    ReaderModule,
    RequestHandlerModule,
    RobotModule,
    SchedulerModule,
    ServiceModule,
    StateMachineModule,
    StorageModule,
    TelemetryModule,
    UtilitiesModule,
)


def create_app(test_config=False):

    tags_metadata = [
    {
        "name": "Scheduler",
        "description": "Mission functionality",
    }
]

    logging.config.dictConfig(yaml.safe_load(open(f"./src/isar/config/logging.conf")))
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
        config.get("logging", "azure_storage_logging_level")
    )
    logging.getLogger("transitions.core").setLevel(
        config.get("logging", "transitions_core_logging_level")
    )

    app = FastAPI(openapi_tags=tags_metadata)
    
    injector = Injector(
        [
            APIModule,
            TelemetryModule,
            QueuesModule,
            StateMachineModule,
            StorageModule,
            SchedulerModule,
            ServiceModule,
            UtilitiesModule,
            RobotModule,
            ReaderModule,
            RequestHandlerModule,
            CoordinateModule,
        ]
    )  

    app.include_router(router=create_scheduler_router(injector=injector))
    
    if not test_config:
        state_machine_thread = Thread(target=main, args=[injector])
        state_machine_thread.start()

    return app



