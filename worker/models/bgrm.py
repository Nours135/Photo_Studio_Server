# background removal model

import os
import torch
from typing import Any
from torchvision import transforms
from skimage import io

from app.logger_config import get_logger

from worker.models.u2net.u2net import U2NET, U2NETP
from worker.models.u2net.transform import normPRED, RescaleT, ToTensorLab, save_output
from worker.models.base import BaseModel
from app.core.queue import QueueTaskPayload
from app.core.storage import LocalStorage, S3Storage
# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
logger = get_logger(__name__)


class BackgroundRemovalModel(BaseModel):
    def __init__(self, model_name: str = 'u2net'):
        super().__init__()
        assert model_name in ['u2net', 'u2netp'], "Invalid model name"
        self._model_name = model_name
        self._model_dir = os.path.join(os.path.expanduser(os.environ['ROOT_DIR']), './worker/models/u2net', 'saved_models', self._model_name, self._model_name + '.pth')

        self._model_transform = transforms.Compose([
            RescaleT(320),
            ToTensorLab(flag=0),
        ])

        self.storage_service = LocalStorage()  
        self.storage_service_s3 = S3Storage()

    def _use_cuda(self) -> bool:
        return torch.cuda.is_available() and self.config['MODEL_DEVICE'] == 'cuda'

    async def _inference(self, task: QueueTaskPayload) -> Any:   # do not implement batch processing here
        await self._lazy_load_model()
        # import pdb; pdb.set_trace()
        # preprocess the input image
        if self.config['ENV'] == 'local':
            task_path = task.input_image_s3_key
        elif self.config['ENV'] == 'GPU':
            raise NotImplementedError("Not implemented")
            # task_path = task.input_image_s3_key
            # TODO: download the image from S3
        else:
            raise ValueError(f"Invalid environment: {self.config['ENV']}")

        logger.info(f"task_id: {task.task_id}, BackgroundRemovalModel: task_path: {task_path}")
        # import pdb; pdb.set_trace()
        input_image_path = self.storage_service.get_local_file_path(task_path)
        input_image = io.imread(input_image_path)
        input_image = self._model_transform({'image': input_image})['image']

        input_image = input_image.type(torch.FloatTensor)

        if self._use_cuda():
            input_image = input_image.to(self.config['MODEL_DEVICE'])
        # else:
        #     input_image = input_image.to('cpu')

        # inference
        # import pdb; pdb.set_trace()  
        input_image = input_image.unsqueeze(0)  # add batch dimension
        d1,d2,d3,d4,d5,d6,d7 = self._model(input_image)
        del input_image, d2,d3,d4,d5,d6,d7
        
        pred = d1[:,0,:,:]
        pred = normPRED(pred)

        # postprocess the output
        logger.info(f'task_id: {task.task_id}, BackgroundRemovalModel: saving output...')
        output_id = LocalStorage.get_output_id(task_path)  # Use static method
        output_image_path = self.storage_service.get_local_file_path(output_id)
        
        await save_output(input_image_path, pred, output_image_path)  # save to local
        output_img_content = await self.storage_service.read(output_id)  # Use file_id not path
        await self.storage_service_s3.save(output_id, output_img_content)  # save to s3


    async def _lazy_load_model(self):   # need IO, so async
        if self._is_loaded and self._model is not None:
            return
        
        if(self._model_name=='u2net'):
            logger.info("...load U2NET---173.6 MB")
            net = U2NET(3,1)
        elif(self._model_name=='u2netp'):
            logger.info("...load U2NEP---4.7 MB")
            net = U2NETP(3,1)

        if self._use_cuda():
            net.load_state_dict(torch.load(self._model_dir))
            net.to(self.config['MODEL_DEVICE'])
        else:
            net.load_state_dict(torch.load(self._model_dir, map_location='cpu'))
        net.eval()  # set model to evaluation mode

        self._model = net
        self._is_loaded = True

    def _unload_model(self):
        if self._model is not None:
            del self._model
            self._model = None
            self._is_loaded = False


# if __name__ == '__main__':
    # do a test for background removal
    # copy these to the worker/main.py file
    # then run python -m worker.main


    # import os
    # os.environ['ROOT_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # # print(os.environ['ROOT_DIR'])
    # # import pdb; pdb.set_trace()

    # async def test_bgrm():
    #     from app.core.queue import QueueTaskPayload
    #     import uuid

    #     bgrm = BackgroundRemovalModel()
    #     bgrm.start()
    #     return await bgrm._inference(QueueTaskPayload(
    #         task_id=uuid.uuid4(),
    #         task_type='background_removal',
    #         user_id=uuid.uuid4(),
    #         input_image_local_path='./uploads/horse.jpg',
    #         input_image_s3_key='horse.jpg',
    #     ))

    # asyncio.run(test_bgrm())