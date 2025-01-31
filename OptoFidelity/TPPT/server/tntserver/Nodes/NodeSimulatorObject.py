from .Node import *
import tntserver.globals
import math
import base64



class NodeSimulatorObject(Node):

    def __init__(self, name):
        super().__init__(name)
        self._texture_name = None
        self._texture_ppmm = None
        self._texture_size = None

    def _init(self, type, **kwargs):
        """

        :param type: string defining which kind of object: 'texture' == flat textured canvas object
        :param kwargs: parameters depending on type

        :param ppmm: pixels per millimeter on canvas
        :param width: object width in millimeters
        :param height: object height in millimeters
        :param draw: draw program. Commands:
            cls: clears screen with current draw color
            color <color>: changes current draw color. HTML colors. 'color white; color #fff;'
            circle <x y r line_width> line_width 0 == filled
            rect <x1 y1 x2 y2 line_width> line_width 0 == filled
            line <x1 y1 x2 y2> draw line between x1,y1 - x2,y2

            example:
                color white; cls; color white; rect 0 0 100 100 1; circle 50 50 50 2;
        :param simulator_parent_object: name of parent simulator object. Optional.

        """
        # Only initialize if using visual simulation.
        if "program_arguments" in kwargs:
            if not kwargs["program_arguments"].visual_simulation:
                return

        enabled = kwargs.get("enabled", True)
        if not enabled:
            return

        if type == 'texture':
            ppmm = float(kwargs['ppmm'])
            pos = kwargs['position']
            width = float(kwargs['width'])
            height = float(kwargs['height'])
            draw = str(kwargs['draw']) if 'draw' in kwargs else None
            image = str(kwargs['image']) if 'image' in kwargs else None
            parent_object_name = str(kwargs['simulator_parent_object']) if 'simulator_parent_object' in kwargs else None

            # euler angles (if given)
            for i in range(len(pos) - 3):
                pos[i+3] = math.radians(pos[i+3])

            c = tntserver.globals.simulator_instance

            object_name = "obj_" + self.name
            texture_name = "tex_" + self.name
            self._texture_name = texture_name
            self._texture_ppmm = ppmm
            self._texture_size = width, height
            self.rectangeMesh(object_name, pos, width, height, parent_object_name=parent_object_name)

            c.createDynamicTexture(texture_name, width * ppmm, height * ppmm)
            c.setObjectTexture(object_name, texture_name)

            if draw is not None:
                c.drawDynamicTexture(texture_name, draw, scale = ppmm)
            elif image is not None:
                with open(image, "rb") as file:
                    image_data = file.read()
                image_data = base64.encodebytes(image_data).decode("ascii")
                draw = "bitmap 0 0 {} {} {}".format(width, height, image_data)
                c.drawDynamicTexture(texture_name, draw, scale=ppmm)


        elif type == 'chessboard':
            ppmm = float(kwargs['ppmm'])
            pos = kwargs['position']
            width = float(kwargs['width'])
            height = float(kwargs['height'])
            bs = int(kwargs['bs'])
            bw = int(kwargs['bw'])
            bh = int(kwargs['bh'])
            parent_object_name = str(kwargs['simulator_parent_object']) if 'simulator_parent_object' in kwargs else None

            # euler angles (if given)
            for i in range(len(pos) - 3):
                pos[i+3] = math.radians(pos[i+3])

            c = tntserver.globals.simulator_instance

            object_name = "obj_" + self.name
            texture_name = "tex_" + self.name
            self._texture_name = texture_name
            self._texture_ppmm = ppmm
            self.rectangeMesh(object_name, pos, width, height, parent_object_name=parent_object_name)

            c.createDynamicTexture(texture_name, width * ppmm, height * ppmm)
            c.setObjectTexture(object_name, texture_name)

            draw = "color black;"

            ox = (width - bs * bw) * 0.5
            oy = (height - bs * bh) * 0.5

            for y in range(bh):
                for x in range(bw):
                    if ((x+y) & 1) == 0:
                        draw += "rect {} {} {} {} 0;".format(ox + x*bs, oy + y*bs, ox + x*bs+bs, oy + y*bs+bs)

            print(draw)
            c.drawDynamicTexture(texture_name, draw, scale=ppmm)



        elif type == 'blobs':
            ppmm = float(kwargs['ppmm'])
            pos = kwargs['position']
            width = float(kwargs['width'])
            height = float(kwargs['height'])
            margin = float(kwargs['margin'])
            radius = float(kwargs['radius'])
            parent_object_name = str(kwargs['simulator_parent_object']) if 'simulator_parent_object' in kwargs else None

            # euler angles (if given)
            for i in range(len(pos) - 3):
                pos[i + 3] = math.radians(pos[i + 3])

            draw = self.create_blob_target_program(width, height, margin, radius)

            c = tntserver.globals.simulator_instance

            object_name = "obj_" + self.name
            texture_name = "tex_" + self.name
            self._texture_name = texture_name
            self._texture_ppmm = ppmm
            self.rectangeMesh(object_name, pos, width, height, parent_object_name)

            c.createDynamicTexture(texture_name, width * ppmm, height * ppmm)
            c.setObjectTexture(object_name, texture_name)
            c.drawDynamicTexture(texture_name, draw, scale=ppmm)

        elif type == 'file':
            url = kwargs['url']

            pos = kwargs['position']
            # euler angles (if given)
            for i in range(len(pos) - 3):
                pos[i + 3] = math.radians(pos[i + 3])

            c = tntserver.globals.simulator_instance

            parent_object_name = str(kwargs['simulator_parent_object']) if 'simulator_parent_object' in kwargs else None

            c.addStl(url, parent_object_name, "", list(pos))

    def rectangeMesh(self, name, position, width, height, parent_object_name):

        dut_grid_size = 2
        px, py, pz = 0, 0, 0

        a = [[{} for i in range(dut_grid_size)] for j in range(dut_grid_size)]
        for y in range(dut_grid_size):
            for x in range(dut_grid_size):
                xx = px + width * x / (dut_grid_size - 1)
                yy = py + height * y / (dut_grid_size - 1)
                zz = pz

                a[x][y] = [xx, yy, zz, x / (dut_grid_size - 1), (dut_grid_size - 1 - y) / (dut_grid_size - 1)]


        ax = []
        ay = []
        az = []
        au = []
        av = []
        for y in range(dut_grid_size - 1):
            for x in range(dut_grid_size - 1):
                p0 = a[x][y]
                p1 = a[x + 1][y]
                p2 = a[x][y + 1]
                p3 = a[x + 1][y + 1]

                # 1st triangle
                ax.append(p0[0])
                ax.append(p1[0])
                ax.append(p3[0])
                ay.append(p0[1])
                ay.append(p1[1])
                ay.append(p3[1])
                az.append(p0[2])
                az.append(p1[2])
                az.append(p3[2])
                au.append(p0[3])
                au.append(p1[3])
                au.append(p3[3])
                av.append(p0[4])
                av.append(p1[4])
                av.append(p3[4])

                # 2nd triangle
                ax.append(p0[0])
                ax.append(p3[0])
                ax.append(p2[0])
                ay.append(p0[1])
                ay.append(p3[1])
                ay.append(p2[1])
                az.append(p0[2])
                az.append(p3[2])
                az.append(p2[2])
                au.append(p0[3])
                au.append(p3[3])
                au.append(p2[3])
                av.append(p0[4])
                av.append(p3[4])
                av.append(p2[4])


        c = tntserver.globals.simulator_instance
        c.addObject(name, parent_name=parent_object_name)
        c.moveObject(name, position)
        c.addMesh(name, ax, ay, az, au, av)

    def create_blob_program(self, x, y, index, radius=10):
        numbits = 8
        prg = ""

        index = int(index)
        numbits = int(numbits)

        r = radius / 2.0
        r1 = r * 2.0

        data = []

        # sync mark
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)

        # print("index:", index)
        # add bits

        bits = []
        parity = 0
        for i in range(numbits):
            bit = 2 ** i
            v = index & bit
            if v != 0:
                parity ^= 1
                bits.append(1)
            else:
                bits.append(0)
        bits.append(parity)

        for v in bits:
            if v != 0:
                data.append(1)
                data.append(1)
                data.append(1)
                data.append(1)
                data.append(0)
                data.append(0)
            else:
                data.append(1)
                data.append(1)
                data.append(0)
                data.append(0)
                data.append(0)
                data.append(0)

        numbits = len(data)

        # draw pie slice for every '1' bit
        for i in range(len(data)):
            b = data[i]

            dat = b & 1

            a0 = -90 + i * 360 / (numbits)
            a1 = a0 + 360 / numbits + 1

            if b & 1:
                prg += 'circle {} {} {} {} {} {};'.format(x, y, r1, 0, a0, a1)

        # draw filled circle in the middle ( blob for blob detector )
        prg += 'circle {} {} {} 0;'.format(x, y, r)

        # draw outer ring
        ro = r * 0.6
        prg += 'circle {} {} {} {};'.format(x, y, r1, ro)

        # clear dot to middle
        ro = r * 0.4
        prg += 'color white; circle {} {} {} 0; color black;'.format(x, y, ro)

        return prg

    def create_blob_target_program(self, width, height, margin, radius):
        prg = "color white; cls; color black;"

        for y in range(0, 16, 1):
            for x in range(0, 16, 1):
                xx = radius + margin + x * (width - radius * 2 - margin * 2) / 15
                yy = radius + margin + y * (width - radius * 2 - margin * 2) / 15
                prg += self.create_blob_program(xx, yy, (y * 16 + x) & 255, radius)

        return prg

    def draw(self, program: str):
        c = tntserver.globals.simulator_instance
        c.drawDynamicTexture(self._texture_name, program, scale=self._texture_ppmm)

    def draw_image(self, image_data):
        """

        :param image: jpeg or png image as byte array data
        """
        image_data = base64.encodebytes(image_data).decode("ascii")
        draw = "bitmap 0 0 {} {} {}".format(self._texture_size[0], self._texture_size[1], image_data)
        c = tntserver.globals.simulator_instance
        c.drawDynamicTexture(self._texture_name, draw, scale=self._texture_ppmm)

    @json_out
    def get_draw(self, program: str):
        self.draw(program)
        return "ok"