import multiprocessing

try:
    # From wheel_hook
    import sitecustomize
except:
    pass

try:
    import tntserver
except ValueError as e:
    # ValueError is thrown by server build if decryption of imported module fails.
    print(str(e))
    print("Please check that HASP dongle is connected and valid.")
else:
    if __name__ == "__main__":
        # Required for multiprocessing to work with pyinstaller.
        # Must be first code line after if __name__ == "__main__": or it won't work.
        multiprocessing.freeze_support()

        tntserver.main()
