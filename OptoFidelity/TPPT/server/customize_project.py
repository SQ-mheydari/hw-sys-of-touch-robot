import shutil, os, argparse


def customize_by_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configuration-file", help="Include this configuration as start.yaml", default="start.yaml")

    args = parser.parse_args()

    if args.configuration_file != "start.yaml":
        try:
            os.rename("configuration/start.yaml", "configuration/start.yaml.orig")
        except OSError:
            pass
        shutil.copy("configuration/{}".format(args.configuration_file), "configuration/start.yaml")


if __name__ == "__main__":
    customize_by_args()


