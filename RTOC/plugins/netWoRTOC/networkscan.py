import os
import socket
import multiprocessing
import subprocess
import os


def pinger(job_q, results_q):
    """
    Do Ping
    :param job_q:
    :param results_q:
    :return:
    """
    DEVNULL = open(os.devnull, 'w')
    while True:

        ip = job_q.get()

        if ip is None:
            break

        try:
            #subprocess.check_call(['ping', '-c1', ip],
            #                      stdout=DEVNULL)
            subprocess.check_call(['ping', ip],
                                  stdout=DEVNULL)
            results_q.put(ip)
        except:
            pass

def get_my_ip():
    """
    Find my IP address
    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def map_network(pool_size=255):
    """
    Maps the network
    :param pool_size: amount of parallel ping processes
    :return: list of valid ip addresses
    """

    ip_list = list()

    # get my IP and compose a base like 192.168.1.xxx
    ip_parts = get_my_ip().split('.')
    base_ip = ip_parts[0] + '.' + ip_parts[1] + '.' + ip_parts[2] + '.'
    print(base_ip)
    # prepare the jobs queue
    jobs = multiprocessing.Queue()
    results = multiprocessing.Queue()

    pool = [multiprocessing.Process(target=pinger, args=(jobs, results)) for i in range(pool_size)]

    for p in pool:
        p.start()

    # cue hte ping processes
    for i in range(1, 255):
        jobs.put(base_ip + '{0}'.format(i))

    for p in pool:
        jobs.put(None)

    for p in pool:
        p.join()

    # collect he results
    while not results.empty():
        ip = results.get()
        ip_list.append(ip)

    return ip_list

import socket
from contextlib import closing

def check_socket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        if sock.connect_ex((host, port)) == 0:
            return True
        else:
            return False

def check_if_up(ip_address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.4)
    try:
        with closing(sock):
            sock.connect((str(ip_address), 135))
            return True
    except socket.error:
        return False

def map_port(pool_size=255, port=5050):
    ip_list = list()

    # get my IP and compose a base like 192.168.1.xxx
    ip_parts = get_my_ip().split('.')
    base_ip = ip_parts[0] + '.' + ip_parts[1] + '.' + ip_parts[2] + '.'
    print(base_ip)

    for i in range(pool_size):
        address = base_ip+str(i)
        if check_if_up(address):
            print(address+ " ...")
            if check_socket(address, port):
                print('Port '+str(port)+ ' is open.')
                ip_list.append(address)
            else:
                print('Port '+str(port)+ ' is closed.')
    return ip_list

if __name__ == '__main__':

    print('Mapping...')
    lst = map_network()
    print(lst)
    portlst = []
    for l in lst:
        if check_socket(l,5050):
            portlst.append(l)
    print(portlst)
