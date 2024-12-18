This is a txt file on purpose, having only the actual help texts as markdown makes automatic document rendering easier

Here are some tips and tricks for the help writers:
- all the help texts should be written as markdown (md) files in folder tnt_ui/tnttool/res/help_content
- the name of the md file should be <help_name>.md, help_name is the name that is used to refer to the
specific help field in the code
- pictures are also supported, they should be put into folder tnt_ui/tnttool/res/images
- pictures can be referred in the md with for example
![Image caption that will show up in user manual.](ui_help_images/example.png "example")
- Note that "ui_help_images" is a magic identifier that is handled differently for embedded UI help and compiled user manual.
- It is recommended to make images as svg using Inkscape
- Help markdown files can use SVG image directly but there must also be a PDF version with the same name that will be used in user manual
- Help markdown files can use PNG images directly but there must also be a JPG version with the same name that will be used in user manual
- remember that characters such as '"' or '<' might break the text since it is handled as html

About the tooltip files:
- These are the texts shown when the mouse is hovered on top of the text/button etc.  Headers are the
names of the tooltips. They are used as keys to get the actual text content. All the following
text before next header is shown. Tooltip widget cannot show images. However, if these are ever used for
exporting help, images can be added. The parsing function discards the lines that include pictures
(or anything that starts with '[')

Additional things to remember while writing help:
- the better the help the less there will be customer emails asking random questions
- picture tells more than a thousand words
- the reader of the help is likely to know less about the system than you :)