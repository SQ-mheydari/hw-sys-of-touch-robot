from tntserver.Nodes.TnT.Dut import *
import os
import shutil
import toolbox
import cv2


dut_name = 'simu_dut'
dut_node = Dut(dut_name)
svg_file = os.path.abspath(os.path.join(os.getcwd(), 'data', 'dut_svg', 'simu_dut.svg'))
svg_backup = os.path.abspath(os.path.join(os.getcwd(), 'data', 'dut_svg', 'simu_dut_backup.svg'))


def set_svg_data():
    with open(svg_file, 'rb') as f:
        content = f.read()

    dut_node.set_svg_data(content)


def test_set_get_svg_data():
    set_svg_data()
    result = dut_node.svg_data()
    assert result is not None


def test_delete_svg_data():
    # set svg data to dut
    set_svg_data()

    # make a backup for svg file, as below codes delete the original file
    if not os.path.exists(svg_backup):
        shutil.copy(svg_file, svg_backup)

    # set None to delete svg data from dut
    dut_node.set_svg_data(None)
    result = dut_node.svg_data()
    assert result is None

    # rename backup file to original name
    if not os.path.exists(svg_file):
        shutil.copy(svg_backup, svg_file)

        # delete backup file
        if os.path.exists(svg_backup):
            os.remove(svg_backup)


def check_filtered_points(filtered, is_line=False):
    """
    Check if filtered points or lines are inside region or not
    In case of lines, only check the starting points and ending points
    Parameters
    ----------
    filtered: filtered lines or points
    is_line: True if it is filtered line; False if filtered points

    Returns: none
    -------

    """

    # here just if starting and ending points of lines are inside the region or not
    region = dut_node._svgregion
    contour = toolbox.dut.SvgRegion.region_to_contour(region.region['analysis_region'])
    for i in range(len(filtered)):
        # check if starting point (start x, and start y) is inside the region
        value = cv2.pointPolygonTest(contour,
                                     (float(filtered[i].strip(' [').split(',')[0]),
                                      float(filtered[i].strip(' [').split(',')[1].strip('[').strip(']'))),
                                     False)
        assert value >= 0

        # skip following check if filtered points
        if is_line:
            # check if ending point (end x, and end y) is inside the region
            value = cv2.pointPolygonTest(contour,
                                         (float(filtered[i].strip(' [').split(',')[2]),
                                          float(filtered[i].strip(' [').split(',')[3].strip('[').strip(']'))),
                                         False)
            assert value >= 0


def test_put_filter_lines():
    set_svg_data()

    # [start x, start y, end x, end y]
    l1 = [1, 0, 30, 59]
    l2 = [0, 1, 60, 98]

    l3 = [10, 10, 80, 130]
    l4 = [10, 10, 70, 190]

    # test the case where margin is default value
    result = dut_node.put_filter_lines(lines=(l1, l2, l3, l4), region='analysis_region')
    assert len(result) > 0
    filtered_lines = result[1].decode('utf-8').split('],')

    # check if filtered lines are inside region or not
    check_filtered_points(filtered_lines, True)

    # test the case where margin is not default value
    result = dut_node.put_filter_lines(lines=(l1, l2, l3, l4), region='analysis_region', margin=0.00001)
    assert len(result) > 0
    filtered_lines = result[1].decode('utf-8').split('],')

    # check if filtered lines are inside region or not
    check_filtered_points(filtered_lines, True)


def test_put_filter_points():
    set_svg_data()
    x1, y1 = 29, 30
    x2, y2 = 19, 33

    # test the case where margin is default value
    result = dut_node.put_filter_points(points=((x1, y1), (x2, y2)), region='analysis_region')
    assert len(result) > 0
    # check if filtered points are inside region or not
    filtered_points = result[1].decode('utf-8').split('],')
    check_filtered_points(filtered_points)

    # test the case where margin is not default value
    result = dut_node.put_filter_points(points=((x1, y1), (x2, y2)), region='analysis_region', margin=1)
    assert len(result) > 0
    filtered_points = result[1].decode('utf-8').split('],')
    # check if filtered points are inside region or not
    check_filtered_points(filtered_points)


def test_get_region_contour():
    set_svg_data()
    num_points = 10
    result = dut_node.get_region_contour(region='analysis_region', num_points=num_points)
    assert len(result[1].decode('utf-8').split('],')) == num_points
