'''
Start of Part 1 code 




OVERVIEW OF PROTOCOL:

    All communiction between client and server will be sent in this format:

    | PayloadTypes | payload |

    There are 4 payloads:
        1. server_info    : info sent from server
            => Error
            => List of users
            => New user
        2. server_command : command sent from server
            => USERNAME (get the username from a new user)
            => EXIT (tell the client to exit)
        3. client_command : command sent from client
            => All commands available to user (this will be the raw input from the user)
        4. client_info    : info sent from client (only use is username)
            => USERNAME 


    CLIENT_COMMAND : Any of the user commands
        | CLIENT COMMAND | Command Obj
    CLIENT_REQ_RESP : Response to a server request
        | CLEITN_REQ | String info | 
    SERVER_COMMAND_RESP : Response to a client request
        | Server_command_resp | String Object to be printed to term |
    SERVER_INFO : Server Info, will be displayed on client
        | Server_info | String Object to be printed to term |
    SERVER_REQ_INFO: Server request for info
        | Servver req info | info wanted |

    The majority of parsing will be done on the server 
    side. Errors during parsing of client_info or 
    client_command will result in error response from 
    server


    NOTE: 
        When a POST is sent to the server it is a command by the client 

        When the server distributes the post it is INFO by the server
'''


import socket
import select
import queue

import datetime

from dataclasses import dataclass
from enum import Enum

from typing import Union

from packet import PayloadTypes, Packet, gen_packet, \
    gen_serialized_packet, unserialize_packet

from commands import ClientCommands, ServerCommands, Status, \
    Command, gen_client_cmd_from_raw

from errors import ClientCommandError, ClientParseError, \
    ServerError, EmptyPacketError, GroupInstanceKeyError, \
    CommandGenerationError, PostGenerationError


@dataclass
class ClientConnection:
    conn: socket.socket
    username: str


@dataclass
class PostObject:
    msg_id: int
    sender: str
    date: str
    subject: str
    message: str


@dataclass
class QueueObject:
    # This is the same as the protocol with one addition
    serial_payload: bytes

    # Need a list of target connections to send to
    targets: list[ClientConnection]


# Now all the server has to do is:
#
# 1. Listen for new connections
# 2. Handle Connections:
#   2a. Get a valid username
#   2b. Prompt user for a group, join valid group, notify
#           group members of new user
#   2c. Connection loop (2z)
#
#   2z. Connection Loop:
#       - Recieve a cmd from the client
#       - If it's a post, wrap that in a msgObj and add to Que
#       - Handle the message Que sending messages to correct ppl
#           - Use the msgObj.msgGroups to identify which groups
#              to send the message to
#           - use the list of client_connections and the
#               client_connections.groups and .conn to find the
#               corresponding group and use the conn to send the
#               message
#


