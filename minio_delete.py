from minio import Minio
from minio.error import S3Error
import datetime
 
# Initialize MinIO client
client = Minio(
    "192.168.1.150:9000",  # MinIO server endpoint (adjust to your server)
    access_key="admin",
    secret_key="Accelx@123456",
    secure=False  # Set to True if you're using HTTPS
)
 
# Specify the bucket name and folder (prefix)
bucket_name = "acceleye-media"
prefix = "ori_detect_image_no_box/"  # This could be your folder or prefix in the bucket
 
# Get the list of objects in the folder
objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
 
# Create a list of (object_name, last_modified) pairs
object_list = []
for obj in objects:
    object_list.append((obj.object_name, obj.last_modified))
 
# Sort objects by last_modified timestamp (oldest first)
object_list.sort(key=lambda x: x[1])
 
# Delete the oldest 1000 images
oldest_images = object_list[:1000]  # Select the oldest 1000 objects
 
# Loop through and delete each of the oldest 1000 images
for obj_name, last_modified in oldest_images:
    try:
        print(f"Deleting image: {obj_name} (Last modified: {last_modified})")
        client.remove_object(bucket_name, obj_name)
    except S3Error as e:
        print(f"Error deleting {obj_name}: {e}")
 
print("Oldest 1000 images deleted successfully.")
 