from tntserver.Nodes.Node import *
import os
from tntserver.globals import root_path


class NodeDoc(Node):

    @html_out
    def get_api(self):

        html = ""

        html += '<div class="title">TnT Server Documentation</div>'
        html += '<h1>Api Documentation</h1>'
        html += '<h2>List of REST api calls</h2>'
        html += self.__api_list_html()
        html += self.__detail_api_html()

        html = self.__body_to_template(html)

        return html

    def __api_list_html(self):
        def node_to_html(node: Node, path: str = ""):
            # html = "<h3>{}</h3>".format(node.name)
            html = ""

            f_get = [('get', p[4:]) for p in dir(node.__class__) if p[:4] == "get_"]
            f_put = [('put', p[4:]) for p in dir(node.__class__) if p[:4] == "put_"]
            f_post = [('post', p[5:]) for p in dir(node.__class__) if p[:4] == "post_"]
            fs = f_get + f_put + f_post

            for f in fs:
                # html += "<b>{}</b> {}<br/>".format(f[0], f[1])
                html += "<tr><td>{}</td><td>{}/{}</td></tr>".format(f[0], path, f[1])

            for child in node.children.values():
                html += node_to_html(child, path + "/" + node.name + "")

            return html

        html = "<table>"
        html += node_to_html(Node.root)
        html += "</table>"
        return html

    def __detail_api_html(self):
        html = "<h1>API details</h1>"

        def node_to_html(node: Node, prefix_filter=""):

            html = ""

            html += "<table>"

            html += "<tr>"
            html += "<th>Function</th>"
            html += "<th>Parameters</th>"
            html += "<th>Description</th>"
            html += "<th>Value</th>"

            for name in dir(node.__class__):
                if name[0] == '_':
                    # ignore private methods
                    continue
                #
                # only document functions with given filter, eg. GET_ PUT_ POST_
                #
                if not str.startswith(name, prefix_filter):
                    continue

                #
                # fill in Class Documentation or warning if missing.
                #
                try:
                    value = getattr(node, name)
                    doc = value.__doc__
                except Exception as e:
                    value = str(e)
                if doc == "" or doc is None or doc =="None":
                    doc = "<div style='background-color:red; color:white;'>TO DO</div>"

                #
                # fill in function parameter annotations
                # or warning if missing
                #
                info = ""
                try:
                    ans = value.__annotations__
                    if len(ans):
                        for argname in ans:
                            argclass = ans[argname]
                            s = "<i>" + argname + " </i>"
                            s += "(" + str(argclass).replace("<class '", "").replace("'>", "") + ")"
                            info += s + "<br/>"
                    else:
                        info = "<div style='background-color:red; color:white;'>TO DO</div>"

                    print(info)
                except:
                    info = ""

                html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(name, info, doc, str(value))

            html += "</table>"
            return html

        def node_to_html_recursive(node: Node):
            html = "<div class='page'>"

            html += "<h2>{} {}</h2>".format(node.name, node.__class__.__name__)
            html += "<i>{}</i><br/>".format(str(node.__class__.__doc__))

            html += "<h3>GET</h3>"
            html += node_to_html(node, prefix_filter="get_")

            html += "<h3>PUT</h3>"
            html += node_to_html(node, prefix_filter="put_")

            html += "<h3>POST</h3>"
            html += node_to_html(node, prefix_filter="post_")

            for child in node.children.values():
                html += node_to_html_recursive(child)

            html += "</div>"
            return html

        html += node_to_html_recursive(Node.root)
        return html


        html += node_to_html(Node.root)
        return html


    def __body_to_template(self, body):
        """
        Inserts body html content to document template.
        :param body: html string including everything that goes inside <body> tag
        :return: whole web page as string
        """
        style = """
        <style>

body
	{
	font-family: "Calibri Light", sans-serif;
	counter-reset: h1counter;
	}

.title
	{
	font-size: 28.0pt;
	color: black;
	letter-spacing: -.5pt;
	}

.subtitle
	{
	margin-bottom: 12.0pt;
	line-height: 107%;
	text-autospace: none
	margin: 0cm;
	margin-bottom: .0001pt;
	font-size: 12.0pt;
	}
	
.page
    {
    //page-break-after: always;
    }
    
h1, h2, h3, h4, h5 
    {
    page-break-after: avoid;    
    }    

h1:before
	{
	content: counter(h1counter) " ";
	counter-increment: h1counter;
	//counter-reset: h2counter;
	}

h2:before
	{
	content: counter(h1counter) "." counter(h2counter) " ";
	counter-increment: h2counter;
	//counter-reset: h3counter;
	}

h3:before 
	{
	content: counter(h1counter) "." counter(h2counter) "." counter(h3counter) " ";
	counter-increment: h3counter;
	}

h1
	{
	counter-reset: h2counter;
	font-size: 14pt;
	line-height: 14pt;
	font-weight: bold;

	}

h2
	{
	page-break-before: always;
	counter-reset: h3counter;
	font-size: 12pt;
	line-height: 12pt;
	font-weight: bold;
	}

h3
	{
	font-size: 10pt;
	line-height: 12pt;
	font-weight: bold;
	}

.body
	{
	line-height: 12pt
	font-size: 10pt;
	color: black;

	margin-bottom: 8.0pt;
	}

table
	{
    page-break-inside: avoid;
	-webkit-border-horizontal-spacing: 2px;
	-webkit-border-vertical-spacing: 2px;
	border-collapse: collapse;
	border: none;
	}

tr	
	{
	border-collapse: collapse;
	}

th
	{
	border: 1pt solid black;
	background: white;
	padding: 0cm 5.4pt 0cm 5.4pt;
	border-collapse: collapse;
	font-size: 10pt;
	font-weight: bold;
	}

td
	{
	border: 1pt solid black;
	background: white;
	padding: 0cm 5.4pt 0cm 5.4pt;
	border-collapse: collapse;
	font-size: 10pt;
	font-weight: 200;
	}


</style>
        """

        head = """
        <head><meta charset="utf-8"/></head>
        """

        html = "<html>" + style + head + "<body>" + body + "</body></html>"

        return html