class SingleGroupServer:
    '''
        This is a server that will concurrently 
        serve all the connections to it

        SingleGroupServer will NOT ever send a packet 
        itself, but rather return the packet to be 
        sent the MasterServer 

        This is because I cannot have 2 or more SingleGroupServers
        running and both try to send to the same user_conn at the 
        same time

        Responsibilites:
        MasterServer:               | Single Group Server
            Handle incoming comms   |
            Handle JOIN and         |
            JOIN GROUP              |
            Packet routing          |   Parsing packet
            Determine Packet type   |   Generate responses to 
                Send command packets|       packets
                to Single Group     |
                servers             |
    '''

    def __init__(self, group_name):

        # Name of this group
        self.group_name = group_name

        # List of ClientConnection objects in group
        self.client_connections = []
        self.group1 = []
        self.group2 = []
        self.group3 = []
        self.group4 = []
        self.group5 = []

        # Post log is int id : PostObj post
        self.post_log = {}

        # payload queue
        self.payload_queue = []

        # Current post id
        self.post_count = 0

    def parse_packet(self, packet: Packet) -> Union[Command, str]:
        '''
            Parse the packet and return a Command 
            object based on the packet
        '''

        # @ TODO: Made this as a middle man function
        #           incase I want to wrap the
        #           gen_client_cmd_from_raw function

        # Update: Good thing this was middle man!
        #   packet.contents is now of type Command

        # Generate a command objetc
        # return gen_client_cmd_from_raw(Packet.contents)
        return packet.contents

    def session_loop(self, packet: Packet, client_conn: ClientConnection) -> list[QueueObject]:
        '''
            Session loop recieves parsed 
            commands from master server
        '''

        # If we are here, the cmd object is expected to be a command
        # and not a string
        cmd_object = self.parse_packet(packet)

        # Make sure this is a cmd_object
        if not isinstance(cmd_object, Command):
            # We have an issue
            resp_packet = gen_serialized_packet(
                PayloadTypes.SERVER_INFO, str(Status.ERROR.value))
            return [QueueObject(resp_packet, [client_conn])]

        # In the command object, the name
        # of the command is a string, I want the
        # corresponding command Enum for that
        cmd = [x for x in ClientCommands if x.value == cmd_object.name][0]

        print(f'[SESH_LOOP] has cmd {cmd_object} from {client_conn.username}')

        match cmd:

            case ClientCommands.GROUPJOIN:
                # Add the group to the list, queue
                # a message to notify all users that
                # A new user has joingd

                # Append the new client
                self.client_connections.append(client_conn)

                # Create the notify packet and QueueObjetc
                notify_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, f"User {client_conn.username} has joined :)")

                # get the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the two packets for the last two messages
                if len(self.post_log) >= 2:
                    last_id = max([int(x) for x in list(self.post_log.keys())])
                    second_last_id = last_id - 1

                    # Get the last two msgs
                    msg1 = self.post_log[last_id]
                    msg2 = self.post_log[second_last_id]

                    # Create the strings for the last 2
                    msg1_str = f"{msg1.msg_id} {msg1.sender} {msg1.date} {msg1.subject}"
                    msg2_str = f"{msg2.msg_id} {msg2.sender} {msg2.date} {msg2.subject}"

                    msg1_packet = gen_serialized_packet(
                        PayloadTypes.SERVER_INFO, msg1_str)

                    msg2_packet = gen_serialized_packet(
                        PayloadTypes.SERVER_INFO, msg2_str)

                    # get the targets
                    targets = [conn for conn in self.client_connections
                               if conn.username != client_conn.username]

                # Create the two packets for the last two messages

                    return [QueueObject(notify_packet, targets), QueueObject(msg1_packet, [client_conn]), QueueObject(msg2_packet, [client_conn])]
                else:
                    return [QueueObject(notify_packet, targets)]

            case ClientCommands.POST | ClientCommands.GROUPPOST:
                # Need to parse the args
                # Should be in format:
                #   POST <msg_subject> <msg_contents>

                print("[GEN] Generating a post obj")
                # Need to create a post object:
                #   msg_id: str
                #   sender: date
                #   date: str
                #   subject: str
                #   contents: str

                # Creaet post object
                try:
                    post = PostObject(
                        msg_id=self.post_count,
                        sender=client_conn.username,
                        date=str(datetime.datetime.now()),
                        subject=cmd_object.args['subject'],
                        message=cmd_object.args['msg']
                    )
                except KeyError as e:
                    raise PostGenerationError("Failed to gen post")

                # Add the post to the log
                self.post_count += 1
                self.post_log[post.msg_id] = post

                # Need to send a notification to every of the post
                notify_str = f"{post.msg_id} {post.sender} {post.date} {post.subject}"

                # Create the packet for the MasterServer
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, notify_str)

                # get the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue packet to send to the MasterSevrer
                queue_payload = QueueObject(resp_packet, targets)

                return [queue_payload]

            case ClientCommands.USERS | ClientCommands.GROUPUSERS:
                # command to list a user in the group
                # Now theres a list of lists of str reprs: "{group.name} name1, name2 , ..., namex"
                # Format into one string

                ret_str = ", ".join(
                    [client.username for client in self.client_connections])

                # Create the return packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, ret_str)

                # Create the targets
                targets = [client_conn]

                # Create the queue packet to send to the MasterSevrer
                queue_payload = QueueObject(resp_packet, targets)

                return [queue_payload]

        #
        # @TODO:
        #   Should Leave return an status.OK pakcet?
        #
            case ClientCommands.LEAVE | ClientCommands.GROUPLEAVE:
                # command to leave the group

                # Remove username from group
                if client_conn in self.client_connections:
                    self.client_connections.remove(client_conn)
                else:
                    # Create the resp packet
                    resp_packet = gen_serialized_packet(
                        PayloadTypes.SERVER_INFO, f"Not in group {self.group_name}")
                    return [QueueObject(resp_packet, [client_conn])]

                # Create the resp packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, f"User {client_conn.username} has left")

                # Create the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)

                return [queue_payload]

            case ClientCommands.MESSAGE | ClientCommands.GROUPMESSAGE:
                # command to get the contents of a message

                # The cmd object should have key
                # msg_id
                try:
                    msg_id = int(cmd_object.args['msg_id'])
                except Exception as e:
                    raise ClientCommandError

                # See if this msg_id is known
                try:
                    post = self.post_log[msg_id]
                except KeyError as e:
                    raise ClientCommandError

                # If we get here, the post is logged
                # Return the contents of the post to
                # the client

                post_message = post.message

                # Create a packet for this
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, post_message)

                # Create the targets
                targets = [client_conn]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)

                return [queue_payload]

            case ClientCommands.EXIT:
                # command to disconned from server

                # Server side handles the connection close, this side will
                # handle removing the username

                # Remove username from group
                self.client_connections.remove(client_conn)

                # Create the resp packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, f"User {client_conn.username} has exitted the server")

                # Create the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)

                return [queue_payload]
                #    raise ClientParseError(f"No command: {command}")
            case _:
                # Error case

                # Create the resp packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, str(Status.ERROR.value))

                # Create the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)
                return [queue_payload]


