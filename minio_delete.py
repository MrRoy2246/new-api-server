from minio import Minio
from minio.error import S3Error
import datetime
import time
 
# Initialize MinIO client
print("Hello--->")
client = Minio(
    "minioodb.accelx.net",  # MinIO server endpoint (adjust to your server)
    access_key="admin",
    secret_key="Accelx@123456",
    secure=False  # Set to True if you're using HTTPS
)
 
# Specify the bucket name and folder (prefix)
bucket_name = "acceleye-media"
prefix = "ori_detect_image_no_box/"  # This could be your folder or prefix in the bucket
count = 0
try:
    objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
   
    for obj in objects:
        client.remove_object(bucket_name, obj.object_name)
       
        count = count + 1
        print(f"deleted: {obj.object_name} count: {count}")
        # time.sleep(0.02)
except Exception as e:
    print(f"Error deleting bucket {bucket_name}: {e}")


