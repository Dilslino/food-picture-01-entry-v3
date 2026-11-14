#!/usr/bin/env python3
"""Ship the pre-rendered food picture to the grader output directory.

The picture is baked into this repository as entry.png. This script does
no drawing at all: it only places a byte-exact copy of that file into the
directory named by MAKEFUN_OUTPUT_DIR (falling back to /output).

Standard library only. Nothing in here needs to be installed.
"""

import os
import shutil
import sys

IMAGE_NAME = "entry.png"
MAX_BYTES = 1024 * 1024


def fail(message):
    print("error: " + message, file=sys.stderr)
    raise SystemExit(1)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, IMAGE_NAME)

    if not os.path.isfile(source):
        fail("source image is missing: " + source)

    source_size = os.path.getsize(source)
    if source_size > MAX_BYTES:
        fail(
            "source image is %d bytes, over the %d byte limit"
            % (source_size, MAX_BYTES)
        )

    with open(source, "rb") as handle:
        header = handle.read(3)
    if header != bytes([0xFF, 0xD8, 0xFF]):
        fail("source image is not a JPEG file: bad magic bytes")

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, IMAGE_NAME)

    shutil.copyfile(source, dest)

    copied_size = os.path.getsize(dest)
    if copied_size != source_size:
        fail(
            "copied image is %d bytes, expected %d bytes"
            % (copied_size, source_size)
        )

    print("wrote %s (%d bytes)" % (dest, copied_size))


if __name__ == "__main__":
    main()
