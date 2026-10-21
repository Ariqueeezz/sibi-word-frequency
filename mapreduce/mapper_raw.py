import sys
import re

for line in sys.stdin:
    words = re.findall(
        r"[^\W\d_]+",
        line.lower(),
        flags=re.UNICODE
    )

    for word in words:
        if len(word) > 1:
            print("{}\t1".format(word))
