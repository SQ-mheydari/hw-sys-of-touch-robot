import logging


class PatternFilter(logging.Filter):

    def __init__(self, ignore):
        # Ensure backward compatibility with old logging configs.
        if isinstance(ignore, str):
            self.ignore = [ignore]
        else:
            self.ignore = ignore

    def filter(self, record):
        return not any(i in record.getMessage() for i in self.ignore)
