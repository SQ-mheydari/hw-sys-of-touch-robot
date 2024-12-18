from .Node import *
import sys
from os import listdir
from os.path import isfile, join, splitext
from scriptpath import join_script_root_directory


class TestsNode(Node):
    """
    Node that hosts test cases as child nodes.
    Test cases can be imported from a directory of Python modules.
    """
    def __init__(self, name):
        super().__init__(name)

        self.test_case_modules = None

    def import_test_cases(self, context, subdirectory=None, exclude=None):
        """
        Import test cases from specific directory and make them child nodes for the sequence.
        TODO: We should probably have different test case directories for one finger, two finger etc. tests.
        TODO: Each finger type could have its own TestsNode object.
        """

        directory = join_script_root_directory('testcases')

        if subdirectory is not None:
            directory = join(directory, subdirectory)

        # Append test case folder to path to be able to import as Python modules.
        sys.path.append(directory)

        # Import all test cases located in directory as class names and add them to the sequence
        importfiles_ = [splitext(f)[0] for f in listdir(directory) if isfile(join(directory, f))]

        # Remove duplicates. This is O(n^2), but it doesn't matter since count of testcases won't ever be high.
        importfiles = []
        [importfiles.append(item) for item in importfiles_ if item not in importfiles]

        modules = []

        # TODO: We should group one and two finger test cases somehow.
        for class_name in importfiles:

            if exclude is not None and class_name in exclude:
                continue

            module = __import__(class_name, globals(), locals(), [class_name], 0)

            # Create instance of test step class and add as child node.
            Test = getattr(module, class_name)
            self.add_child(Test(context))

            modules.append(module)

        self.test_case_modules = modules


def get_test_case_modules(node):
    """
    Get test case modules of test nodes under start node recursively.
    :param node: Node to start hierarchy traversal. Must be of type TestsNode.
    :return: List of test case modules.
    """

    test_case_modules = node.test_case_modules

    for child in node.children:
        if type(child) == TestsNode:
            test_case_modules += get_test_case_modules(child)

    return test_case_modules

