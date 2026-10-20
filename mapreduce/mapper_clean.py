#!/usr/bin/env python3
import sys
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STOPWORDS_FILE = os.path.join(SCRIPT_DIR, "stopwords_id.txt")

with open(STOPWORDS_FILE, "r", encoding="utf-8") as f:
    stopwords = {
        line.strip().lower()
        for line in f
        if line.strip()
    }

for line in sys.stdin:
    words = re.findall(
        r"[^\W\d_]+",
        line.lower(),
        flags=re.UNICODE
    )

    for word in words:
        if len(word) > 1 and word not in stopwords:
            print("{}\t1".format(word))
