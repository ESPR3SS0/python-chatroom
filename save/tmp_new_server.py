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
#import threading
import select
import queue

import datetime

from dataclasses import dataclass
from enum import Enum

from packet import PayloadTypes, Packet, gen_packet, \
    gen_serialized_packet, unserialize_packet

from commands import ClientCommands, ServerCommands, Status, \
    Command, gen_client_cmd_from_raw

from errors import ClientCommandError, ClientParseError, ServerError, EmptyPacketError


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

        # Post log is int id : PostObj post
        self.post_log = {}

        # payload queue
        self.payload_queue = []

        # Current post id
        self.post_count = 0

    def parse_packet(self, packet: Packet) -> Command:
        '''
            Parse the packet and return a Command 
            object based on the packet
        '''

        # @ TODO: Made this as a middle man function
        #           incase I want to wrap the
        #           gen_client_cmd_from_raw function

        # Generate a command objetc
        return gen_client_cmd_from_raw(Packet.contents)

    def session_loop(self, packet: Packet, client_conn: ClientConnection) -> QueueObject:
        '''
            Session loop recieves parsed 
            commands from master server
        '''

        cmd_object = self.parse_packet(packet)

        # In the command object, the name
        # of the command is a string, I want the
        # corresponding command Enum for that
        cmd = [x for x in ClientCommands if x.value == cmd_object.name][0]

        match cmd:

            # @TODO
            case ClientCommands.POST:
                # Need to parse the args
                # Should be in format:
                #   POST <msg_subject> <msg_contents>

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
                        message=cmd_object.args['message']
                    )
                except KeyError as e:
                    raise ClientCommandError

                # Add the post to the log
                self.post_log[post.msg_id] = post
                self.post_count += 1

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

                return queue_payload

            case ClientCommands.USERS:
                # command to list a user in the group

                # Now theres a list of lists of str reprs: "{group.name} name1, name2 , ..., namex"
                # Format into one string
                ret_str = ", ".join(
                    [client.username for client in self.client_connections])

                # Create the return packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, ret_str)

                # Create the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue packet to send to the MasterSevrer
                queue_payload = QueueObject(resp_packet, targets)

                return queue_payload

        #
        # @TODO:
        #   Should Leave return an status.OK pakcet?
        #
            case ClientCommands.LEAVE:
                # command to leave the group

                # Remove username from group
                self.client_connections.remove(client_conn)

                # Create the resp packet
                resp_packet = gen_serialized_packet(
                    PayloadTypes.SERVER_INFO, str(Status.OK.value))

                # Create the targets
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)

                return queue_payload

            case ClientCommands.MESSAGE:
                # command to get the contents of a message

                # The cmd object should have key
                # msg_id
                try:
                    msg_id = cmd_object.args['msg_id']
                except KeyError as e:
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
                targets = [conn for conn in self.client_connections
                           if conn.username != client_conn.username]

                # Create the queue payload
                queue_payload = QueueObject(resp_packet, targets)

                return queue_payload

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

                return queue_payload
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
                return queue_payload


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
        self.conns_to_write = []

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
        resp_packet = gen_serialized_packet(
            PayloadTypes.SERVER_COMMAND, str(ServerCommands.SEND_USERNAME.value))

        # Create a tempary ClientConnection object, that is not
        # stored in the self.connection_objects yet
        number_temp_names = len(
            [x for x in self.client_connections if self.reserved_name_prefix in x.username])
        temp_name = self.reserved_name_prefix + str(number_temp_names)

        # Create the client connection and appends to the list of connections
        client_conn = ClientConnection(conn, username=temp_name)
        self.client_connections.append(client_conn)

        # generate the queue packet
        queue_payload = QueueObject(resp_packet, targets=[client_conn])

        # Put the payload onto the queue to send out
        self.add_payload_queue(queue_payload)
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
            self.conns_to_write.append(target.conn)

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

        readables, writables, _ = select.select(
            readables, self.conns_to_write, [])

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

            # In this case a conn is sending something

            # Read in the packet from the client
            raw_recieved = read.recv(1024)

            # De-serialize the packet
            recv_packet = unserialize_packet(raw_recieved)

            # Check that the packet isn't empty, if so exit the conn
            if recv_packet == "":
                # the conn has closed
                self.client_connections.remove(read)
                self.conns_to_write.pop(read)
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

                    # Need to parse the command a bit
                    cmd = gen_client_cmd_from_raw(recv_packet.contents)

                    try:
                        #  Check to see if we have the easier group command
                        if "group" in str(cmd.name).lower():
                            # parse the group that they want to send this to
                            group_name = recv_packet.contents.split(" ")[1]
                            group_inst = self.get_group_inst(group_name)

                           # Get the group server for that
                            group_obj = self.group_instance_dict[group_name]

                            # Send the group_obj the packet
                            queue_payload = group_obj.session_loop(
                                recv_packet, client_conn)

                            # Put the payload onto the queue to send out
                            self.add_payload_queue(queue_payload)
                        else:
                            # We do not have a group command, so hanlde the weird

                            # Because it's a single command, I'm making the default behavior
                            # treat it like a 'broadcast' command

                            # So send the command to every group that this connection is apart of
                            for group_name, group_obj in self.group_instance_dict.items():
                                # Now for each SingleGroupServer that the user is apart of, send the message
                                if client_conn in group_obj.client_connections:
                                    # Send the group_obj the packet
                                    queue_payload = group_obj.session_loop(
                                        recv_packet, client_conn)

                                    # Put the payload onto the queue to send out
                                    self.add_payload_queue(queue_payload)
                    except ClientCommandError as e:
                        self.create_and_queue_error(client_conn)
        # Readable are done

        # Here write is going to be a socket connection
        for write in writables:
            # In this case a conn is targeted by a payload

            # Grab the username based on conn
            username = [
                x.username for x in self.client_connections if x.conn == write][0]

            # Grab the most first element in the msgs to the sock
            outgoing_packet = self.packets_for_conn[write][0]

            # de-serialize the packet for more debug info to screen
            deserial_packet = unserialize_packet(outgoing_packet)

            print(
                f"[WRITE_QUEUE] Sending msg to {username}: {deserial_packet.header} {deserial_packet.contents}")
            # Write the packet to the socket
            write.send(outgoing_packet)

            # Remove the first packet
            self.packets_for_conn[write].pop(0)

            # Remove the conection if it doesn't
            if len(self.packets_for_conn[write]) == 0:
                self.conns_to_write.remove(write)

    def get_group_inst(self, group_name: str) -> SingleGroupServer:
        '''
            Check that a group instance exists and return it 
        '''
        try:
            return self.group_instance_dict[group_name]
        except KeyError as e:
            # Group does not exist
            raise ClientCommandError(f"Group {group_name} doesn't exist")

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

    # def handle_group_cmd(self, group_inst: SingleGroupServer, client_conn: ClientConnection):
    #    '''
    #        Pass the packet to the group server
    #    '''


