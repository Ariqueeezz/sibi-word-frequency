#!/usr/bin/env python3
import sys

current_word = None
current_count = 0

for line in sys.stdin:
    line = line.rstrip("\n")
    parts = line.split("\t", 1)

    if len(parts) != 2:
        continue

    word, count = parts

    try:
        count = int(count)
    except ValueError:
        continue

    if word == current_word:
        current_count += count
    else:
        if current_word is not None:
            print("{}\t{}".format(current_word, current_count))

        current_word = word
        current_count = count

if current_word is not None:
    print("{}\t{}".format(current_word, current_count))
