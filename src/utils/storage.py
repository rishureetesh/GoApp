from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.config.settings import STORAGE_ACCOUNT_NAME


def getCredentials() -> any:
    return DefaultAzureCredential()


def list_blobs(storage_account: str = STORAGE_ACCOUNT_NAME, path: str = None) -> list:
    token_credential = getCredentials()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=token_credential,
    )
    container_name = path.split("/")[0]
    target_directory = "/".join(path.split("/")[1:])
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_list = [
            {
                "filepath": f"{container_name}/{blob.name}",
                "filename": blob.name.split("/")[-1],
                "created": blob.creation_time,
            }
            for blob in container_client.list_blobs(name_starts_with=target_directory)
            if len(blob.name.split("/")[-1].split(".")) > 1
        ]
        return blob_list
    except Exception as e:
        return []


def read_blob(
    storage_account: str = STORAGE_ACCOUNT_NAME,
    path: str = None,
    bytes_to_read: int = None,
) -> any:
    token_credential = getCredentials()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=token_credential,
    )
    container_name = path.split("/")[0]
    target_filepath = "/".join(path.split("/")[1:])
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(target_filepath)

        # If we have been given a limited number of bytes to read,
        # then we also need to have an explicit offset (though that will always be 0)
        offset = None
        if bytes_to_read != None:
            offset = 0

        return blob_client.download_blob(length=bytes_to_read, offset=offset).readall()
    except:
        return None


def write_to_blob(
    storage_account: str = STORAGE_ACCOUNT_NAME, path: str = None, data: any = None
) -> any:
    token_credential = getCredentials()
    account_url = f"https://{storage_account}.blob.core.windows.net"
    blob_service_client = BlobServiceClient(
        account_url=account_url,
        credential=token_credential,
    )
    container_name = path.split("/")[0]
    target_filepath = "/".join(path.split("/")[1:])
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(target_filepath)
        blob_client.upload_blob(data=data, overwrite=True)
        return f"{account_url}/{container_name}/{target_filepath}"
    except Exception as e:
        return None


def delete_blob(storage_account: str = STORAGE_ACCOUNT_NAME, path: str = None) -> any:
    token_credential = getCredentials()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=token_credential,
    )
    container_name = path.split("/")[0]
    target_filepath = "/".join(path.split("/")[1:])
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(target_filepath)
        blob_client.delete_blob()
    except Exception as e:
        print(e)
        return None
