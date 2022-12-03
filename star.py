from _thread import *
import threading
import socket
import time
import random
import os
import sys

CSS_PORT = random.randint(3000, 8000)        # Choose a random port to host the simulator on
host = '127.0.0.1'
NODES = []
DEBUG = True
ACTIVE = False
BUFFER = 260
NUM = 10
CAS = 5
ALL_CONNECTED = False
MAKE_NODES = False
NUM_CONNECTED = 0
PACKETS_RECEIVED = 0
ABORTED = False

def generate_input(network, curr, num, cas):      # Generate random input files given a number of nodes
    words = ['networks', 'pc', 'trees', 'extra', 'moment', 'pickle', 'book', 'lunch', 'no', 'free', 'big']
    output = ''
    for i in range(3):
        net = random.randint(0, cas-1)
        no = random.randint(0, num-1)
        while no == curr and net == network:
            no = random.randint(0, num-1)
            net = random.randint(0, cas-1)
        output += f'{net}_{no}:'
        for i in range(3):
            output += random.choice(words) + ' '
        output += '\n'
    return output

class Frame:
    def __init__(self):
        self.src = None
        self.dest = None
        self.size = None
        self.data = None

    def __init__(self, bytes):
        bytes = bytes.split(':')
        self.src = str(bytes[0])
        self.dest = str(bytes[1])
        self.size = int(bytes[2])
        self.data = bytes[3]

    def enc(self):
        return f'{self.src}:{self.dest}:{self.size}:{self.data}'.encode()

def node(net, id):
    global ACTIVE
    global NUM_CONNECTED
    global PACKETS_RECEIVED
    sock = socket.socket()
    sock.settimeout(3)
    try:    # Attempt to connect to switch
        while sock.connect_ex((host, CSS_PORT + net + 1)) != 0:
            if not ACTIVE: 
                sock.close()
                if DEBUG: print(f"Node {net}_{id} shutting down...")
                exit()
            print(f"Node {net}_{id}: Attempting to connect")
            time.sleep(random.uniform(0.5, 2))      # Ensure no overlap between nodes
    except socket.error as e:
        print(str(e))
    sock.send(f"{net}_{id}".encode())
    NUM_CONNECTED += 1
    while not ALL_CONNECTED:    # Wait until all nodes are connected to start sending frames
        if not ACTIVE:
            sock.close()
            if DEBUG: print(f"Node {net}_{id}: Shutting down...")
            exit()
        time.sleep(1)
    with open(f'node{net}_{id}output.txt', 'w+') as outfile:      # Open input and output files for read and writing
        infile = open(f'node{net}_{id}.txt', 'r')
        lines = infile.readlines()
        for line in lines:      # Loop through input lines and get them to their destinations
            if not ACTIVE: break
            line = line.strip().split(':')
            sock.send(Frame(f"{net}_{id}:{str(line[0])}:{len(line[1])}:{line[1]}").enc())
            ack = False
            attempts = 0
            while not ack:     # Ensure an acknowledgement frame is received, otherwise retry the send
                if attempts >= 3:
                    sock.send(Frame(f"{net}_{id}:{str(line[0])}:{len(line[1])}:{line[1]}").enc())
                    attempts = 0
                try:
                    if not ACTIVE: break
                    data = sock.recv(BUFFER)
                    if not data:
                        break
                    data = Frame(data.decode())
                    if data.size == 0:
                        ack = True
                    else:
                        if data.dest.split("_")[1] == str(id):
                            outfile.write(f"{data.src}: {data.data}\n")
                            print(f"Node {net}_{id}: Received '{data.data}' from node {data.src}")
                            sock.send(Frame(f"{net}_{id}:{data.src}:{0}:").enc())
                except TimeoutError:
                    attempts += 1
        attempts = 0
        while ACTIVE:       # Catch any remaining frames sent to this node after sending
            try:
                data = sock.recv(BUFFER)
                if not data:
                    break
                data = Frame(data.decode())
                outfile.write(f"{data.src}: {data.data}\n")
                print(f"Node {net}_{id}: Received '{data.data}' from node {data.src}")
                sock.send(Frame(f"{net}_{id}:{data.src}:{0}:").enc())
                PACKETS_RECEIVED += 1
            except TimeoutError:
                attempts += 1

        if DEBUG: print(f"Node {net}_{id}: Shutting down...")
        sock.close()



