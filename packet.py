'''
    Library for packet generation
'''

# Use this to create C like structs
from dataclasses import dataclass

# Pickle serializes data, such as whole objects
import pickle

# Create enumeration, used as constants
from enum import Enum

from commands import Command, ClientCommands

from typing import Union


class PayloadTypes(Enum):
    '''
        Enum for payload type
    '''
    SERVER_INFO = "server_info"  # This will be displayed to the screen
    SERVER_COMMAND = "server_command"  # This is a request for things such as username
    CLIENT_INFO = "client_info"         # This is a resp to things such as username
    CLIENT_COMMAND = "client_command"   # This is any clients command

    STATUS = "status"


@dataclass
class Packet:
    '''
        The Packet dataclass, all socekt communication
        should use this as it's packet object.
    '''
    header: PayloadTypes
    #contents: str
    #contents: Command
    # Have to do a union because info is just a string
    contents: Union[str, Command]


# TODO: see multiple dispatch
def gen_packet(payload_type: PayloadTypes, contents: Union[str, Command]) -> Packet:
    '''
        Create a packet dataclass and serialize 

        The return is a serial object ready to be sent over 
        the socket
    '''

    # Create the Packet dataclass
    return Packet(payload_type, contents)


def serialize_packet(packet: Packet) -> bytes:
    '''
        Serialize the packet data
    '''
    # Return the serialized packet, this is ready to be sent
    # over the socket
    return pickle.dumps(packet)


# CHANGE: Second param is a Command object now
# def gen_serialized_packet(payload_type: PayloadTypes, contents: str):
def gen_serialized_packet(payload_type: PayloadTypes, contents: Union[Command, str]):
    '''
        Create packet dataclass and serialize 
    '''
    # Create the Packet dataclass
    packet = Packet(payload_type, contents)

    # Return the serialized packet, this is ready to be sent
    # over the socket
    return pickle.dumps(packet)


def unserialize_packet(pickled_data: bytes) -> Packet:
    '''
        Unserialize a read packet

        This is expected to be a dataclass object
    '''
    # Return the 'unpickled' or unserialize_packet, this
    # should return a Packet dataclass
    return pickle.loads(pickled_data)


if __name__ == "__main__":
    packet = Packet(PayloadTypes.SERVER_COMMAND, "this that")

    pickled = pickle.dumps(packet)

    print(f"This is the pickled data: {pickled}\n\n")

    unpickled = pickle.loads(pickled)
    print(f"This is the unpickled data: {unpickled}")
    print(unpickled.contents)
