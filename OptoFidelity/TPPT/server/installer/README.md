# TnT Server Installer

This project is used to create TnT Server installer/package in Jenkins.

PyInstaller traverses through required packages using project's start.py as an entry point. After the single folder package has been created, InnoSetup is used to encapsulate the package to an actual installer.

# Project structure

This project requires that it's run inside an activated TnT Server virtual environment which has all the TnT Server dependencies installed.

The application structure should be approximately following:

```
app_package/
installer/
main.py
project_config.json
Jenkinsfile
```

where `app_package` contains all project python modules, `installer` is this git repository (as a submodule), `main.py` is the entry point that imports `app_package`, `project_config.json` contains project specific configuration for the installer as detailed below and `Jenkinsfile` is the file used by Jenkins pipeline to build the project.

If encryption is desired, then `cwheel` and `cwheel_hook` packages must also be installed in the same virtual environment(currently these are pre-built wheels within installer). In this case, the project entry file (`main.py`) must contain `import sitecustomize` as the first line. This will hook the cwheel decrpytion functionality in the built application. Note that the entry point file can not be encrypted. So `main.py` should look like this

```
try:
    # From wheel_hook
    import sitecustomize
except:
    pass

try:
    import app_package
except ValueError as e:
    # ValueError is thrown by server build if decryption of imported module fails.
    print(str(e))
    print("Please check that HASP dongle is connected and valid.")
else:
    if __name__ == "__main__":
        app_package.main()

```

# Step-by-step process

The installation process is detailed below. In typical use case, these steps are implemented in the project's Jenkins file.

1. Project generates a JSON file (see below) that specifies project specific attributes for the build process. These include the application name, hidden Python modules and so on. Make sure the project directory is in `PYTHONPATH`.
2. Go to installer directory
3. Run `python setup_installer.py setup-generic.in.iss ..\\project_config.json %BUILD_NUMBER%`, where `project_config.json` is the project specific config file and `%BUILD_NUMBER` is environment variable set by Jenkins. This produces `setup-generic.iss` file for `iscc` installer creator and `version.txt` that contains appropriate version information of the build.
4. Run `python -m PyInstaller -y tnt-generic.spec ..\\project_config.json`. This runs Pyinstaller that produces executeable application.
5. Run `python encrypt_packages.py ..\\project_config.json` to encrypt packages specified by the JSON file.
6. Run `iscc setup-generic.iss` to create a Windows installer for the application.

# The project configuration JSON file

The project JSON file must have at least following content:

```
{
  "encrypted_packages":
      [
      "app_package"
      ],
  
  "hiddenimports":
      [
      "tntmini.loggingfilters"
      ],
  
  "add_dlls": [
      {
          "module": "numpy",
          "subdir": "./core"
      }
  ],
  "entry": "../main.py",
  "datas": [
      [
          "version.txt",
          "."
      ]
  ],
  "exe_name": "MyApplication",
  "app_name": "MyApplication",
  "app_id": "app-id-for-iss-file",
  "version_module": "MyApplication",
  "configuration_directories": [
      "configuration"
  ]
}
```

# Example Jenkinsfile

In Jenkins pipeline, the `Jenkinsfile` stage structure for Windows build could look like this:

```
    stages {
        stage('Prepare virtualenv') {
            steps {
                notifySlack('STARTED')

                deleteDir()
                checkout scm
                bat """
SET PATH=C:\\Users\\tuotekehitys\\AppData\\Local\\Programs\\Python\\Python35-32;%PATH%
SET PATH=C:\\Users\\tuotekehitys\\AppData\\Local\\Programs\\Python\\Python35-32\\Scripts;%PATH%
SET PATH=%PATH:"=%

python -m venv venv
call venv\\Scripts\\activate.bat

python -m pip install --upgrade pip==18
python -m pip install --upgrade setuptools

cd installer
pip install -r requirements.txt
cd ..

pip install -r requirements.txt

copy /y installer\\pyinstaller_fix\\misc.py venv\\Lib\\site-packages\\PyInstaller\\utils
                """
            }
        }
        stage('Installer') {
            steps {
                bat """
SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat

SET PYTHONPATH=%cd%

cd installer
python setup_installer.py setup-generic.in.iss ..\\project_config.json %BUILD_NUMBER%
python -m PyInstaller -y tnt-generic.spec ..\\project_config.json
python encrypt_packages.py ..\\project_config.json

iscc setup-generic.iss
cd ..
                """
                archive 'installer\\Output\\*.exe'
            }
        }
        stage('Test - Installer') {
            steps {
                bat """
for /r %%x in (installer\\Output\\*.exe) do set INSTALLER="%%x"

%INSTALLER% /VERYSILENT /LOG=install.log /DIR=installation
                """
                archive 'install.log'
            }
        }
        stage('Test - License key') {
            steps {
                bat """
set OF_LICENSE_PATH=installer/licenses/license_expired
installation\\"MyApplication.exe" > output.txt
findstr "bad marshal data" output.txt
                """
            }
        }
        stage('Test - Uninstaller') {
            steps {
                bat """
"installation\\unins000.exe" /VERYSILENT
                """
            }
        }
    }
```

Notice that currently one Python file in Pyinstaller is patched due to a bug. An issue has been reported so hopefully this patch can be removed in the future.

There is also a test stage that verifies that the application will not start with expired license.

# Security

The main motivation for HASP encryption is to time-lock software when it is delivered. This gives leverage if customer refuses to pay the final bill. Another motivation is to prevent customer from seeing our platform source code. However, the encryption does not give strong guarantee for the latter. The Python bytecode will be decrypted in memory during the execution of the program.

To be able to use cwheel without making modifications to pyinstaller, it is necessary that all pyc files are stored as individual files in the build (instead of being archived inside the exe). The pyc files that are our IPR, are then encrypted. However, if the license if valid and HASP attached, the customer is able to see our code with a very simple procedure:

Let's suppose our encrypted package in the build is `mypackage`. Lets also assume that customer has installed Python interpreter. Then in the installation directory, launch python and type:

```
> import sitecustomize  # This hooks the cwheel decrypt feature
> import mypackage  # If license is valid, this encrypted package is then decrypted and imported
```

Now the contents of `mypackage` is good for inspection. Chances are that they are not aware that sitecustomize needs to be imported. In this case `mypackage` can't be imported even with a valid license. However, this is very weak defense from determined hacker.