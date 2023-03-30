'''
    NEED TO USE select.select
'''




from packet import PayloadTypes, Packet, gen_packet, \
                    gen_serialized_packet, unserialize_packet

from errors import CommandGenerationError

from commands import ClientCommands, ServerCommands, \
        gen_client_cmd_from_raw

import socket
import threading

import sys

import select


def myPrint(msg: str)-> None:
    sys.stdout(msg)
    sys.stdout.write(inp)
    #sys.stdout.flush()

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

            #print(self.prompt, end="")
            readable, _, error = select.select([self.server_sock, sys.stdin], [],[])

            for read in readable:
                if read == self.server_sock:
                    self.handle_server_read()
                else:
                    inp = sys.stdin.readline()
                    sys.stdout.write("<Your inp>")
                    sys.stdout.write(inp)
                    sys.stdout.flush()

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
                                continue
                        case ClientCommands.EXIT.value:
                            # Quit the program
                            done = True
                            return
                        case ClientCommands.JOIN.value:
                            print(f"Command: {command.name} not done")




    def setup_username(self):
        '''
            Invoked immediately when the connection is 
            first started
        '''

        print("Lsitening for server...")
        resp = self.server_sock.recv(1024)
        print(f"Before unpickled: {resp}")
        recieved_packet = unserialize_packet(resp)
        print(f"After unpickle: {recieved_packet}")
        if "username" not in recieved_packet.contents.lower():
            print("did not get username resp")
            self.setup_username()

        # If we get here the server has now requested 
        #   for the username from this client 
        #   prompt the user and ask for username
        username = input("Input Username:")

        serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_INFO, username)
        self.server_sock.send(serial_packet)

        resp = self.server_sock.recv(1024)
        #resp = resp.decode()
        resp = unserialize_packet(resp)

        if "ok" not in resp.contents.lower():
            # The server was not happy with the username 
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





    def recv_from_server(self):
        data = ''
        done = False
        while not done:
            new_data = self.server_sock.recv(1024).decode()
            if new_data == '':
                done = True
            else:
                data += new_data
        return new_data

    def send_raw_command_in(self, raw_inp):
        self.server_sock()



if __name__ == "__main__":
    client_one = socketClient()
    client_one.enter_shell()







