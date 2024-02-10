import base64


def get_base64_string(file_path):
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        data = str(encoded_string)[2:]
        data = data[:-1]
        return data
