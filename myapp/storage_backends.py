from storages.backends.s3boto3 import S3Boto3Storage

class MinioMediaStorage(S3Boto3Storage):
    bucket_name = "abinroy"  # your actual bucket name
    location = ""            # root of bucket (no folder nesting)
    default_acl = "public-read"
    file_overwrite = False   # optional: prevents overwriting files with the same name
