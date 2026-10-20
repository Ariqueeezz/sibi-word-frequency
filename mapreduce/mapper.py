#!/usr/bin/env python3
import sys
import re

for line in sys.stdin:
    words = re.findall(r"[^\W\d_]+", line.lower(), flags=re.UNICODE)
    for word in words:
        print("{}\t1".format(word))
