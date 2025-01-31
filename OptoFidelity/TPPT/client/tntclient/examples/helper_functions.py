"""
This file contains helper functions that make using OCR and icon detection a bit more convenient when doing basic
taps and swipes on detected objects.
"""
import time


def tap_icon(dut, icon_name, duration=0, timeout=5.0):
    """
    Taps an icon on a DUT screen if it is found before timeout occurs. Raises an exception if not successful.
    :param dut: Which DUT to try and find the icon in.
    :param icon_name: Name of the icon to find and tap.
    :param duration: Tap duration.
    :param timeout: How long to try finding the icon if it is not found immediately.
    :return:
    """
    start_time = time.time()

    # Try until timeout is reached in case the icon is not found on the first try
    while time.time() < start_time + timeout:
        # Try to find object
        # Tip: in pycharm it is possible to use debugger breakpoints to study return values
        object_data = dut.find_objects('C:\\OptoFidelity\\TnT Server\\data\\icons\\{}.shm'.format(icon_name))

        # If an object is found tap on the icon
        if len(object_data['results']) != 0:
            # We choose the first index from returned matches since it is the one with highest score
            results = object_data['results'][0]
            # Tapping on the icon
            dut.tap(results['centerX'], results['centerY'], clearance=-1, duration=duration)

            # Continue execution in the calling function since the icon was already tapped
            return

    # Icon was not found during the defined timeout period
    raise Exception('Icon {} was not found on the screen of {}'.format(icon_name, dut.name))


def swipe_icon(dut, icon_name, direction='up', swipe_length=10, timeout=5.0):
    """
    Swipes starting from the icon location on a DUT screen if it is found before timeout occurs.
    Raises an exception if not successful.
    :param dut: Which DUT to try and find the icon in.
    :param icon_name: Name of the icon to find and tap.
    :param direction: Swipe direction from list ['up', 'down', 'left', 'right'].
    :param swipe_length: Length of the swipe in millimeters.
    :param timeout: How long to try finding the icon if it is not found immediately.
    :return:
    """
    start_time = time.time()

    # Try to find the object until the timeout is reached in case the icon is not found on the first try
    while time.time() < start_time + timeout:
        object_data = dut.find_objects('C:\\OptoFidelity\\TnT Server\\data\\icons\\{}.shm'.format(icon_name))

        # If an object is found swipe starting from the icon
        if len(object_data['results']) != 0:
            # We choose the first index from returned matches since it is the one with highest score
            results = object_data['results'][0]
            # Swipe starting from the icon
            start_x = results['centerX']
            start_y = results['centerY']

            # Set the end coordinates according to the swipe direction.
            if direction == 'up':
                end_x = start_x
                end_y = start_y - swipe_length
            elif direction == 'down':
                end_x = start_x
                end_y = start_y + swipe_length
            elif direction == 'left':
                end_x = start_x - swipe_length
                end_y = start_y
            elif direction == 'right':
                end_x = start_x + swipe_length
                end_y = start_y
            else:
                raise ValueError('Invalid swipe direction. Use values from list ["up", "down", "left", "right")')

            dut.swipe(start_x, start_y, end_x, end_y, clearance=-1)
            # Continue execution in the calling function since the icon was already swiped
            return

    # Icon was not found during the defined timeout period
    raise Exception('Icon {} was not found on the screen of {}'.format(icon_name, dut.name))


def tap_text(dut, text, duration=0, timeout=5.0):
    """
    Taps on text on a DUT screen if it is found before timeout occurs. Raises an exception if not successful.
    :param dut: Which DUT to try and find the icon in.
    :param text: Text to tap.
    :param duration: Tap duration.
    :param timeout: How long to try finding the icon if it is not found immediately.
    :return:
    """
    start_time = time.time()

    # Try until timeout is reached in case the text is not found on the first try
    while time.time() < start_time + timeout:
        # Try to find the text
        text_data = dut.search_text(text)

        # If text is found
        if len(text_data['results']) != 0:
            # We choose the first index from returned matches since it is the one with highest score
            results = text_data['results'][0]
            # Tapping on the text
            dut.tap(results['centerX'], results['centerY'], clearance=-1, duration=duration)
            # Continue execution in the calling function since the text was already tapped
            return

    # Text was not found during the defined timeout period
    raise Exception('Text "{}" was not found on the screen of {}'.format(text, dut.name))
