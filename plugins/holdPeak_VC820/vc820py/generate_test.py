#!/usr/bin/python
from random import randrange
import vc820
import sys

messages_to_create = 50
counter = 0

def _generate_bytes():  
    bts = bytes()
    for segment in range (1,15):
        random = randrange(0,16)
        number = (segment<<4)|random
        bts += bytes([number])
    return(bts)

def get_random_list(count):
    lst = []
    for i in range(count):
        while True:
            global counter
            counter += 1
            bts = _generate_bytes()
            mm = None
            try:
                mm = vc820.MultimeterMessage(bts)
            except (ValueError, AttributeError) as e:
                continue
            print("found valid message (%d): %s - %s"%(i,bts.hex(),str(mm)))
            lst.append(bts)
            break
    return lst


if __name__ == "__main__":
    filename = sys.argv[1]
    testvaluesfile = open(filename, "wb")

    for item in get_random_list(messages_to_create):
        testvaluesfile.write(item)

    print("Tried %d Messages, found %d valid"%(counter, messages_to_create))
