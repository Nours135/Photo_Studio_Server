# load config from .env to change from local to remote
import os
from dotenv import load_dotenv

def get_worker_config() -> dict:
    load_dotenv()
    if os.getenv("ENV") == "local":  # local worker
        return {
            "RESIZE_IMAGE": True,
            "RESIZE_IMAGE_SIZE": (512, 512),  # some models need to resize the image to be able to run on CPU
            "MODEL_DEVICE": "cpu",
            "ENV": "local"
        }
    elif os.getenv("ENV") == "GPU":  # remote worker (GPU server)   
        return {
            "RESIZE_IMAGE": False,
            "MODEL_DEVICE": "cuda",
            "ENV": "GPU"
        }
    else:
        raise ValueError(f"Invalid environment: {os.getenv('ENV')}")


