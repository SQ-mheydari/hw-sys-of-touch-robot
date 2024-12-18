import json

import numpy as np

from tntserver import __version__
import tntserver.globals
from tntserver import robotmath
from tntserver.Nodes import TnT
from tntserver.Nodes.Node import *


class TnT(Node):

    @json_out
    def get_version(self):
        return {"tnt_version": str(__version__)}

    @html_out
    def get_help(self, **kwargs):
        """ Gives you the whole REST api in nice formatted HTML page

        """

        template = """

        <html>
        <head>
        <meta charset="utf-8"/>
        </head>
        <style>
            body
                {
                font-family:Tahoma, Geneva, sans-serif;
                background-color:#fefefe;
                }
            .page
                {
                width:auto;
                margin:20px;
                padding:10px;
                border-radius:13px;
                box-shadow:1px 5px 10px gray;
                background-color:white;
                box-sizing:border-box;
                }
            .doc
                {
                font:11px monospace;
                }
        </style>

        <body>
            <div class="help">__help__</div>
        </body>
        </html>

        """

        classes = {}
        self.fillClasses(self, classes)
        lis = []
        for obj_name in classes:
            obj = classes[obj_name]
            #lis.append(obj.help())
            lis.append(obj)

        s = ""
        s += "<h1 style='text-align:center;'>TnT api reference</h1>"
        for obj in sorted(lis, key=lambda o: o.__class__.__name__):
            # Skip nodes that are not real nodes
            if not hasattr(obj, 'help'):
                continue
            item = obj.help()
            s += "<div class='page'>"
            s += "<h2>" + item["classname"] + "</h2>"

            if obj.__doc__ is not None:
                s += "<blockquote class='doc'>"
                for p in obj.__doc__.split("\n"):
                    s += "<p>" + p + "</p>"
                s += "</blockquote>"

            s += "<h3>Functions</h3>"
            functions = item["functions"]
            #for ftype, fname in sorted(functions, key=str.lower):
            for ftype, fname in functions:
                path = []
                p = item["object"]
                while p is not None:
                    path.append(p.name)
                    p = p.parent

                lnk = "http://127.0.0.1:" + str(tntserver.globals.server_port) + "/"
                for name in path[::-1]:
                    lnk += name
                    lnk += "/"
                lnk += fname

                s += "<b>" + str.upper(ftype) + "</b>  "
                s += "<a href=" + lnk + "><b>" + fname + "</b></a>"

                s += "("

                p = item["object"]
                #func = getattr(p, "api_" + f)
                func = getattr(p, ftype + "_" + fname)

                bb = func.__annotations__

                for argname in sorted(bb, key=str.lower):
                    argclass = bb[argname]
                    s += "<i>" + argname + " </i>"
                    s += "(" + str(argclass).replace("<class '","").replace("'>","") + "), "

                if len(bb) > 0:
                    s = s[:-2]
                s += ")"

                s += "<br/>"

                func_help = help(func)
                if func_help is None:
                    func_help = func.__doc__
                if func_help is None:
                    func_help = func.__class__.__doc__
                if func_help is None:
                    func_help = func.__mro__.__doc__
                if func_help is None:
                    func_help = "no help available"
                s += "<blockquote class='doc'>"
                for p in func_help.split("\n"):
                    s += "<p>" + p + "</p>"
                s += "</blockquote>"

            if len(functions) == 0:
                s += "-<br/>"


            s += "<h3>Properties</h3>"
            properties = item["properties"]
            for pname in sorted(properties):
                p = properties[pname]
                s += "<b>" + pname + " </b>"
                s += self.param_to_infotext(p)
                #s += "<i>(" + p["type"] + ")</i> "
                #s += "<u>" + p["value"] + "</u>"
                s += "<br/>"

            if len(properties) == 0:
                s += "-<br/>"

            s += "<hr/>"
            s += "</div>"

        s = template.replace("__help__", s)
        return s

    def param_to_infotext(self, p, tab=0):
        s = ""
        prefix = " " * (4*tab)
        if isinstance(p, dict):
            for name in p:
                s += prefix + "<b>{}</b><br/>".format(name)
                v = self.param_to_infotext(p[name])
                s += prefix + "  {}<br/>".format(v)
        elif isinstance(p, list) or isinstance(p, np.ndarray) or isinstance(p, np.matrix):
            if isinstance(p, np.matrix):
                p = p.A
            for v in p:
                s += prefix + "  {}<br/>".format(self.param_to_infotext(v))
        else:
            s += str(p)
        return s

    def fillClasses(self, obj, classes):
        classes[obj.__class__] = obj
        if hasattr(obj, 'children'):
            for child_name in obj.children:
                child = obj.children[child_name]
                self.fillClasses(child, classes)

    @html_out
    def get_tree(self, **kwargs):
        """ Outputs the current tree structure.

        """
        template = """

        <html>
        <head>
        <meta charset="utf-8"/>
        </head>
        <style>
            body
                {
                font-family:Tahoma, Geneva, sans-serif;
                background-color:#fefefe;
                }
            .page
                {
                width:auto;
                margin:20px;
                padding:10px;
                border-radius:13px;
                box-shadow:1px 5px 10px gray;
                background-color:white;
                box-sizing:border-box;
                }
            .node
                {
                margin:20px;
                background-color:transparent;
                }
            .nodebg
                {
                padding:10px;
                position:relative;
                top:0px;
                left:0px;
                width:300px;
                background-color:white;
                border-radius:13px;
                box-sizing:border-box;
                box-shadow:1px 5px 10px gray;

                }
            .doc
                {
                font:11px monospace;
                }
        </style>

        <body>
            <div class="help">__tree__</div>
        </body>
        </html>

        """

        # If optional parameter object_tree is given with value True, then display the object node tree.
        object_tree = kwargs.get("object_tree", False)

        s = ""
        s += self.tree_item(Node.root, object_tree)
        s = template.replace("__tree__", s)
        return s


    def tree_item(self, node, object_tree=False):

        def param_to_infotext(p, tab=4):
            s = ""
            if tab == 4:
                s += "<div style='font-family:monospace; margin-left:{}px;'>".format(tab*10)

            if isinstance(p, dict):
                for name in p:
                    s += "<b>{}</b>\n".format(name)
                    v = self.param_to_infotext(p[name], tab+4)
                    s += "{}\n".format(v)
            elif isinstance(p, list) or isinstance(p, np.ndarray) or isinstance(p, np.matrix):
                if isinstance(p, np.matrix):
                    p = p.A
                for v in p:
                    s += "{}\n".format(self.param_to_infotext(v, tab+4))
            else:
                s += str(p)

            if tab == 4:
                s += "</div>"

            return s

        ps = ""
        property_names = [p for p in dir(node.__class__) if isinstance(getattr(node.__class__, p), property)]
        for name in property_names:
            value = ""
            try:
                value = getattr(node, name)
            except:
                pass


            value = param_to_infotext(value)
            ps += "<b>{}</b>{}<br/>".format(name, value)

        s = "<div class='node'><div class='nodebg'><div style=''>" + node.name + "</div><div style=''>" + node.__class__.__name__ + "<br/>" + ps + "<br/>" + "</div></div>"
        if object_tree:
            for childname in node.object_children:
                child = node.object_children[childname]
                s += self.tree_item(child, object_tree)
        else:
            for childname in node.children:
                child = node.children[childname]
                s += self.tree_item(child, object_tree)

        s += "</div>"
        return s


    @ascii_out
    def get_test(self):

        node_list = self._get_children()

        s = ""
        lf = "\n"
        tab = "    "
        for node in node_list:
            s += node.name + " : " + node.__class__.__name__ + lf
            s += tab + "@init" + lf

            try:
                bb = getattr(node, "init")
                bb = bb.__annotations__
                for argname in sorted(bb, key=str.lower):
                    argclass = bb[argname]
                    s += tab*2 + argname + lf
            except:
                pass

            s += lf
            s += tab + "@properties" + lf

            help = node.help()
            properties = help["properties"]
            for propertyname in properties:
                p = properties[propertyname]
                type = p["type"]
                value = p["value"]
                s += tab*2 + propertyname + " = " + str(value) + lf

            s += lf

        return s

    @json_out
    def get_contexts(self):
        contexts = [self.name]

        for child in self._get_children():
            if not Node.private_property(child, "frame") and not np.array_equal(np.eye(4), child.frame):
                contexts.append(child.name)

            elif getattr(child, "surface", None) is not None:
                contexts.append(child.name)

        return {"contexts": contexts}

    def _get_children(self):
        def get_nodes(node, list):
            list.append(node)
            for childname in node.children:
                child = node.children[childname]
                get_nodes(child, list)

        node_list = []
        get_nodes(self, node_list)
        return node_list

    @json_out
    def get_translate(self, from_context, to_context, pose=None, frame=None):
        """
        translates frames from context to another
        :param from_context:
        :param to_context:
        :param pose:
        :param frame:
        :return: pose or frame, depending which one was given as input
        """
        if pose is None and frame is None:
            raise Exception("translate needs pose or frame")

        if pose is not None:
            if isinstance(pose, str):
                pose = json.loads(pose)
            frame = TnT.tnt_pose_to_frame(**pose)
        elif frame is not None:
            if isinstance(frame, str):
                frame = json.loads(frame)
            frame = np.matrix(frame)
        else:
            frame = robotmath.identity_frame()

        from_node = Node.find(from_context)
        to_node = Node.find(to_context)
        result_frame = robotmath.translate(frame, from_node, to_node)

        if frame is not None:
            return [[float(v) for v in a] for a in result_frame.A]

        return TnT.pose_to_tnt_roll_pose(result_frame)