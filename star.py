from _thread import *
import threading
import socket
import time
import random
import os
import sys

ROUTER_PORT = random.randint(3000, 8000)        # Choose a random port to host the simulator on
host = '127.0.0.1'
SWITCH_TABLE = {}
QUEUE = []
NODES = []
SLAVES = []
DEBUG = True
ACTIVE = False
BUFFER = 260
NUM = 100
ALL_CONNECTED = False
NUM_CONNECTED = 0
PACKETS_RECEIVED = 0

def generate_input(curr, num):      # Generate random input files given a number of nodes 
    words = ['networks', 'pc', 'trees', 'extra', 'moment', 'pickle', 'book', 'lunch', 'no', 'free']
    output = ''
    for i in range(3):
        no = random.randint(0, num-1)
        while no == curr:
            no = random.randint(0, num-1)
        output += f'{no}:'
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
        self.src = int(bytes[0])
        self.dest = int(bytes[1])
        self.size = int(bytes[2])
        self.data = bytes[3]

    def enc(self):
        return f'{self.src}:{self.dest}:{self.size}:{self.data}'.encode()
    
def node(id):
    global ACTIVE
    global NUM_CONNECTED
    global PACKETS_RECEIVED
    sock = socket.socket()
    sock.settimeout(3)
    try:    # Attempt to connect to switch
        while sock.connect_ex((host, ROUTER_PORT)) != 0:
            if not ACTIVE: 
                sock.close()
                if DEBUG: print(f"Node {id} shutting down...")
                exit()
            print(f"Node {id}: Attempting to connect")
            time.sleep(random.uniform(0.5, 2))      # Ensure no overlap between nodes
    except socket.error as e:
        print(str(e))
    sock.send(str(id).encode())
    NUM_CONNECTED += 1
    while not ALL_CONNECTED:    # Wait until all nodes are connected to start sending frames
        if not ACTIVE:
            sock.close()
            if DEBUG: print(f"Node {id}: Shutting down...")
            exit()
        time.sleep(1)
    with open(f'node{id}output.txt', 'w+') as outfile:      # Open input and output files for read and writing
        infile = open(f'node{id}.txt', 'r')
        lines = infile.readlines()
        for line in lines:      # Loop through input lines and get them to their destinations
            if not ACTIVE: break
            line = line.strip().split(':')
            sock.send(Frame(f"{id}:{int(line[0])}:{len(line[1])}:{line[1]}").enc())
            ack = False
            attempts = 0
            while ack == False:     # Ensure an acknowledgement frame is receives, otherwise retry the send
                if attempts >= 3:
                    sock.send(Frame(f"{id}:{int(line[0])}:{len(line[1])}:{line[1]}").enc())
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
                        if data.dest == id:
                            outfile.write(f"{data.src}: {data.data}\n")
                            print(f"Node {id}: Received '{data.data}' from node {data.src}")
                            sock.send(Frame(f"{id}:{data.src}:{0}:").enc())
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
                print(f"Node {id}: Received {data.data} from node {data.src}")
                sock.send(Frame(f"{id}:{data.src}:{0}:").enc())
                PACKETS_RECEIVED += 1
            except TimeoutError:
                attempts += 1

        if DEBUG: print(f"Node {id}: Shutting down...")
        sock.close()

    

def switch():       # Main switch class manages slave threads and sends frames to connected nodes
    global ACTIVE
    def slave(conn):        # Slave is in charge of receiving and putitng frames in frame buffer
        global ACTIVE
        id = int(conn.recv(BUFFER).decode())
        print(f"Node {id}: Connected.")
        SWITCH_TABLE[id] = conn
        while True:
            try:
                if not ACTIVE: break
                data = conn.recv(BUFFER)
                if not data:
                    break
                # conn.sendall(str.encode(response))
                QUEUE.append(Frame(data.decode()))
            except TimeoutError:
                pass
        conn.close()

    def master_slave():     # Master slave manages slave threads and the connections
        global ACTIVE
        sock = socket.socket()
        sock.settimeout(3)
        try:
            sock.bind((host, ROUTER_PORT))
        except socket.error as e:
            print(str(e))
        print('Switch: Listening...')
        sock.listen(5)
        attempts = 0
        while True:     # Main loop for master slave. Makes connections and a thread for each to handle it
            try:
                if not ACTIVE: break
                Client, address = sock.accept()
                print('Router: Accepted connection ' + address[0] + ':' + str(address[1]))
                # start_new_thread(slave, (Client, ))
                SLAVES.append(threading.Thread(target=slave, args=(Client, )))
                SLAVES[-1].start()
            except TimeoutError:
                # attempts += 1
                pass
        print("Switch: Shutting down...")
        sock.close()

    ms = threading.Thread(target=master_slave)
    ms.start()
    while True:     # Main loop for looking through frame buffer and send each packet to their destination
        if not ACTIVE: break
        if len(QUEUE) > 1:
            packet = QUEUE.pop(0)
            if SWITCH_TABLE[packet.dest] == None:       # If a destination node is not in the switch table, send it to all nodes
                for conn in SWITCH_TABLE:
                    conn.send(packet.enc())
            SWITCH_TABLE[packet.dest].send(packet.enc())


def main():
    global ACTIVE
    global NUM
    global ALL_CONNECTED
    global PACKETS_RECEIVED
    ACTIVE = True
    ALL_CONNECTED = False
    
    if len(sys.argv) < 2:
        print("Usage: python3 star.py [NUMBER OF NODES] [random]")
        exit()
    NUM = int(sys.argv[1])
    if len(sys.argv) == 3:
        print("Randomizing input files...")
        for i in range(NUM):
            with open(f'node{i}.txt', 'w+') as f:
                f.write(generate_input(i, NUM))

    print(f"Starting router on port {ROUTER_PORT}\nStarting {NUM} nodes...")
    time.sleep(5)
    m_router = threading.Thread(target=switch)
    m_router.start()
    for i in range(NUM):
        NODES.append(threading.Thread(target=node, args=(i,)))
        NODES[-1].start()
        time.sleep(0.1)
    attempts = 0
    while NUM_CONNECTED != NUM:     # Ensure all nodes are connected to the switch before continuing
        if attempts >= 5:
            print(f"Error! {NUM - NUM_CONNECTED} node(s) failed to connect. Aborting...")
            time.sleep(3)
            ACTIVE = False
            exit()
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