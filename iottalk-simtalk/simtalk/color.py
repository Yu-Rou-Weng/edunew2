import platform


class ColorBase:
    default = "\033[0m"
    data = "\033[1;33m"

    @classmethod
    def wrap(cls, color, s):
        """
        wrap string with color
        """
        if platform.system() == 'Windows':
            # If we want to support colored printing on Windows.
            # The easiest way is https://github.com/tartley/colorama,
            # but this introduces extra dependency.
            # The implementation for Windows is not small enought to self-shipped.
            return s

        return "{}{}{}".format(color, s, cls.default)


class SimTalkColor(ColorBase):
    logger = "\033[32m"
