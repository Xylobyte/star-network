# Star Network Switch

## Repository
https://github.com/Xylobyte/star-network

## Group Members
Donovan Griego and Jai Bhullar

## Project Files
star.py: Main file that contains all classes and methods and main control flow of the program. 

## Requirements
Latest Python 3

## How To Execute
The simulator can be run manually with the following command
    python3 star.py [NUMBER OF NODES] [RANDOM?]
For example
    python3 star.py 50 random

The NUMBER OF NODES parameter will specify how many nodes to create at start.
The RANDOM? parameter can be either included or excluded. It will create random input files for each node.

Alternatively the program can be run by typing 'make' in the terminal. This will start the simulator
with 50 nodes and random inputs.

## Frame Format
### Fields
- Source: Node where frame is coming from. Max size 1 byte
- Destination: Destination node for fram. Max size 1 byte
- Size: Size of data sent. Max size 1 byte
- Data: Actual data being sent. Max size 255 bytes

## Feature Checklist
| Feature                                                            | Status/Description |
| ------------------------------------------------------------------ | ------------------ |
| Project Compiles and Builds without warnings or errors             | Complete           |
| Switch class                                                       | Complete           |
| Switch has a frame buffer, and reads/writes appropriately          | Complete           |
| Switch allows multiple connections                                 | Complete           |
| Switch floods frame when it doesn't know the destination           | Complete           |
| Switch learns destinations, and doesn't forward packet to any port | Complete           |
| Node class                                                         | Complete           |
| Nodes instantiate, and open connection to the switch               | Complete           |
| Nodes open their input files, and send data to switch              | Complete           |
| Nodes open their output files, and save data that they received    | Complete           |

## Known Bugs
- Nodes can sometimes refuse to connect to the router. There is no obvious reason as to why this occurs. We have determined that
  this is likely due to the Python sockets library being unreliable at times. This is solved by terminating and restarting the program.