def switch(id):       # Main switch class manages slave threads and sends frames to connected nodes
    global ACTIVE
    queue = []
    switch_table = {}
    css = socket.socket()
    css.settimeout(3)
    def css_slave(conn):        # Slave is in charge of receiving and putitng frames in frame buffer
        global ACTIVE
        print(f"CAS {id}: CSS connected.")
        while True:
            try:
                if not ACTIVE: break
                data = conn.recv(BUFFER)
                if not data:
                    break
                # conn.sendall(str.encode(response))
                queue.append(Frame(data.decode()))
                # print(f"CAS {id}: Received a packet and dest is {queue[-1].dest}")
            except TimeoutError:
                pass
        conn.close()

    def slave(conn):        # Slave is in charge of receiving and putitng frames in frame buffer
        global ACTIVE
        msg = str(conn.recv(BUFFER).decode()).split("_")
        id = str(msg[1])
        net = str(msg[0])
        print(f"Node {net}_{id}: Connected.")
        switch_table[id] = conn
        while True:
            try:
                if not ACTIVE: break
                data = conn.recv(BUFFER)
                if not data:
                    break
                # conn.sendall(str.encode(response))
                queue.append(Frame(data.decode()))
                # print(f"Received a packet and dest is {queue[-1].dest}")
            except TimeoutError:
                pass
        conn.close()

    def master_slave():     # Master slave manages slave threads and the connections
        global ACTIVE
        slaves = []
        sock = socket.socket()
        sock.settimeout(3)
        try:
            sock.bind((host, CSS_PORT + 1 + id))
        except socket.error as e:
            print(str(e))
        print(f'CAS {id}: Listening...')
        sock.listen(5)
        attempts = 0
        while True:     # Main loop for master slave. Makes connections and a thread for each to handle it
            try:
                if not ACTIVE: break
                client, address = sock.accept()
                print(f'CAS {id}: Accepted connection ' + address[0] + ':' + str(address[1]))
                # start_new_thread(slave, (Client, ))
                slaves.append(threading.Thread(target=slave, args=(client, )))
                slaves[-1].start()
            except TimeoutError:
                # attempts += 1
                pass
        print(f"CAS {id}: Shutting down...")
        sock.close()

    try:    # Attempt to connect to switch
        while css.connect_ex((host, CSS_PORT)) != 0:
            if not ACTIVE:
                css.close()
                if DEBUG: print(f"CAS {id} shutting down...")
                exit()
            print(f"CAS {id}: Attempting to connect")
            time.sleep(random.uniform(0.5, 2))      # Ensure no overlap between nodes
    except socket.error as e:
        print(str(e))
    css.send(f"{id}".encode())
    css_handler = threading.Thread(target=css_slave, args=(css,))
    css_handler.start()
    ms = threading.Thread(target=master_slave)
    ms.start()
    while True:     # Main loop for looking through frame buffer and send each packet to their destination
        if not ACTIVE: break
        if len(queue) > 1:
            # print("dealing with a packet")
            packet = queue.pop(0)
            # print(f"dest is {packet.dest}")
            if packet.dest.split("_")[0] == str(id):
                if switch_table[packet.dest.split("_")[1]] is None:       # If a destination node is not in the switch table, send it to all nodes
                    for conn in switch_table:
                        conn.send(packet.enc())
                switch_table[packet.dest.split("_")[1]].send(packet.enc())
                # print(f"CAS {id}: sent packet to node {packet.dest.split('_')[1]}")
            else:
                css.send(packet.enc())


