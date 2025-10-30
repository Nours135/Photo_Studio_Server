
# app/core/storage.py

import os
import aiofiles
import aioboto3



from app.logger_config import get_logger
logger = get_logger(__name__)


class StorageService:
    ''''Abstract storage service
    '''
    async def save(self, file_id: str, content: bytes) -> bool:
        """save file, return access path"""
        raise NotImplementedError("Not implemented")
    
    async def read(self, file_id: str) -> bytes:
        """read file content"""
        raise NotImplementedError("Not implemented")

    async def delete(self, file_id: str) -> bool:
        """delete file"""
        raise NotImplementedError("Not implemented")
    
    async def exists(self, file_id: str) -> bool:
        """check if file exists"""
        raise NotImplementedError("Not implemented")

    @staticmethod
    def get_output_id(file_id: str) -> str:
        aaa = file_id.split(".")
        output_id = '.'.join(aaa[:-1]) + '.output' + '.png'
        return output_id
    

class LocalStorage(StorageService):
    def __init__(self):
        self.base_dir = os.path.join(os.path.expanduser(os.getenv("ROOT_DIR")), os.getenv("UPLOAD_DIR"))
        os.makedirs(self.base_dir, exist_ok=True)

    def get_local_file_path(self, file_id: str) -> str:
        return os.path.join(self.base_dir, file_id)

    async def save(self, file_id: str, content: bytes) -> bool:
        """save file, return access path"""
        try:
            file_path = self.get_local_file_path(file_id)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"LocalStorage: save file failed: {e}", exc_info=True)
            return False
    
    async def read(self, file_id: str) -> bytes:
        """read file content"""
        try:
            file_path = self.get_local_file_path(file_id)
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
        except FileNotFoundError:
            logger.error(f"LocalStorage: file not found: {file_id}")
            return None
        except Exception as e:
            logger.error(f"LocalStorage: read file failed: {e}", exc_info=True)
            return None

    async def delete(self, file_id: str) -> bool:
        try:
            file_path = self.get_local_file_path(file_id)
            os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"LocalStorage: delete file failed: {e}", exc_info=True)
            return False
    
    async def exists(self, file_id: str) -> bool:
        file_path = self.get_local_file_path(file_id)
        return os.path.exists(file_path)
    

class S3Storage(StorageService): 
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket_name = os.getenv("BUCKET_NAME")
        self.region = os.getenv("BUCKET_REGION", "us-east-2")

    async def save(self, file_id: str, content: bytes) -> bool:
        """save file, return access path"""
        try:
            async with self.session.client('s3', region_name=self.region) as client:
                await client.put_object(Bucket=self.bucket_name, Key=file_id, Body=content)
            return True
        except Exception as e:
            logger.error(f"S3Storage: save file failed: {e}", exc_info=True)
            return False
    
    async def read(self, file_id: str) -> bytes:
        """read file content"""
        try:
            async with self.session.client('s3', region_name=self.region) as client:
                response = await client.get_object(Bucket=self.bucket_name, Key=file_id)
                return await response['Body'].read()
        except Exception as e:
            logger.error(f"S3Storage: read file failed: {e}", exc_info=True)
            return None
    
    async def delete(self, file_id: str) -> bool:
        try:
            async with self.session.client('s3', region_name=self.region) as client:
                await client.delete_object(Bucket=self.bucket_name, Key=file_id)
            return True
        except Exception as e:
            logger.error(f"S3Storage: delete file failed: {e}", exc_info=True)
            return False
    
    async def exists(self, file_id: str) -> bool:
        try:
            async with self.session.client('s3', region_name=self.region) as client:
                await client.head_object(Bucket=self.bucket_name, Key=file_id)
            return True
        except Exception as e:
            logger.error(f"S3Storage: file not found: {file_id}", exc_info=True)
            return False