class MasterGroupServer:
    '''
        The server is responsible for recieving communications 
        from the client, parsing, and sending commands to th 
        groupserver 
    '''

    def __init__(self, host, port, group_names: list[str]):
        '''
        port host and sock  used for sock

        Sock is server socket
        '''

        self.port = port
        self.host = host

        # Create the socket for the server to server on
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))

        # The offical connection point for clients
        self.sock = server

        # List of group names
        self.groups = group_names

        # Make a list of the SingleGroupServers
        self.group_instance_dict = {
            name: SingleGroupServer(name) for name in group_names}

        # List of ClientConnection object
        self.client_connections = []

        # List of QueueObjs that need to be sent
        self.payload_queue = queue.Queue()

        # List of connections that have a pending Packet for them
        #self.conns_to_write = []

        # Dict of conns : Packets
        self.packets_for_conn = {}

        # Reserved Name
        self.reserved_name_prefix = "<NONAME>"

    def add_new_conn(self, conn):
        '''
            This is the new connection listening 

            The only job this has is to establish new 
            conns and add them to the list of connecions

            This will run on it's own thread 
        '''
        # The new connection must send a valid username
        # resp_packet = gen_serialized_packet(
        #    PayloadTypes.SERVER_COMMAND, str(ServerCommands.SEND_USERNAME.value))

        # Create a tempary ClientConnection object, that is not
        # stored in the self.connection_objects yet
        number_temp_names = len(
            [x for x in self.client_connections if self.reserved_name_prefix in x.username])
        temp_name = self.reserved_name_prefix + str(number_temp_names)

        # Create the client connection and appends to the list of connections
        client_conn = ClientConnection(conn, username=temp_name)
        self.client_connections.append(client_conn)

        # generate the queue packet
        #queue_payload = QueueObject(resp_packet, targets=[client_conn])

        # Put the payload onto the queue to send out
        # self.add_payload_queue(queue_payload)
        return

    def add_payload_queue(self, payload: QueueObject) -> None:
        '''

            Put the payload onto the queue

            Update the message for a given conn

            Add all the targets to the conns to write to 

        '''
        self.payload_queue.put(payload)

        for target in payload.targets:
            print(f"Adding payload_queue for {target.username}")
            if target.conn not in self.packets_for_conn.keys():
                # Add a spot for the conn
                self.packets_for_conn[target.conn] = []

            # Add the packet to the list of packets to send a connection
            self.packets_for_conn[target.conn].append(payload.serial_payload)

            # Finally, flag that the conn(s) need to be written to
            # self.conns_to_write.append(target.conn)

            targets_repr = ", ".join(
                target.username for target in payload.targets)

            print(
                f"[QUEUE_PAYLOAD] Added a payload for targets: {targets_repr}")

    def serve_forever(self):
        '''
            This starters the server
        '''
        while True:
            self.sock.listen()
            self.session()

    def session(self):
        '''
            This is the main handler 

            select.select from the queue and listen 
            to the self.conns
        '''

        # Create a list of just the conns that are readable
        readables = [client.conn for client in self.client_connections]
        readables.append(self.sock)

        # Select between reading and writing to sockets,
        # Reading occurs when:
        #   client sends to server
        #   a new client is trying to connect
        # Writing occurs when:
        #   a payload is queued for a connection

        writables = list(
            x for x, q in self.packets_for_conn.items() if len(q) > 0)

        # readables, writables, exceptionals = select.select(
        #    readables, self.conns_to_write, readables)

        readables, writables, exceptionals = select.select(
            readables, writables, readables)

        for read in readables:

            # If the readable is the server sock, a new client is trying to connect
            if read is self.sock:
                # Accept new connection
                conn, addr = self.sock.accept()
                # Verbose print if desired
                print(f"[CONN] New req from {conn} {addr}")

                # Handle the new connection
                self.add_new_conn(conn)
                break

            # This is a fancy way of getting the ClientConnection object
            # from the list of client connections based on its conn
            client_conn = [
                x for x in self.client_connections if x.conn is read][0]

            # In this case a conn is sending something
            try:
                # Read in the packet from the client
                raw_recieved = read.recv(1024)
                recv_packet = unserialize_packet(raw_recieved)
            except Exception as e:
                # There was an error readign the sock
                # disconnected
                self.clear_client_conn(client_conn)
                return

            # De-serialize the packet

            # Check that the packet isn't empty, if so exit the conn
            if recv_packet == "":
                # the conn has closed
                self.client_connections.remove(read)
                # self.conns_to_write.pop(read)
                return

            # This is a fancy way of getting the ClientConnection object
            # from the list of client connections based on its conn
            client_conn = [
                x for x in self.client_connections if x.conn is read][0]

            print(
                f"[READ] From user: {client_conn.username} header: {recv_packet.header} contents: {recv_packet.contents}")

            # Headers are 1 of 2 options
            match recv_packet.header:

                case PayloadTypes.CLIENT_INFO:
                    # Client info should only be:
                    #   - Username

                    # and SHOULD be a string
                    if not isinstance(recv_packet.contents, str):
                        # If it is not a string there's an issue
                        print("[ERROR] Payload type of info has non-str contents")
                        self.create_and_queue_error(client_conn)
                        return

                    if "username" not in recv_packet.contents.lower():
                        # error here

                        # Send another request for the USERNAME
                        resp_packet = gen_serialized_packet(
                            PayloadTypes.SERVER_COMMAND, str(ServerCommands.SEND_USERNAME.value))

                        # generate the queue packet
                        queue_payload = QueueObject(
                            resp_packet, targets=[client_conn])
                        # Put the payload onto the queue to send out
                        self.add_payload_queue(queue_payload)
                    else:
                        # did send a username
                        # Now check to see that is good

                        # the contents will be: "username <name>"
                        username = recv_packet.contents.split(" ")[1]

                        if username not in [conn.username for conn in self.client_connections]:
                            # If the username is good send an OK status
                            resp_packet = gen_serialized_packet(
                                PayloadTypes.SERVER_INFO, str(Status.OK))

                            # Change the connection's username
                            client_conn.username = username

                        else:
                            # If the username is taken ask for it again
                            resp_packet = gen_serialized_packet(
                                PayloadTypes.SERVER_COMMAND, str(ServerCommands.SEND_USERNAME))

                        # generate the queue packet
                        queue_payload = QueueObject(
                            resp_packet, targets=[client_conn])
                        # Put the payload onto the queue to send out
                        self.add_payload_queue(queue_payload)

                case PayloadTypes.CLIENT_COMMAND:
                    # This one is more work
                    #   POST
                    #   LEAVE
                    #   MESSAGE
                    # Are really only meant for a single group
                    # server, and don't make sense for multigroups
                    # Therefore, I chose to make those a "broadcast"
                    # command and apply to every group a user is apart of

                    # However any commands that are group commands will be easy!
                    # B/c they only apply to one group

                    # and SHOULD be a Command
                    if not isinstance(recv_packet.contents, Command):
                        # If it is not a string there's an issue
                        print(
                            "[ERROR] Payload type of info has non-Command contents")
                        self.create_and_queue_error(client_conn)
                        return

                    # No need to parse command anymore, done client side
                    cmd = recv_packet.contents

                    try:
                        if cmd.name == str(ClientCommands.GROUPS.value):
                            # List the groups
                            group_str = ", ".join(self.groups)

                            # Create the serial payload
                            serial_payload = gen_serialized_packet(
                                PayloadTypes.SERVER_INFO, group_str)

                            # Create the queue payload
                            queue_payload = QueueObject(
                                serial_payload, [client_conn])

                            # Add the payload to queueu
                            self.add_payload_queue(queue_payload)
                            return

                        #  Check to see if we have the easier group command
                        if "group" in cmd.name.lower():

                            print(
                                f"[sub_WRITE] Should be generating group sepecifc resp:")
                            print(
                                f"[sub_WRITE] The command name is: {cmd.name}")
                            print(f"[sub_WRITE] The command {cmd}")

                            # parse the group that they want to send this to
                            group_name = cmd.args['group']
                            print(
                                f"[sub_WRITE] The group_name is: {group_name}")

                            group_inst = self.get_group_inst(group_name)

                            # Send the group_obj the packet
                            queue_payloads = group_inst.session_loop(
                                recv_packet, client_conn)

                            print(
                                f"[sub_WRITE] Got {len(queue_payloads)} payloads")

                            for payload in queue_payloads:

                                #de_serial = unserialize_packet(payload.serial_payload)
                                #print(f"[sub_WRITE] made a queue payload: {de_serial.header} {de_serial.contents}")

                                # Put the payload onto the queue to send out
                                self.add_payload_queue(payload)
                        else:
                            # We do not have a group command, so hanlde the weird

                            # Because it's a single command, I'm making the default behavior
                            # treat it like a 'broadcast' command

                            # So send the command to every group that this connection is apart of
                            for group_name, group_obj in self.group_instance_dict.items():
                                # Now for each SingleGroupServer that the user is apart of, send the message
                                if client_conn in group_obj.client_connections:
                                    # Send the group_obj the packet
                                    queue_payloads = group_obj.session_loop(
                                        recv_packet, client_conn)

                                    for payload in queue_payloads:
                                        # Put the payload onto the queue to send out
                                        self.add_payload_queue(payload)
                    except GroupInstanceKeyError as e:
                        print("[ERROR] Getting the group instance")
                    except CommandGenerationError as e:
                        print("[ERROR] Formtaing the cmd")
                    except ClientCommandError as e:
                        print("[ERROR] formatting command")
                        self.create_and_queue_error(client_conn)
        # Readable are done

        # Here write is going to be a socket connection
        for write in writables:
            # In this case a conn is targeted by a payload

            # Grab the username based on conn
            client_conn = [
                x for x in self.client_connections if x.conn == write][0]

            try:

                if len(self.packets_for_conn[write]) == 0:
                    # Shouldn't be in here
                    return

                # Grab the most first element in the msgs to the sock
                outgoing_packet = self.packets_for_conn[write][0]

                # de-serialize the packet for more debug info to screen
                deserial_packet = unserialize_packet(outgoing_packet)

                print(
                    f"[WRITE_QUEUE] Sending msg to {client_conn.username}: {deserial_packet.header} {deserial_packet.contents}")
                # Write the packet to the socket
                write.send(outgoing_packet)

                # Remove the first packet
                self.packets_for_conn[write].pop(0)

                # Remove the conection if it doesn't
                # if len(self.packets_for_conn[write]) == 0:
                #    self.conns_to_write.remove(write)
            # @TODO: Probably not good to capture every excpetion like this
            except socket.error as e:
                # There was an issue in writing the connection
                # Sockets closed so clear any trace of connection
                self.clear_client_conn(client_conn)
            except IndexError as e:
                print(f'[ERROR] Index error for sock, removing sock from writables')
                self.packets_for_conn.pop(write)

        # Writeable done

        # @TODO
        for s in exceptionals:
            # These are the threads that likely unexcpetedly closed
            # Need to clear the connection from every group that it was apart of
            # and from any queue in here

            # Grab the username based on conn
            client_conn = [
                x for x in self.client_connections if x.conn == s][0]

            self.clear_client_conn(client_conn)

        # exceptionsals done

    def clear_client_conn(self, client_conn: ClientConnection) -> None:
        '''
            Wipe the server and all rooms of the client conn
        '''

        # Create a fake leave command for the client to send to server
        pseudo_leave_cmd = gen_client_cmd_from_raw(
            str(ClientCommands.LEAVE.value))
        pseudo_packet = gen_packet(
            PayloadTypes.CLIENT_COMMAND, pseudo_leave_cmd)

        # For the groups that are connection is in, call leave cmd for them
        for group_inst in self.group_instance_dict.values():
            group_inst.session_loop(pseudo_packet, client_conn)

        # Now wipe the saves for the connection
        if client_conn in self.client_connections:
            self.client_connections.remove(client_conn)
        # if client_conn in self.conns_to_write:
        #    self.conns_to_write.remove(client_conn)
        if client_conn in list(self.packets_for_conn.keys()):
            self.packets_for_conn.pop(client_conn)

        print(f"[CONN] Unexpected exit from: {client_conn.username}")

    def get_group_inst(self, group_name: str) -> SingleGroupServer:
        '''
            Check that a group instance exists and return it 
        '''
        try:
            return self.group_instance_dict[group_name]
        except KeyError as e:
            # Group does not exist
            raise GroupInstanceKeyError(f"Group {group_name} doesn't exist")

    def create_and_queue_error(self, client_conn: ClientConnection):
        '''
            Create a SERVERINFO packet with Status.Error
            and put on the queueu for the corresponding client_conn
        '''
        # Send back an error packet
        resp_packet = gen_serialized_packet(
            PayloadTypes.SERVER_INFO, str(Status.ERROR))

        # generate the queue packet
        queue_payload = QueueObject(resp_packet, targets=[client_conn])

        # Put the payload onto the queue to send out
        self.add_payload_queue(queue_payload)


