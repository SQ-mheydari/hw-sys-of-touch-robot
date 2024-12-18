import TPPTAnalysisSW


class MetaVersion(type):
    _major, _minor, _patch = TPPTAnalysisSW.__version__.split(".")[:3]
    _build = "0 (rnd)"
    _revision = "0"
    _date = ""

    @property
    def major(cls):
        """ Major version """
        return cls._major

    @property
    def build(cls):
        """ Build number """
        return cls._build

    @property
    def minor(cls):
        """ Release number """
        return cls._minor

    @property
    def patch(cls):
        """ Release number """
        return cls._patch

    @property
    def revision(cls):
        """ Revision number """
        return cls._revision

    @property
    def date(cls):
        """ Build date """
        return cls._date

    @property
    def simple(cls):
        """
        Software version: <major>.<release>

        Access software version from software:
            #>>> from info.version import Version
            ... Version.simple
        """
        return "%s.%s.%s" % (
            cls.major,
            cls.minor,
            cls.patch)

    @property
    def software(cls):
        """
        Software version: <major>.<release>.<build> rev. <number> [date]

        Access software version from software:
         from info.version import Version
            ... Version.software
        """
        return "%s.%s.%s rev. %s %s" % (
            cls.major,
            cls.minor,
            cls.build,
            cls.revision,
            cls.date)

    @property
    def api(self):
        """
        RESTful API version: <major>.<minor>

        Major -- Change(s) breaking current API increases major number by one:

            * Not backwards compatible
            * Removing something from API (methods or parameters)
            * Changing how method functions or meaning of a parameter

        Minor -- Changes(s) adding something to API but not breaking it
        increases the minor version by one:

            * 100% backwards compatible
            * Adding new methods (e.g., robot/Move)
            * Adding new parameters (e.g., robot/Move + x=2)

        API version is always a string. Access from software:
            #>>> from info.version import Version
            ... Version.api_version

        """
        return '1.0'

#
# Example of API update
#
# API 1.2
#   Finger API:
#       * Tap [x, y, z, duration]
#       * DoubleTap [x, y, z, duration, lift, interval]
#
class Version(object,  metaclass=MetaVersion):
    """
    API 1.0
        Initial version by Sami Laine
    """

    #__metaclass__ = MetaVersion


__version__ = Version.software