# class socketServer:
#    def __init__(self, host, port):
#      '''
#        port host and sock  used for sock
#
#        Sock is server socket
#      '''
#      self.port = port
#      self.host = host
#
#      # Create the socket for the server to server on
#      server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#      server.bind((self.host, self.port))
#
#      # The offical connection point for clients
#      self.sock = server
#
#      # List of msgObjs that need to be sent
#      self.payload_queue = queue.Queue()
#
#      # List of  ClientConnection objects
#      self.client_connections_names = []
#
#      # List of different groups that a client can join
#      self.groups = [
#                     GroupObject("PRIVATE1",[],{}),
#                     GroupObject("PRIVATE2",[], {}),
#                     GroupObject("PRIVATE3",[], {}),
#                     GroupObject("PRIVATE4",[], {}),
#                     GroupObject("PRIVATE5",[], {}),
#                    ]
#      self.serving = False
#
#      self.server_log = []
#
#        # post counter is going to incrament with every
#        # post and will be the post id
#      self.post_counter = 0
#
#    def begin_serving(self):
#        '''
#        Listen forever on sock and throw new
#        connections onto new threads
#        '''
#
#
#        self.serving = True
#        thread = threading.Thread(target=self.serve_queue)
#
#        print(f"[SERVER] Now serving on {self.host}:{self.port}")
#
#        # Begin listening on socket
#        self.sock.listen()
#
#        while True:
#
#            # Accept new connection
#            conn, addr = self.sock.accept()
#
#            # Verbose print if desired
#            print(f"[CONN] New req from {conn} {addr}")
#
#            # Create a new thread to handle the connection
#            thread = threading.Thread(target=self.handle_new_conn, args=(conn,addr) )
#            print("[SERVER] Begining new Thread")
#            thread.start()
#            #self.handle_new_conn(conn, addr)
#            print("[SERVER] Began new Thread")
#        return
#
#
#
#    def handle_new_conn(self,conn,addr):
#        '''
#        Method to handle connection
#
#        Steps:
#            - Get a valid username
#                => Server records connection and username
#            - List the All the groups
#
#            -> Begin the remainder of the session
#        '''
#
#        print(f"[SERVER] Requesting name from new conn")
#        # Get the valid username
#        valid_name = False
#        while not valid_name:
#
#            # Create the serial packet object thats going to be sent
#            serial_packet = gen_serialized_packet(PayloadTypes.SERVER_COMMAND,
#                                                    ServerCommands.SEND_USERNAME.value
#                            )
#            # Send the packet object
#            conn.send(serial_packet)
#
#            # Recieve the response from the client
#            raw_recieved = conn.recv(1024)
#
#            # De-serial the packet
#            resp_packet = unserialize_packet(raw_recieved)
#
#            # Check for a valid packet with a valid username
#            if resp_packet.header != PayloadTypes.CLIENT_INFO:
#                # Make sure the packet is of type CLIENT_INFO
#                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO,
#                        f"{Status.ERROR.value} Expected Server Info")
#
#            elif len(resp_packet.contents.split(" ")) != 1:
#                # Check that the username is only one word long
#                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO,
#                        f"{Status.ERROR.value} Username can only be one word")
#
#            elif (username:=resp_packet.contents) in [x for x in self.client_connections_names]:
#                # Check that the username is unique
#                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO,
#                        f"{Status.ERROR.value} Username taken")
#            else:
#                # If we get here, the username is valid
#
#                # Create a ClientConnection object, this holds the actual connection
#                # the username of the connection, and the groups that the connection is apart of
#                client_connection = ClientConnection(conn, username, [])
#                self.client_connections_names.append(client_connection.username)
#
#                # Generate packet to tell client that the username was good
#                serial_packet = gen_serialized_packet(PayloadTypes.STATUS, Status.OK.value)
#
#                # Set valid_name to True to exit the loop
#                valid_name = True
#
#            # Send the serial_packet response to the client
#            conn.send(serial_packet)
#
#        print(f'[USERS] UserCount is {len(self.client_connections_names)}')
#
#        # Handle the remainder of the session
#        self.handle_session(client_connection)
#        return
#
#    #def serve_queue(self):
#    #    '''
#    #        This method is designed to be constantly running on it's own thread
#    #
#    #        This method also EXPECTS that the message queue has perfectly crafted
#    #        messages
#    #    '''
#    #    while self.serving:
#    #
#    #        # If theres no users or theres nothing in the queue do nothing
#    #        if self.payload_queue.empty():
#    #            continue
#    #
#    #        # Now need to parse the QueueObject:
#    #        # | payload type, contents, target |
#    #
#    #        # So grab each conn, and send a package payload
#    #        queue_object = self.payload_queue.get()
#    #
#    #        # Get the encoded version of the payload
#    #        payload = self.package_payload(queue_object.payload_type, queue_object.contents)
#    #
#    #        # Attempt to route the payload to the targets
#    #        for target in queue_object.targets:
#    #            try:
#    #                target.conn.send(payload)
#    #            except Exception as e:
#    #                print(f"Caught an error while sending payload: {e}")
#
#
#    def gen_and_put_queue_payload(self, type_of_payload: PayloadTypes, contents: str, targets: list[ClientConnection]):
#        '''
#            Append the payload type to the contents of the payload,
#            as well as targets, and send to queue as a QueueObject
#        '''
#
#        # Create payload object
#        queue_payload = QueueObject(type_of_payload, contents, targets)
#
#        # Put the Payload onto the que
#        self.payload_queue.put(queue_payload)
#        return
#
#
#
#    def handle_session(self, client_conn: ClientConnection):
#        '''
#        Handle the session for for the user
#        Need to:
#          - listen for messages from the client
#          - check for broadcast messages
#        '''
#        running = True
#        while running:
#
#            # Recieve the response from the client
#            raw_recieved = client_conn.conn.recv(1024)
#
#            # De-serial the packet
#            client_packet = unserialize_packet(raw_recieved)
#
#            # Get just the command from the packet
#            command = client_packet.contents.split(" ")[0]
#
#            # Get everything after the command
#            cmd_args = client_packet.contents.split(" ")[1::]
#
#            # Run a match case on the command
#            match command:
#
#                # ?? How is this supose to work when theres more than
#                #   on group option ?? ->
#                #       TODO: solution for now is to defualt to joining
#                #               the first group
#                case ClientCommands.value.name.JOIN:
#                    # Join a group command
#
#                    # Set the group to join as the first group
#                    group = self.Groups[0]
#
#                    print(f"User, {username} joining group {group_name}")
#
#                    # Only add the connection to group if not already there
#                    if client_connection not in group.client_connections:
#                        self.add_conn_to_group(self, group_name, client_connection)
#
#                    # If we get here, this is the correct group name
#                    status = Status.OK
#
#                    # Need to get the string version of the status
#                    str_status = status.value
#
#                    # Build the resp_serial_packet and send it
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)
#
#                    # Send the packet to the client
#                    client_connection.conn.send(resp_packet)
#
#
#                # ?? How does this work if a user is in multiple
#                # groups ??
#                # @TODO:
#                #   solution for now ->
#                #       post to every group that the user is
#                #       apart of
#                case ClientCommands.POST:
#                    # Command to post a message
#                    # Need to create a post object
#                    # Add post object to a groups message log
#                    #   groups.msg_log(id: PostObject)
#                    # Queue a notification of a post
#
#                    # Need to create a post object:
#                    #   groups: list[str]
#                    #   msg_id: str
#                    #   sender: date
#                    #   date: str
#                    #   subject: str
#                    #   contents: str
#
#
#                    # Get the string of the message
#                    msg = " ".join(cmd_args)
#
#                    # Get the current time
#                    time = datetime.datetime.now()
#                    time = str(time)
#
#                    # Find all the groups that this user is apart of
#                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]
#
#                    total_users = []
#                    # Find all the users in the groups that the client conn is in
#                    for group in groups_conn_is_in:
#                        for userConn in group.client_connection:
#                            if userConn not in total_users:
#                                total_users.append(userConn)
#
#
#                    # Get the post id and increament the post counter
#                    post_id = self.post_counter
#                    self.post_counter+=1
#
#                    # Create the post object
#                    post = PostObject(groups_conn_is_in, post_id, client_connection.username, time, msg)
#
#                    # Add the post to the groups message log
#                    for group in groups_conn_is_in:
#                        group.msg_log[post_counter] = post
#
#                    # Create the queue payload
#                    self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO,
#                            f"{post.msg_id} {post.sender} {time} {post.contents}",
#                            targets=total_users
#                            )
#
#
#
#
#
#                # ?? How is this supose to work when theres more
#                #   than one group ->
#                # TODO: current solution is to list the users of
#                #           every group that the user is apart of
#                case ClientCommands.USERS:
#                    # command to list a user in the group
#
#                    # Find all the groups that this user is apart of
#                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]
#
#                    groups_str_reprs = []
#                    # Now make a list of user for each group
#                    for group in groups_conn_is_in:
#                        str_repr = f"{group.name}: "
#
#                        # Make a list of names in the group 'group'
#                        str_repr += ", ".join([client.name for client in group.client_connections])
#
#                        # Append this str repr to the list of reprs
#                        groups_str_reprs.append(str_repr)
#
#
#                    # Now theres a list of lists of str reprs: "{group.name} name1, name2 , ..., namex"
#                    # Format into one string
#                    ret_str = "\n".join(str_repr for str_repr in groups_str_reprs)
#
#                    # Create the return packet
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, ret_str)
#
#                    # Send the packet
#                    client_connection.conn.send(resp_packet)
#
#                # ?? How should this work if they are in more than one group ??
#                # TODO: Solution for now ->
#                #           Leave all the groups the user is currently in
#                case ClientCommands.LEAVE:
#                    # command to leave the group(s)?
#
#                    # Find all the groups that this user is apart of
#                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]
#
#                    for group in groups_conn_is_in:
#                        self.remove_conn_from_group(group.name, client_connection)
#
#                    # Set the status
#                    status = Status.OK
#                    str_status = status.value
#
#                    # Create the resp packet
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)
#
#                    # Send the packet
#                    client_connection.conn.send(resp_packet)
#
#
#                #case ClientCommand.MESSAGE:
#                #    # command to get the contents of a message
#
#                case ClientCommands.EXIT:
#                #    # command to disconned from server
#
#                    # Make sure to remove the client from all groups
#                    # Find all the groups that this user is apart of
#                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]
#
#                    # Remove the cononection from list of connections in a group
#                    for group in groups_conn_is_in:
#                        self.remove_conn_from_group(group.name, client_connection)
#
#                    # Close the client socket
#                    client_connection.conn.close()
#
#                    # Remove the connection from the list of connections
#                    self.client_connections_names.remove(client_connection.username)
#
#
#
#                case ClientCommands.GROUPS:
#                    # command to list groups
#                    # CONTENTS RETURN (not a status return)
#
#                    # Return a str of group names seperated by commas
#                    group_names = ",".join[group.name for group in self.Groups]
#
#                    # Gen packet
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, group_names)
#
#                    # Send the packet
#                    client_connection.conn.send(resp_packet)
#
#                case ClientCommands.GROUPJOIN:
#                    # Command to join a group
#
#                    # Get the group name
#                    group_name = cmd_args.split(" ")[1]
#                    status = Status.ERROR
#                    for group in self.Groups:
#                        # If this isn't the correct group name move onto the next group
#                        if group_name != group.name:
#                            continue
#
#                        # If we get here, this is the correct group name
#                        status = Status.OK
#                        print(f"User, {username} joining group {group_name}")
#
#                        # Only add the connection to the group's list of conns if
#                        # it's not already there
#                        if client_connection not in group.client_connections:
#                            self.add_conn_to_group(self, group_name, client_connection)
#
#                    # Need to get the string version of the status
#                    str_status = status.value
#
#                    # Build the resp_serial_packet and send it
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)
#
#                    # Send the packet to the client
#                    client_connection.conn.send(resp_packet)
#
#
#                case ClientCommands.GROUPPOST:
#                    # Command to get post to a group
#
#                    # Add post object to a groups message log
#                    #   groups.msg_log(id: PostObject)
#                    # Queue a notification of a post
#
#                    # Need to create a post object:
#                    #   groups: list[str]
#                    #   msg_id: str
#                    #   sender: date
#                    #   date: str
#                    #   subject: str
#                    #   contents: str
#
#
#                    # The group to send the messge to is the first argument
#                    group_to_post_to = cmd_args[0]
#
#                    # Get the string of the message
#                    msg = " ".join(cmd_args[1::])
#
#                    # Get the current time
#                    time = datetime.datetime.now()
#                    time = str(time)
#
#                    # Make sure the group is a good group
#                    for group in self.Groups:
#                        # If this isn't the correct group name move onto the next group
#                        if group_name != group.name:
#                            continue
#
#                        # If we get here, this is the correct group name
#                        targets = group.client_connections
#                        found_group = True
#                        post_group = group
#                        break
#
#                    # If the group doesn't exist raise an error
#                    if not found_group:
#                        raise ClientCommandError
#
#                    # Get the post id and increament the post counter
#                    post_id = self.post_counter
#                    self.post_counter+=1
#
#                    # Create the post object
#                    post = PostObject(post_group, post_id, client_connection.username, time, msg)
#
#                    # Add the post to the groups message log
#                    post_group.msg_log[post_counter] = post
#
#                    # Create the queue payload
#                    self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO,
#                            f"{post.msg_id} {post.sender} {time} {post.contents}",
#                            targets=total_users
#                            )
#
#
#                case ClientCommands.GROUPUSERS:
#                    # Command to get a list of members in a gorup
#
#                    # Get the argument for the group to leave
#                    group_name = cmd_args[0]
#
#                    names_rep = ""
#
#                    # Get the group object for the group
#                    for group in self.Groups:
#                        # If this isn't the correct name move onto the next iteration
#                        if group.name != group_name:
#                            continue
#
#                        # If we get here we are at the correct group object
#                        names_repr = ", ".join([group.name for group in group.client_connections])
#
#                    # Generate resp_packet
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, names_repr)
#
#                    # Send the packet
#                    client_connection.conn.send(resp_packet)
#
#                case ClientCommands.GROUPLEAVE:
#                    # Command to leave a group
#
#                    # Get the argument for the group to leave
#                    group_name = cmd_args[0]
#
#                    # Get the group object for the group
#                    for group in self.Groups:
#                        # If this is the correct group, remove conn and break
#                        if group_name == group.name:
#                            # Remove the conn and break
#                            self.remove_conn_from_group(group_name, client_connection)
#                            break
#
#                    # Set the status
#                    status = status.OK
#                    str_status = status.value
#
#                    # gen the resp_packet
#                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)
#
#                    # Send the packet
#                    client_connection.conn.send(resp_packet)
#
#
#                #case ClientCommand.GROUPMESSAGE:
#                #    # Command to get a group message
#                #case _:
#                #    raise ClientParseError(f"No command: {command}")
#            #except Exception as e:
#            #    print("Error in client {e}: Sending error response...")
#            #    self.send_error(client_connection)
#
#    def send_error(self, client_conn)-> None:
#        '''
#            Send an error message to client
#
#            This is a server info packet
#        '''
#        # Generate the error payload and add to queue
#        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO,
#                str(ServerInfo.ERROR.value),
#                targets=[client_conn]
#                )
#        return
#
#    def remove_conn_from_group(self, group_name: str, client_conn: ClientConnection):
#        '''
#            Add the connection to a group
#            - Remove the group name to the client connection info
#            - Remove the client connection to the group
#            - Add a server info message to the queue for the remove notice
#                with a target of the new group
#        '''
#
#        # Have to find the group object in the list of groups
#        for group_obj in self.groups:
#            if group_obj.name == group_name:
#                new_group = group_obj
#                break
#
#        # Append the name of the group to the client connection
#        if new_group.name in ClientConnection.group_names:
#            client_conn.group_names.remove(new_group.name)
#
#        # Append the clientconnection object to the group
#        if ClientConnection in new_group.client_connections:
#            new_group.client_connections.remove(ClientConnection)
#
#        # Get a list of the targets for the payload
#        targets = [x for x in self.new_group.client_connections]
#
#        # Generate the queue payload
#        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO,
#                f"[INFO]User {client_conn.username} has left the group {new_group.name}",
#                targets
#                )
#
#
#
#    def add_conn_to_group(self,group_name: str, client_conn: ClientConnection):
#        '''
#            Add the connection to a group
#            - Add the group name to the client connection info
#            - Add the client connection to the group
#            - Add a server info message to the queue for the connection notice
#                with a target of the new group
#        '''
#
#        # Have to find the group object in the list of groups
#        for group_obj in self.groups:
#            if group_obj.name == group_name:
#                new_group = group_obj
#                break
#
#        # Append the name of the group to the client connection
#        if new_group.name not in ClientConnection.group_names:
#            client_conn.group_names.append(new_group.name)
#
#        # Append the clientconnection object to the group
#        if ClientConnection not in new_group.client_connections:
#            new_group.client_connections.append(ClientConnection)
#
#        # Get a list of the targets for the payload
#        targets = [x for x in self.new_group.client_connections]
#
#        # Generate the queue payload
#        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO,
#                f"[INFO]New user {client_conn.username} has joined the group {new_group.name}",
#                targets
#                )

if __name__ == '__main__':

    groups = ['Group1', 'Group2', 'Group3', 'Group4', 'Group5']

    mServer = MasterGroupServer('0.0.0.0', 8000, groups)

    print("About to serve...")
    mServer.serve_forever()
