import numpy as np
import scipy.interpolate
from tntserver import robotmath
import transformations as tr


class Surface:
    """
    Creates curved correlation between dut coordinates and curved world coordinates
    Creates one 2-dimensional curve function for each x, y and z
    """
    def __init__(self, data):
        """

        :param data: {"points": list of points,
                      "grid_size": tuple of width, height of one grid step,
                      "transform": transformation matrix as list}
        """
        points = data["points"]
        grid_size = data["grid_size"]
        transform = data["transform"]
        self._transform = np.matrix(transform)

        print("init with {} points, grid {},{}".format(len(points), grid_size[0], grid_size[1]))

        # curve functions:
        self._width = 0
        self._height = 0

        self.xf = None
        self.yf = None
        self.zf = None
        self._points = points
        self._grid_size = grid_size

        self.set_indexed_points(points)

    def points(self):
        return self._points

    def set_indexed_points(self, points):
        # assume 16 x 16 grid with 256 possible point IDs

        grid_size = self._grid_size

        pts = []

        for p in points:
            v = int(p)
            x = int(v & 15) * grid_size[0]
            y = int(v / 16) * grid_size[1]

            p3d = points[p]

            newpt = [x, y, p3d[0], p3d[1], p3d[2]]
            pts.append(newpt)

        # dut size
        mx = np.max(np.array(pts), 0)
        self._width = mx[0]
        self._height = mx[1]

        pts = np.array(pts)

        xf = scipy.interpolate.SmoothBivariateSpline(
            pts[:, 0].flatten(),
            pts[:, 1].flatten(),
            pts[:, 2].flatten(), kx=3, ky=3, s=0.1)

        yf = scipy.interpolate.SmoothBivariateSpline(
            pts[:, 0].flatten(),
            pts[:, 1].flatten(),
            pts[:, 3].flatten(), kx=3, ky=3, s=0.1)

        zf = scipy.interpolate.SmoothBivariateSpline(
            pts[:, 0].flatten(),
            pts[:, 1].flatten(),
            pts[:, 4].flatten(), kx=3, ky=3, s=0.1)

        self.xf = xf
        self.yf = yf
        self.zf = zf

    def ddx_for_xy(self, x, y):
        dx = float(self.xf.ev(x, y, dx=1))
        dy = float(self.yf.ev(x, y, dx=1))
        dz = float(self.zf.ev(x, y, dx=1))
        return dx, dy, dz

    def ddy_for_xy(self, x, y):
        dx = float(self.xf.ev(x, y, dy=1))
        dy = float(self.yf.ev(x, y, dy=1))
        dz = float(self.zf.ev(x, y, dy=1))
        return dx, dy, dz

    def xyz_for_xy(self, x, y):
        px = float(self.xf(x, y))
        py = float(self.yf(x, y))
        pz = float(self.zf(x, y))
        return px, py, pz

    def closest_point(self, x, y):
        cl_x = np.clip(x, 0, self.width)
        cl_y = np.clip(y, 0, self.height)

        return cl_x, cl_y

    def frame_for_xyz(self, x, y, z):

        # Find closest point within surface parameter space to given point.
        # Frame orientation is evaluated at this closest point.
        # Frame translation is evaluated at given point or by linear
        # extrapolation if the point is outside of surface.
        cl_x, cl_y = self.closest_point(x, y)

        # Surface tangent vector along x-parameter
        tan_x = np.array(self.ddx_for_xy(cl_x, cl_y))
        tan_x /= np.linalg.norm(tan_x)

        # Surface tangent vector along y-parameter
        tan_y = np.array(self.ddy_for_xy(cl_x, cl_y))
        tan_y /= np.linalg.norm(tan_y)

        # Normal vector
        normal = np.cross(tan_x, tan_y)
        normal /= np.linalg.norm(normal)

        # Make tan_y orthogonal to tan_x and normal to get orthonormal basis.
        tan_y = np.cross(normal, tan_x)
        tan_y /= np.linalg.norm(tan_y)

        frame = np.matrix(np.eye(4, 4))

        # Construct frame rotation part from orthonormal surface tangent and normal vectors.
        frame.A[0:3, 0] = tan_x
        frame.A[0:3, 1] = tan_y
        frame.A[0:3, 2] = normal

        # Differences from closest point to given point.
        dx = x - cl_x
        dy = y - cl_y

        # Now frame has the desired rotation.
        # Set the translation part at the closest point.
        px, py, pz = self.xyz_for_xy(cl_x, cl_y)

        frame.A[0:3, 3] = [px, py, pz]

        # Move along dut x and y (surface tangent) directions to extrapolate to given point.
        frame = frame * robotmath.xyz_to_frame(dx, dy, 0)

        # lose one degrees of freedom ( 6 -> 5 : TAFF has 5 degrees of freedom )
        a, b, c = tr.euler_from_matrix(frame)
        frame.A[0:3, 0:3] = tr.euler_matrix(0, b, c)[0:3, 0:3]  # just leave tilt and azimuth

        # add Z ( to the direction of plane normal )
        z_frame = robotmath.xyz_to_frame(0, 0, z)
        frame = frame * z_frame

        # correction transform
        frame.A[0:3, 3] += self._transform.A[0:3, 3]

        return frame

    def transform(self, frame):
        orientation = np.matrix(np.eye(4))
        orientation.A[0:3, 0:3] = frame.A[0:3, 0:3]

        x, y, z = robotmath.frame_to_xyz(frame)
        if hasattr(frame, 'meta'):
            frame = robotmath.matrix(self.frame_for_xyz(x, y, z), meta=frame.meta)
        else:
            frame = self.frame_for_xyz(x, y, z)

        frame = frame * orientation
        return frame

    @property
    def data(self):
        t = [[float(v) for v in a] for a in self._transform.A]
        return {"points": self._points, "grid_size": self._grid_size, "transform": t}

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height
