import logging
import logging.config

import uvicorn
import yaml

from isar import create_app
from isar.config import config

if __name__ == "__main__":

    app = create_app()
   
    hostAPI = config.get("environment", "fastapi_run_host")
    portAPI = config.get("environment", "fastapi_run_port")
    
    uvicorn.run(app,port=3000,host='localhost')