def css():
    global ACTIVE
    global CAS
    global MAKE_NODES
    queue = []
    cas_switches = []
    CAS_conn = {}
    firewall = []
    def slave(conn):        # Slave is in charge of receiving and putitng frames in frame buffer
        global ACTIVE
        id = str(conn.recv(BUFFER).decode())
        print(f"CAS {id}: Connected.")
        CAS_conn[id] = conn
        while True:
            try:
                if not ACTIVE: break
                data = conn.recv(BUFFER)
                if not data:
                    break
                # conn.sendall(str.encode(response))
                queue.append(Frame(data.decode()))
                # print("CSS: Received a packet")
            except Exception as e:
                print(f"Exception in CSS: {e}")
        conn.close()

    def master_slave():     # Master slave manages slave threads and the connections
        global ACTIVE
        slaves = []
        sock = socket.socket()
        sock.settimeout(3)
        try:
            sock.bind((host, CSS_PORT))
        except socket.error as e:
            print(str(e))
        print('CSS: Listening...')
        sock.listen(5)
        attempts = 0
        while True:     # Main loop for master slave. Makes connections and a thread for each to handle it
            try:
                if not ACTIVE: break
                client, address = sock.accept()
                print('CSS: Accepted connection ' + address[0] + ':' + str(address[1]))
                # start_new_thread(slave, (Client, ))
                slaves.append(threading.Thread(target=slave, args=(client, )))
                slaves[-1].start()
            except TimeoutError:
                # attempts += 1
                pass
        print("CSS: Shutting down...")
        sock.close()
    print(f"CSS: Loaded firewall rules")
    print(f"CSS: Starting listening on port {CSS_PORT}...")
    time.sleep(3)
    ms = threading.Thread(target=master_slave)
    ms.start()
    for i in range(CAS):
        cas_switches.append(threading.Thread(target=switch, args=(i,)))
        cas_switches[-1].start()
        time.sleep(0.1)
    attempts = 0
    while len(cas_switches) != CAS:     # Ensure all nodes are connected to the switch before continuing
        if attempts >= 5:
            print(f"Error! {CAS - len(cas_switches)} CAS(s) failed to connect. Aborting...")
            ABORTED = True
            time.sleep(3)
            ACTIVE = False
            return
        attempts += 1
        time.sleep(1)
    MAKE_NODES = True
    while True:     # Main loop for looking through frame buffer and send each packet to their destination
        if not ACTIVE: break
        if len(queue) > 1:
            packet = queue.pop(0)
            # print("CSS: Dealing with a packet")
            # print(f"CSS: dest is {packet.dest}")
            # print(CAS_conn)
            CAS_conn[packet.dest.split('_')[0]].send(packet.enc())


def main():
    global ACTIVE
    global NUM
    global CAS
    global ALL_CONNECTED
    global PACKETS_RECEIVED
    ACTIVE = True
    ALL_CONNECTED = False

    if len(sys.argv) < 3:
        print("Usage: python3 star.py [NUMBER OF NODES] [NUMBER OF CAS] [random]")
        exit()
    NUM = int(sys.argv[2])
    CAS = int(sys.argv[1])
    if len(sys.argv) == 4 and sys.argv[3] == "random":
        print("Randomizing input files...")
        for j in range(CAS):
            for i in range(NUM):
                with open(f'node{j}_{i}.txt', 'w+') as f:
                    f.write(generate_input(j, i, NUM, CAS))

    m_router = threading.Thread(target=css)
    m_router.start()
    while not MAKE_NODES:
        pass
    for j in range(CAS):
        for i in range(NUM):
            NODES.append(threading.Thread(target=node, args=(j, i,)))
            NODES[-1].start()
            time.sleep(0.1)
    attempts = 0
    while NUM_CONNECTED != NUM * CAS:     # Ensure all nodes are connected to the switch before continuing
        if attempts >= 5:
            print(f"Error! {NUM_CONNECTED - NUM} node(s) failed to connect. Aborting...")
            ABORTED = True
            time.sleep(3)
            ACTIVE = False
            return
        attempts += 1
        time.sleep(1)
    print("All nodes connected successfully. Enabling communication...")
    time.sleep(5)
    ALL_CONNECTED = True       # Allow nodes to start communicating
    try:
        while True:
            if input("").lower() == 'status':   # Command to check how many of the packets are successful
                print(f'{NUM}/{NUM}')
            if PACKETS_RECEIVED >= NUM:     # Stop safely when things go well
                print("All packets successfully sent and received. Shutting down...")
                time.sleep(3)
                break
    except KeyboardInterrupt:
        pass
    ACTIVE = False      # Safe shutdown of all threads and connections
    


if __name__ == '__main__':
    main()
    if ABORTED:
        print("The program was aborted. This can normally be solved by re-running...")