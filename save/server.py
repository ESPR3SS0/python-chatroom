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
import threading
import select
import queue

import datetime

from dataclasses import dataclass
from enum import Enum

from packet import PayloadTypes, Packet, gen_packet, \
                    gen_serialized_packet, unserialize_packet

from commands import ClientCommands, ServerCommands, Status

from errors import *

@dataclass 
class ClientConnection:
    conn: socket.socket
    username: str
    group_names: list[str]


@dataclass
class PostObject:
    groups: list[str]

    msg_id: int
    sender: str
    date: str
    contents: str

@dataclass 
class GroupObject:
    name: str
    client_connections: list[ClientConnection]
    msg_log: dict[int: PostObject]

@dataclass 
class QueueObject:
    # This is the same as the protocol with one addition
    payload_type: PayloadTypes
    contents: str

    # Need a list of target connections to send to 
    targets : list[ClientConnection]


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

class socketServer:
    def __init__(self, host, port):
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

      # List of msgObjs that need to be sent 
      self.payload_queue = queue.Queue()

      # List of  ClientConnection objects
      self.client_connections_names = []

      # List of different groups that a client can join
      self.groups = [
                     GroupObject("PRIVATE1",[],{}),
                     GroupObject("PRIVATE2",[], {}),
                     GroupObject("PRIVATE3",[], {}),
                     GroupObject("PRIVATE4",[], {}),
                     GroupObject("PRIVATE5",[], {}),
                    ]
      self.serving = False

      self.server_log = []

        # post counter is going to incrament with every 
        # post and will be the post id
      self.post_counter = 0

    def begin_serving(self):
        '''
        Listen forever on sock and throw new
        connections onto new threads
        '''

        
        self.serving = True
        thread = threading.Thread(target=self.serve_queue)

        print(f"[SERVER] Now serving on {self.host}:{self.port}")

        # Begin listening on socket
        self.sock.listen()
        
        while True:

            # Accept new connection
            conn, addr = self.sock.accept()

            # Verbose print if desired
            print(f"[CONN] New req from {conn} {addr}")

            # Create a new thread to handle the connection
            thread = threading.Thread(target=self.handle_new_conn, args=(conn,addr) )
            print("[SERVER] Begining new Thread")
            thread.start()
            #self.handle_new_conn(conn, addr)
            print("[SERVER] Began new Thread")
        return
      


    def handle_new_conn(self,conn,addr):
        '''
        Method to handle connection

        Steps:
            - Get a valid username 
                => Server records connection and username
            - List the All the groups

            -> Begin the remainder of the session
        '''

        print(f"[SERVER] Requesting name from new conn")
        # Get the valid username
        valid_name = False
        while not valid_name:
            
            # Create the serial packet object thats going to be sent
            serial_packet = gen_serialized_packet(PayloadTypes.SERVER_COMMAND,
                                                    ServerCommands.SEND_USERNAME.value
                            )
            # Send the packet object
            conn.send(serial_packet)

            # Recieve the response from the client 
            raw_recieved = conn.recv(1024)

            # De-serial the packet 
            resp_packet = unserialize_packet(raw_recieved)

            # Check for a valid packet with a valid username
            if resp_packet.header != PayloadTypes.CLIENT_INFO:
                # Make sure the packet is of type CLIENT_INFO
                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, 
                        f"{Status.ERROR.value} Expected Server Info")

            elif len(resp_packet.contents.split(" ")) != 1:
                # Check that the username is only one word long
                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, 
                        f"{Status.ERROR.value} Username can only be one word")

            elif (username:=resp_packet.contents) in [x for x in self.client_connections_names]:
                # Check that the username is unique
                serial_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, 
                        f"{Status.ERROR.value} Username taken")
            else:
                # If we get here, the username is valid

                # Create a ClientConnection object, this holds the actual connection
                # the username of the connection, and the groups that the connection is apart of 
                client_connection = ClientConnection(conn, username, [])
                self.client_connections_names.append(client_connection.username)

                # Generate packet to tell client that the username was good
                serial_packet = gen_serialized_packet(PayloadTypes.STATUS, Status.OK.value)

                # Set valid_name to True to exit the loop
                valid_name = True

            # Send the serial_packet response to the client
            conn.send(serial_packet)

        print(f'[USERS] UserCount is {len(self.client_connections_names)}')

        # Handle the remainder of the session
        self.handle_session(client_connection)
        return

    def serve_queue(self):
        '''
            This method is designed to be constantly running on it's own thread
    
            This method also EXPECTS that the message queue has perfectly crafted 
            messages
        '''
        while self.serving:
    
            # If theres no users or theres nothing in the queue do nothing
            if self.payload_queue.empty():
                continue
    
            # Now need to parse the QueueObject:
            # | payload type, contents, target | 
    
            # So grab each conn, and send a package payload 
            queue_object = self.payload_queue.get()
    
            # Get the encoded version of the payload 
            payload = self.package_payload(queue_object.payload_type, queue_object.contents)
    
            # Attempt to route the payload to the targets
            for target in queue_object.targets:
                try:
                    target.conn.send(payload)
                except Exception as e:
                    print(f"Caught an error while sending payload: {e}")
    
    
    def gen_and_put_queue_payload(self, type_of_payload: PayloadTypes, contents: str, targets: list[ClientConnection]):
        '''
            Append the payload type to the contents of the payload, 
            as well as targets, and send to queue as a QueueObject
        '''
    
        # Create payload object
        queue_payload = QueueObject(type_of_payload, contents, targets)
    
        # Put the Payload onto the que
        self.payload_queue.put(queue_payload)
        return
    
    
    
    def handle_session(self, client_conn: ClientConnection):
        '''
        Handle the session for for the user
        Need to:
          - listen for messages from the client 
          - check for broadcast messages
        '''
        running = True
        while running:

            # Recieve the response from the client 
            raw_recieved = client_conn.conn.recv(1024)

            # De-serial the packet 
            client_packet = unserialize_packet(raw_recieved)

            # Get just the command from the packet
            command = client_packet.contents.split(" ")[0]

            # Get everything after the command
            cmd_args = client_packet.contents.split(" ")[1::] 

            # Run a match case on the command 
            match command:

                # ?? How is this supose to work when theres more than
                #   on group option ?? -> 
                #       TODO: solution for now is to defualt to joining 
                #               the first group
                case ClientCommand.value.name.JOIN:
                    # Join a group command

                    # Set the group to join as the first group
                    group = self.Groups[0]

                    print(f"User, {username} joining group {group_name}")

                    # Only add the connection to group if not already there
                    if client_connection not in group.client_connections:
                        self.add_conn_to_group(self, group_name, client_connection)

                    # If we get here, this is the correct group name
                    status = Status.OK

                    # Need to get the string version of the status
                    str_status = status.value

                    # Build the resp_serial_packet and send it 
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)

                    # Send the packet to the client
                    client_connection.conn.send(resp_packet)


                # ?? How does this work if a user is in multiple 
                # groups ??
                # @TODO:
                #   solution for now ->
                #       post to every group that the user is 
                #       apart of 
                case ClientCommand.POST:
                    # Command to post a message
                    # Need to create a post object
                    # Add post object to a groups message log
                    #   groups.msg_log(id: PostObject)
                    # Queue a notification of a post 

                    # Need to create a post object:
                    #   groups: list[str]
                    #   msg_id: str
                    #   sender: date
                    #   date: str
                    #   subject: str
                    #   contents: str


                    # Get the string of the message
                    msg = " ".join(cmd_args)

                    # Get the current time
                    time = datetime.datetime.now()
                    time = str(time)

                    # Find all the groups that this user is apart of 
                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]

                    total_users = []
                    # Find all the users in the groups that the client conn is in
                    for group in groups_conn_is_in:
                        for userConn in group.client_connection:
                            if userConn not in total_users:
                                total_users.append(userConn)


                    # Get the post id and increament the post counter
                    post_id = self.post_counter
                    self.post_counter+=1

                    # Create the post object
                    post = PostObject(groups_conn_is_in, post_id, client_connection.username, time, msg)

                    # Add the post to the groups message log 
                    for group in groups_conn_is_in:
                        group.msg_log[post_counter] = post

                    # Create the queue payload
                    self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO, 
                            f"{post.msg_id} {post.sender} {time} {post.contents}",
                            targets=total_users
                            )





                # ?? How is this supose to work when theres more 
                #   than one group ->
                # TODO: current solution is to list the users of 
                #           every group that the user is apart of 
                case ClientCommand.USERS:
                    # command to list a user in the group 

                    # Find all the groups that this user is apart of 
                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]

                    groups_str_reprs = []
                    # Now make a list of user for each group
                    for group in groups_conn_is_in:
                        str_repr = f"{group.name}: "

                        # Make a list of names in the group 'group'
                        str_repr += ", ".join([client.name for client in group.client_connections])

                        # Append this str repr to the list of reprs
                        groups_str_reprs.append(str_repr)


                    # Now theres a list of lists of str reprs: "{group.name} name1, name2 , ..., namex"
                    # Format into one string
                    ret_str = "\n".join(str_repr for str_repr in groups_str_reprs)

                    # Create the return packet
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, ret_str)

                    # Send the packet
                    client_connection.conn.send(resp_packet)

                # ?? How should this work if they are in more than one group ??
                # TODO: Solution for now ->
                #           Leave all the groups the user is currently in
                case ClientCommand.LEAVE:
                    # command to leave the group(s)?

                    # Find all the groups that this user is apart of 
                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]

                    for group in groups_conn_is_in:
                        self.remove_conn_from_group(group.name, client_connection)

                    # Set the status
                    status = Status.OK
                    str_status = status.value

                    # Create the resp packet
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)

                    # Send the packet
                    client_connection.conn.send(resp_packet)


                #case ClientCommand.MESSAGE:
                #    # command to get the contents of a message

                case ClientCommand.EXIT:
                #    # command to disconned from server
                    
                    # Make sure to remove the client from all groups 
                    # Find all the groups that this user is apart of 
                    groups_conn_is_in = [group for group in self.Groups if client_connection in group.client_connections]

                    # Remove the cononection from list of connections in a group
                    for group in groups_conn_is_in:
                        self.remove_conn_from_group(group.name, client_connection)

                    # Close the client socket
                    client_connection.conn.close()

                    # Remove the connection from the list of connections
                    self.client_connections_names.remove(client_connection.username)
                    
                    

                case ClientCommand.GROUPS:
                    # command to list groups
                    # CONTENTS RETURN (not a status return)

                    # Return a str of group names seperated by commas
                    group_names = ",".join[group.name for group in self.Groups]

                    # Gen packet
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, group_names)

                    # Send the packet
                    client_connection.conn.send(resp_packet)

                case ClientCommand.GROUPJOIN:
                    # Command to join a group

                    # Get the group name
                    group_name = cmd_args.split(" ")[1]
                    status = Status.ERROR
                    for group in self.Groups:
                        # If this isn't the correct group name move onto the next group
                        if group_name != group.name:
                            continue

                        # If we get here, this is the correct group name
                        status = Status.OK
                        print(f"User, {username} joining group {group_name}")

                        # Only add the connection to the group's list of conns if 
                        # it's not already there
                        if client_connection not in group.client_connections:
                            self.add_conn_to_group(self, group_name, client_connection)

                    # Need to get the string version of the status
                    str_status = status.value

                    # Build the resp_serial_packet and send it 
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)

                    # Send the packet to the client
                    client_connection.conn.send(resp_packet)


                case ClientCommand.GROUPPOST:
                    # Command to get post to a group

                    # Add post object to a groups message log
                    #   groups.msg_log(id: PostObject)
                    # Queue a notification of a post 

                    # Need to create a post object:
                    #   groups: list[str]
                    #   msg_id: str
                    #   sender: date
                    #   date: str
                    #   subject: str
                    #   contents: str


                    # The group to send the messge to is the first argument
                    group_to_post_to = cmd_args[0]
                    
                    # Get the string of the message
                    msg = " ".join(cmd_args[1::])

                    # Get the current time
                    time = datetime.datetime.now()
                    time = str(time)

                    # Make sure the group is a good group
                    for group in self.Groups:
                        # If this isn't the correct group name move onto the next group
                        if group_name != group.name:
                            continue

                        # If we get here, this is the correct group name
                        targets = group.client_connections
                        found_group = True
                        post_group = group
                        break

                    # If the group doesn't exist raise an error
                    if not found_group:
                        raise ClientCommandError

                    # Get the post id and increament the post counter
                    post_id = self.post_counter
                    self.post_counter+=1

                    # Create the post object
                    post = PostObject(post_group, post_id, client_connection.username, time, msg)

                    # Add the post to the groups message log 
                    post_group.msg_log[post_counter] = post

                    # Create the queue payload
                    self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO, 
                            f"{post.msg_id} {post.sender} {time} {post.contents}",
                            targets=total_users
                            )


                case ClientCommand.GROUPUSERS:
                    # Command to get a list of members in a gorup

                    # Get the argument for the group to leave
                    group_name = cmd_args[0]

                    names_rep = ""

                    # Get the group object for the group
                    for group in self.Groups:
                        # If this isn't the correct name move onto the next iteration
                        if group.name != group_name:
                            continue

                        # If we get here we are at the correct group object
                        names_repr = ", ".join([group.name for group in group.client_connections])

                    # Generate resp_packet
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, names_repr)

                    # Send the packet 
                    client_connection.conn.send(resp_packet)
 
                case ClientCommand.GROUPLEAVE:
                    # Command to leave a group
                        
                    # Get the argument for the group to leave
                    group_name = cmd_args[0]

                    # Get the group object for the group
                    for group in self.Groups:
                        # If this is the correct group, remove conn and break
                        if group_name == group.name:
                            # Remove the conn and break
                            self.remove_conn_from_group(group_name, client_connection)
                            break

                    # Set the status
                    status = status.OK
                    str_status = status.value

                    # gen the resp_packet
                    resp_packet = gen_serialized_packet(PayloadTypes.SERVER_INFO, str_status)

                    # Send the packet 
                    client_connection.conn.send(resp_packet)
                        

                #case ClientCommand.GROUPMESSAGE:
                #    # Command to get a group message
                #case _:
                #    raise ClientParseError(f"No command: {command}")
            #except Exception as e:
            #    print("Error in client {e}: Sending error response...")
            #    self.send_error(client_connection)
    
    def send_error(self, client_conn)-> None:
        '''
            Send an error message to client 

            This is a server info packet
        '''
        # Generate the error payload and add to queue
        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO, 
                str(ServerInfo.ERROR.value),
                targets=[client_conn]
                )
        return 

    def remove_conn_from_group(self, group_name: str, client_conn: ClientConnection):
        '''
            Add the connection to a group
            - Remove the group name to the client connection info 
            - Remove the client connection to the group
            - Add a server info message to the queue for the remove notice 
                with a target of the new group
        '''

        # Have to find the group object in the list of groups
        for group_obj in self.groups:
            if group_obj.name == group_name:
                new_group = group_obj
                break

        # Append the name of the group to the client connection
        if new_group.name in ClientConnection.group_names:
            client_conn.group_names.remove(new_group.name)

        # Append the clientconnection object to the group
        if ClientConnection in new_group.client_connections:
            new_group.client_connections.remove(ClientConnection)

        # Get a list of the targets for the payload
        targets = [x for x in self.new_group.client_connections]

        # Generate the queue payload
        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO, 
                f"[INFO]User {client_conn.username} has left the group {new_group.name}",
                targets
                )



    def add_conn_to_group(self,group_name: str, client_conn: ClientConnection):
        '''
            Add the connection to a group
            - Add the group name to the client connection info 
            - Add the client connection to the group
            - Add a server info message to the queue for the connection notice 
                with a target of the new group
        '''

        # Have to find the group object in the list of groups
        for group_obj in self.groups:
            if group_obj.name == group_name:
                new_group = group_obj
                break

        # Append the name of the group to the client connection
        if new_group.name not in ClientConnection.group_names:
            client_conn.group_names.append(new_group.name)

        # Append the clientconnection object to the group
        if ClientConnection not in new_group.client_connections:
            new_group.client_connections.append(ClientConnection)

        # Get a list of the targets for the payload
        targets = [x for x in self.new_group.client_connections]

        # Generate the queue payload
        self.gen_and_put_queue_payload(PayloadTypes.SERVER_INFO, 
                f"[INFO]New user {client_conn.username} has joined the group {new_group.name}",
                targets
                )


if __name__ == '__main__':
    sockServer = socketServer('0.0.0.0', 8000)
    sockServer.begin_serving()
