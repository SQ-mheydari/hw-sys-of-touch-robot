import os
import tempfile


"""
only binary files; if text type, encode first to binary

list_data, read_data, write_data uses subfolders under 'data' folder.
temporaryfile creates temporary file in operating system fashion

Use these functions if you are
- storing any categorized data
    - images for analyze | write_data(category='image_analysis')

Especially use 'temporaryfile' if
- storing data for external applications (images for abbyy, halcon for example)
    
    with open_temporaryfile() as file:
        file.write(image)
    analyze_image_at_path(file.name)
    files.delete_temporaryfile(file)

"""


def __validate_path(path):
    os.makedirs(path, exist_ok=True)


def auto_index_filename(path, name):
    filename, extension = os.path.splitext(name)[0:2]
    __validate_path(path)
    files = [os.path.splitext(file)[0] for file in os.listdir(path) if file.startswith(filename)]
    if len(files) == 0:
        return name

    last_file = sorted(files)[-1]
    index = int(last_file.split("_")[1]) if "_" in last_file else 0
    index += 1
    name = "{}_{}{}".format(filename, index, extension)
    return name


def list_data(category):
    path = os.path.abspath("data/{}".format(category))
    __validate_path(path)
    listed = os.listdir(path)
    return listed


def read_data(category, name):
    path = os.path.abspath("data/{}/{}".format(category, name))
    with open(path, "rb") as file:
        data = file.read()
    return data


def write_data(category, name, data, auto_sequence=False):
    if auto_sequence:
        name = auto_index_filename(os.path.abspath("data/{}".format(category)), name)
    path = os.path.abspath("data/{}/{}".format(category, name))

    __validate_path(os.path.split(path)[0])
    with open(path, "wb") as file:
        file.write(data)
    return os.path.split(path)[1]


def delete_data(category, name):
    path = os.path.abspath("data/{}/{}".format(category, name))
    os.remove(path)


def open_temporaryfile():
    file = tempfile.NamedTemporaryFile(delete=False)
    return file


def delete_temporaryfile(file):
    os.remove(file.name)


if __name__ == '__main__':
    # test
    write_data("strings", "string.txt", b"this is string 1", auto_sequence=True)
    write_data("strings", "string.txt", b"this is string 2", auto_sequence=True)
    write_data("strings", "string.txt", b"this is string 3", auto_sequence=True)
    write_data("strings", "string.txt", b"this is string 4", auto_sequence=True)

    files = list_data('strings')
    print(files)

    for file in files:
        data = read_data("strings", file)
        print(file, data)
        delete_data("strings", file)
