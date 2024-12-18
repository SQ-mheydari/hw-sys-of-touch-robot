import collections
import matplotlib.patches as pltpatches
import numpy
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import mimetypes
import cv2
import base64

import TPPTcommon.containers as Containers
from TPPTcommon.grid import azimuth_direction


class GridVisContainer:
    """
    Container for grid visualization. Contains all elements needed to visualize a test grid.
    Args:
    name: string
    panel_size: (width, height)
    items: List of objects derived from containers.TestAction to be plotted
    title: string [sub-plot title; e.g. DUT name]
    """

    def __init__(self, name, panel_size, items, title=None, projection_3d=False):
        self.name = name
        self.panel_size = panel_size
        self.items = items
        self.title = title
        self.projection_3d = projection_3d

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, hex(id(self)))


class GridVisualizer:
    """
    Class that is used to generate measurement point figures
    Usage:
        gv = GridVisualizer()
        gv.AddGridList(gridlist) # gv.AddGrid(grid) See AddGrid() or AddGridList()
        images = gv.Render()
    """

    def __init__(self):
        self.figure = Figure()
        self.grids = {}

    def Render(self):
        """
        Main rendering function, generates test grid images
        :return: Dictionary { 'test case name' : [list of plotted images] }
        """
        images = {}

        fig = self.figure
        fig_canvas = FigureCanvas(fig)

        for gesture in self.grids:
            grids = self.grids[gesture]

            if not isinstance(grids, collections.Iterable):
                grids = [grids]

            for grid_n in range(len(grids)):
                ax_n = 111
                active_grid = grids[grid_n]
                if active_grid.projection_3d:
                    ax = fig.add_subplot(ax_n, title=active_grid.title, projection='3d')
                else:
                    ax = fig.add_subplot(ax_n, title=active_grid.title)
                points = [[], [], [], []]

                normals = []
                for i in active_grid.items:
                    if isinstance(i, Containers.Point):
                        multi = False
                        try:
                            multi = i.multifinger
                        except:
                            pass
                        if multi:
                            multi_finger_points = self._CreateMultifingerTapPoints(i, i.angle)
                            for multi_finger_point in multi_finger_points:
                                points[0].append(multi_finger_point[0])
                                points[1].append(multi_finger_point[1])
                                points[2].append(multi_finger_point[2])
                                points[3].append(multi_finger_point[3])
                        else:
                            points[0].append(i.x)
                            points[1].append(i.y)
                            points[2].append(i.z)
                            if isinstance(i, Containers.TouchAreaPoint) and i.touch_area == 'edge_area':
                                points[3].append('r')
                            else:
                                points[3].append('b')


                    elif isinstance(i, Containers.Line):
                        multi = False
                        try:
                            multi = i.multifinger
                        except:
                            pass
                        if not multi:
                            color = "blue"
                            try:
                                color = i.color
                            except:
                                pass
                            if not active_grid.projection_3d:
                                ax.arrow(i.start_x, i.start_y, i.end_x - i.start_x, i.end_y - i.start_y, head_width=2,
                                         head_length=2, fc=color, ec=color)
                            else:
                                ax.plot([i.start_x, i.end_x], [i.start_y, i.end_y], zs=[i.start_z, i.end_z],
                                        color=color)
                        else:
                            arrows = self._CreateMultifingerLineArrows(i)
                            for arrow in arrows:
                                ax.arrow(arrow[0], arrow[1], arrow[2], arrow[3], head_width=arrow[4],
                                         head_length=arrow[5], fc=arrow[6], ec=arrow[6])

                if active_grid.projection_3d:
                    ax.scatter(points[0], points[1], points[2], color=points[3])
                    for normal in normals:
                        ax.plot(normal[0], normal[1], normal[2], linewidth=2)

                    max_range = numpy.array([max(points[0]) - min(points[0]), max(points[1]) - min(points[1]),
                                             max(points[2]) - min(points[2])]).max() / 2.0
                    mid_x = (max(points[0]) + min(points[0])) * 0.5
                    mid_y = (max(points[1]) + min(points[1])) * 0.5
                    mid_z = (max(points[2]) + min(points[2])) * 0.5
                    ax.set_xlim(mid_x - max_range, mid_x + max_range)
                    ax.set_ylim(mid_y + max_range, mid_y - max_range)
                    ax.set_zlim(mid_z - max_range, mid_z + max_range)
                else:
                    ax.scatter(points[0], points[1], color=points[3])

                if not active_grid.projection_3d:
                    ax.add_patch(pltpatches.Rectangle([0, 0], active_grid.panel_size[0], active_grid.panel_size[1],
                                                      edgecolor='black', fill=False))
                    ax.axis([-10, active_grid.panel_size[0] + 10, active_grid.panel_size[1] + 10, -10])
                    ax.set_xlabel("Measurement area width " + str(numpy.around(active_grid.panel_size[0], 2)) + " [mm]")
                    ax.set_ylabel(
                        "Measurement area height " + str(numpy.around(active_grid.panel_size[1], 2)) + " [mm]")
                    ax.set_aspect('equal')
                else:
                    pass

                if gesture not in images:
                    images[gesture] = []
                images[gesture].append(self._fig_to_canvas(fig_canvas))

                fig.clear()

        return images

    def autowrap_text(self, textobj, renderer):
        """Wraps the given matplotlib text object so that it exceed the boundaries
        of the axis it is plotted in."""
        import textwrap
        # Get the starting position of the text in pixels...
        x0, y0 = textobj.get_transform().transform(textobj.get_position())
        # Get the extents of the current axis in pixels...
        clip = textobj.get_axes().get_window_extent()
        # Set the text to rotate about the left edge (doesn't make sense otherwise)
        textobj.set_rotation_mode('anchor')

        # Get the amount of space in the direction of rotation to the left and
        # right of x0, y0 (left and right are relative to the rotation, as well)
        rotation = textobj.get_rotation()
        right_space = self.min_dist_inside((x0, y0), rotation, clip)
        left_space = self.min_dist_inside((x0, y0), rotation - 180, clip)

        # Use either the left or right distance depending on the horiz alignment.
        alignment = textobj.get_horizontalalignment()
        if alignment is 'left':
            new_width = right_space
        elif alignment is 'right':
            new_width = left_space
        else:
            new_width = 2 * min(left_space, right_space)

        # Estimate the width of the new size in characters...
        aspect_ratio = 0.5  # This varies with the font!!
        fontsize = textobj.get_size()
        pixels_per_char = aspect_ratio * renderer.points_to_pixels(fontsize)

        # If wrap_width is < 1, just make it 1 character
        wrap_width = max(1, new_width // pixels_per_char)
        try:
            wrapped_text = textwrap.fill(textobj.get_text(), wrap_width)
        except TypeError:
            # This appears to be a single word
            wrapped_text = textobj.get_text()
        textobj.set_text(wrapped_text)

    def min_dist_inside(self, point, rotation, box):
        """Gets the space in a given direction from "point" to the boundaries of
        "box" (where box is an object with x0, y0, x1, & y1 attributes, point is a
        tuple of x,y, and rotation is the angle in degrees)"""
        from math import sin, cos, radians
        x0, y0 = point
        rotation = radians(rotation)
        distances = []
        threshold = 0.0001
        if cos(rotation) > threshold:
            # Intersects the right axis
            distances.append((box.x1 - x0) / cos(rotation))
        if cos(rotation) < -threshold:
            # Intersects the left axis
            distances.append((box.x0 - x0) / cos(rotation))
        if sin(rotation) > threshold:
            # Intersects the top axis
            distances.append((box.y1 - y0) / sin(rotation))
        if sin(rotation) < -threshold:
            # Intersects the bottom axis
            distances.append((box.y0 - y0) / sin(rotation))
        return min(distances)

    def _fig_to_canvas(self, fig_canvas):
        fig_canvas.draw()

        width, height = self.figure.get_size_inches() * self.figure.get_dpi()
        width = int(width)
        height = int(height)

        frame = numpy.fromstring(fig_canvas.tostring_rgb(), dtype='uint8').reshape(height, width, 3)
        bd = GridVisualizer.ndarray_to_img_src(frame, ".png")
        return bd

    def ndarray_to_img_src(image: numpy.ndarray, type=".jpg"):
        """Convert image into img.src source string"""
        mimetype, encoding = mimetypes.guess_type("base" + type)
        mimetype = mimetype if mimetype is not None else 'image/jpeg'
        r, data = cv2.imencode(type, image)
        bd = base64.b64encode(data)
        bd = "data:" + mimetype + ";base64," + bd.decode()
        return bd

    def _CreateMultifingerLineArrows(self, line):
        colour_LUT = ['#0000FF',
                      '#00FF00',
                      '#FF00FF',
                      '#00FFFF',
                      '#FFFF00',
                      '#FFA600',
                      '#8CFF00',
                      '#CC00FF',
                      '#FF7AB6',
                      '#000000',
                      '#7D7D7D']
        retval = []
        start_x = line.start_x
        start_y = line.start_y
        end_x = line.end_x
        end_y = line.end_y
        retval.append((start_x, start_y, end_x - start_x, end_y - start_y, 2, 2, colour_LUT[0]))

        angle = line.angle
        unit_vec = azimuth_direction(numpy.radians(angle))
        for i in range(line.fingers - 1):
            x_t = (i + 1) * line.finger_distance * unit_vec[0]
            y_t = (i + 1) * line.finger_distance * unit_vec[1]
            retval.append((start_x + x_t, start_y + y_t, end_x - start_x, end_y - start_y, 2, 2, colour_LUT[i + 1]))

        return retval

    def _CreateMultifingerTapPoints(self, point, angle=0.0):
        colour_LUT = ['#0000FF',
                      '#00FF00',
                      '#FF00FF',
                      '#00FFFF',
                      '#FFFF00',
                      '#FFA600',
                      '#8CFF00',
                      '#CC00FF',
                      '#FF7AB6',
                      '#000000',
                      '#7D7D7D']
        retval = []
        retval.append((point.x, point.y, 0.0, colour_LUT[0]))

        unit_vec = azimuth_direction(numpy.radians(angle))

        for i in range(point.fingers - 1):
            x_t = (i + 1) * point.finger_distance * unit_vec[0]
            y_t = (i + 1) * point.finger_distance * unit_vec[1]
            retval.append((point.x + x_t, point.y + y_t, 0.0, colour_LUT[i + 1]))

        return retval

    def AddGrid(self, name, grid):
        """
        Adds a single grid for visualization:
        args:
        name: name of the group(Test name usually) to add the grid to.
        grid: GridVisContainer-object
        """
        if name in self.grids:
            self.grids[name].append(grid)
        else:
            self.grids[name] = [grid]

    def AddGridList(self, griddict):
        """
        Adds a dictionary of grids for visualization:
        args:
        griddict: {"name":[GridVisContainer,],}
        """
        self.grids = {**self.grids, **griddict}

    def ClearGrids(self):
        """
        Clears all grids.
        """
        self.grids = {}