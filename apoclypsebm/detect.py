from sys import platform

WINDOWS = platform.startswith('win')
LINUX = platform.startswith('linux')
MACOSX = (platform == 'darwin')
