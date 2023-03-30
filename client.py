'''
    NEED TO USE select.select
'''




from packet import PayloadTypes, Packet, gen_packet, \
                    gen_serialized_packet, unserialize_packet

from errors import CommandGenerationError, ClientCommandError

from commands import ClientCommands, ServerCommands, \
        gen_client_cmd_from_raw

import socket
import threading

import sys

import select



class socketClient:
    def __init__(self):
        self.port = None
        self.host = None
        self.server_sock = None
        self.prompt = ">>"

        self.connected = False


        self.readables = [self.server_sock, sys.stdin]

    def pre_connect(self):
        '''
            Before the client is connect, the only 
            available commands are connect and exit 
        '''
        inp = input(self.prompt)
        command = inp.split(" ")[0]
        match command: 
            case ClientCommands.CONNECT.value:
                try:
                    self.host, self.port = str(inp.split(" ")[1]), int(inp.split(" ")[2])
                except Exception as e:
                    print("Bad command input, connect follows this pattern: connect <host> <port>")
                    #continue
                    return

                # Connect the socket
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.connect((self.host, self.port))

                print("Expecting server to ask for username")
                # If this is the first time getting connected 
                # The server will immediately request for a username
                self.setup_username()
            case ClientCommands.EXIT.value:
                # Quit the program
                print("Quitting")
                return
            case _:
                print(f"No command for: {inp}")

    def shell_wrapper(self):
        while True:
            try:
                self.enter_shell()
            except ClientCommandError as e:
                print(f"Command Error {e}")


    def enter_shell(self):

        # Before any other command can be ran, the user 
        # either needs to connect or exit 
        while not self.connected:
            self.pre_connect()
            
        print("Entering Session loop with connection")
        #print(self.prompt, end="")
        #sys.stdout.write(">>>")
        # At this point a connection has been established
        done = False
        while not done:
            inp = str(input(">>>"))

            # Make sure the input wasn't just enter
            if inp == "":
                continue

            #command = inp.split(" ")[0]
            try:
                command = gen_client_cmd_from_raw(inp)
            except CommandGenerationError as e:
                print(f"Command not available: {inp.split(' ')[0]}")
                continue

            # Make sure that the command is an available command
            #if command not in [x.value for x in ClientCommands]:
            #    print(f"Command not available: {command}")
            #    continue 
            # Make sure that the client is connect before running 
            # any other command
            #elif (command not in ClientCommands.CONNECT.value) and self.connected == False:
            #    print(f"Must be connected to a server before running command: {command}")
            #    continue
            match command.name:
                case ClientCommands.CONNECT.value:
                    if self.connected:
                        print("Already connected")

                        # joining the main group
                case ClientCommands.JOIN.value:
                    '''
                        when the join command is stated 
                    '''
                    print("\n Sending join request to server...")
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # sending a message to the main group
                case ClientCommands.POST.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # responds with a list of users in the main group
                case ClientCommands.USERS.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to open a message
                case ClientCommands.MESSAGE.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to see all groups
                case ClientCommands.GROUPS.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to join a group
                case ClientCommands.GROUPJOIN.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to see message in group
                case ClientCommands.GROUPMESSAGE.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to post in group
                case ClientCommands.GROUPPOST.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to see all the users in a group
                case ClientCommands.GROUPUSERS.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to leave a group
                case ClientCommands.GROUPLEAVE.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # command to leave
                case ClientCommands.LEAVE.value:
                    serial_packet = gen_serialized_packet(
                        PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                    # the command to leave the server
                case ClientCommands.EXIT.value:
                    # Quit the program
                    print("Leaving client and server program.... Bye")
                    print("        ~hasta la vista baby~")
                    sys.exit()

                case ClientCommands.JOIN.value:
                    print(f"Command: {command.name} not done")

            

    def setup_username(self):
        '''
            Invoked immediately when the connection is 
            first started
        '''

        # Get the incoming request for username
        #resp = self.server_sock.recv(1024)
        #recieved_packet = unserialize_packet(resp)

        # If we get here the server has now requested 
        #   for the username from this client 
        #   prompt the user and ask for username
        username = input("Input Username:")

        serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_INFO, f"username {username}")
        self.server_sock.send(serial_packet)

        print("Waiting for server response to username")
        resp = self.server_sock.recv(1024)
        #resp = resp.decode()
        resp = unserialize_packet(resp)

        if "ok" not in resp.contents.lower():
            # The server was not happy with the username 
            print("Server did not like username")
            self.setup_username()
        else:
            print("Username Setup")
            self.connected = True

        # If we get here, the server is happy with the username






    def listen_thread(self):
        '''
            Thread that constantly listens for 
            messages from the server
        '''
        done = False 
        data = ''
        while not done:
            msg = self.recv_from_server(self)
            print(f"msg: {msg}")

            # Protocol from the server is:
            # | PayloadType | Content

            match msg.split(" ")[0]:
                case PayloadTypes.SERVER_INFO:
                    pass

                case PayloadTypes.SERVER_COMMAND:
                    #if ServerCommands.Username = msg.split(" ")[1]:
                    pass






if __name__ == "__main__":
    client_one = socketClient()
    #client_one.enter_shell()
    client_one.shell_wrapper()

