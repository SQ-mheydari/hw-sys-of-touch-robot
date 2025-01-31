import os
import sys
import zipfile
import re
import shutil


def get_version():
    # read version number and build number from version.txt
    data = {}
    with open('version.txt') as f:
        lines = f.readlines()
        for line in lines:
            words = line.split(':')
            if re.search('Version', words[0], re.IGNORECASE):
                data['Version'] = words[1].strip()
            if re.search('Build', words[0], re.IGNORECASE):
                data['Build'] = words[1].strip()
    return data


def zipdir(name, path, ignored):
    zipf = zipfile.ZipFile(name, 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(path):
        add = True
        dirs = root.split('/')
        for item in ignored['dirs']:
            if item in dirs:
                add = False
                break

        if add:
            for file in files:
                if file not in ignored['files']:
                    absname = os.path.join(root, file)
                    arcname = absname[len(path) + 1:]
                    zipf.write(os.path.join(root, file), arcname)

    zipf.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    app_name = sys.argv[1]
    dist_dir = sys.argv[2]
    numbers = get_version()


    ignored_data = dict()
    if app_name == 'tppt_gt':
        app_name = 'TPPT_Scripts'
        zipfile_name= 'dist/' + app_name + '_' + numbers['Version'] + '.' + numbers['Build'] + '.zip'
        ignored_data['dirs'] = ['venv', '__pycache__', '.git', '.idea', 'dist']
        ignored_data['files'] = ['.gitignore', '.git', '.DS_Store', 'README.md', '.gitmodules', 'database.sqlite']

        zipdir(zipfile_name, os.getcwd(), ignored_data)
    else:
        zipfile_name = '../' + app_name + '_' + numbers['Version'] + '.' + numbers['Build']
        os.chdir('Installer/dist/' + dist_dir)
        shutil.make_archive(zipfile_name, 'zip')
        os.chdir('../../..')

