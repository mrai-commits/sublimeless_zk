# -*- coding: utf-8 -*-
"""
Minimal replacement for the stdlib `imghdr` module, which was removed in
Python 3.13. Only the formats Sublimeless handles are detected.
"""


def what(path):
    """Return 'png', 'gif', 'jpeg' or None for the image file at `path`."""
    try:
        with open(path, 'rb') as f:
            head = f.read(32)
    except OSError:
        return None
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if head.startswith(b'\xff\xd8'):
        return 'jpeg'
    return None