if __name__ == '__main__':

    groups = ['Group1', 'Group2', 'Group3', 'Group4', 'Group5']

    # The default ip is 'localhost' on port 8000
    mServer = MasterGroupServer('localHost', 8000, groups)

    print(" _______  __   __  _______  _______  ______      _______  _______  _______  ___ ")
    print("|       ||  | |  ||       ||       ||    _ |    |       ||       ||       ||   |      ")
    print("|  _____||  | |  ||    _  ||    ___||   | ||    |       ||   _   ||   _   ||   |      ")
    print("| |_____ |  |_|  ||   |_| ||   |___ |   |_||_   |       ||  | |  ||  | |  ||   |      ")
    print("|_____  ||       ||    ___||    ___||    __  |  |      _||  |_|  ||  |_|  ||   |___   ")
    print(" _____| ||       ||   |    |   |___ |   |  | |  |     |_ |       ||       ||       |  ")
    print("|_______||_______||___|    |_______||___|  |_|  |_______||_______||_______||_______|  ")
    print("   ")
    print(" _______  __   __  _______  _______    ______    _______  _______  __   __            ")
    print("|       ||  | |  ||   _   ||       |  |    _ |  |       ||       ||  |_|  |           ")
    print("|       ||  |_|  ||  |_|  ||_     _|  |   | ||  |   _   ||   _   ||       |           ")
    print("|       ||       ||       |  |   |    |   |_||_ |  | |  ||  | |  ||       |           ")
    print("|      _||       ||       |  |   |    |    __  ||  |_|  ||  |_|  ||       |           ")
    print("|     |_ |   _   ||   _   |  |   |    |   |  | ||       ||       || ||_|| |           ")
    print("|_______||__| |__||__| |__|  |___|    |___|  |_||_______||_______||_|   |_|           ")
    print("   ")
    print("   ")
    print("   ")
    print("About to serve...")
    mServer.serve_forever()
