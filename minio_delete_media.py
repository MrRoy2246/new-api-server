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

# from minio import Minio
# from minio.error import S3Error
# import concurrent.futures
# import itertools
# # Initialize MinIO client
# print("Hello--->")
# client = Minio(
#     "minioodb.accelx.net",  # MinIO server endpoint (adjust to your server)
#     access_key="admin",
#     secret_key="Accelx@123456",
#     secure=False  # Set to True if you're using HTTPS
# )
 
# bucket_name = "acceleye-media"
# prefix = "ori_detect_image_no_box/"
# batch_size = 100  # number of files to delete per batch/thread group

# # Delete one object
# def delete_object(obj_name):
#     try:
#         client.remove_object(bucket_name, obj_name)
#         return f"Deleted: {obj_name}"
#     except Exception as e:
#         return f"Error deleting {obj_name}: {e}"

# # Group generator
# def batch_iterator(iterable, size):
#     """Yield successive batches of size `size` from iterable."""
#     it = iter(iterable)
#     while True:
#         batch = list(itertools.islice(it, size))
#         if not batch:
#             break
#         yield batch

# try:
#     print("Starting deletion in batches...")

#     # Create a streaming object iterator
#     object_iter = client.list_objects(bucket_name, prefix=prefix, recursive=True)

#     for i, batch in enumerate(batch_iterator(object_iter, batch_size)):
#         object_names = [obj.object_name for obj in batch]

#         with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
#             results = list(executor.map(delete_object, object_names))

#         for r in results:
#             print(r)

#         print(f"✅ Batch {i+1}: Deleted {len(object_names)} images.")

#     print("🚀 All deletions completed.")

# except Exception as e:
#     print(f"Error: {e}")
