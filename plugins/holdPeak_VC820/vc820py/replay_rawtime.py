from sys import argv,stdout
from time import sleep

infile = open(argv[1])
outfile = stdout.buffer

def readfile():
    global last_time
    for line in infile:
        sline = line.strip()
        current_time = float(sline.split(" ")[0])
        sleep(current_time-last_time)
        message = bytes.fromhex(sline.split(" ")[1])
        outfile.write(message)
        outfile.flush()
        last_time = current_time

while True:
    last_time = 0
    readfile()
    infile.seek(0)

    
