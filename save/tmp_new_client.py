'''
    NEED TO USE select.select
'''

from pyautogui import typewrite

from packet import PayloadTypes, Packet, gen_packet, \
    gen_serialized_packet, unserialize_packet

from errors import CommandGenerationError

from commands import ClientCommands, ServerCommands, \
    gen_client_cmd_from_raw

from threading import Timer
from time import sleep
import time
import socket
import threading
import keyboard

import sys

import select


class socketClient:

    def __init__(self):
        self.timeInput = " >> "
        self.refresh = False
        self.discontinue = False
        self.port = None
        self.host = None
        self.server_sock = None
        self.prompt = " >> "

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
                    self.host, self.port = str(
                        inp.split(" ")[1]), int(inp.split(" ")[2])
                except Exception as e:
                    print(
                        "Bad command input, connect follows this pattern: connect <host> <port>")
                    # continue
                    return

                # Connect the socket
                self.server_sock = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.connect((self.host, self.port))

                print("Expecting server to ask for username")
                # If this is the first time getting connected
                # The server will immediately request for a username
                self.setup_username()

            # the command to leave the server
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
        # print(self.prompt, end="")
        # sys.stdout.write(">>>")
        # At this point a connection has been established
        done = False

        while not done:

            self.handleInput()
            self.listen_thread()
            print("\n")
            # sleep(1)
            # print(self.prompt, end="")
            # readable, _, error = select.select([self.server_sock, sys.stdin], [],[])

            # for read in readable:
            #     if read == self.server_sock:
            #         self.handle_server_read()
            #     else:
            #         inp = sys.stdin.readline()
            #         sys.stdout.write("<Your inp>")
            #         sys.stdout.write(inp)
            #         sys.stdout.flush()

            # Make sure the input wasn't just enter
            # if inp == "":
            #     continue

            # command = inp.split(" ")[0]
            # try:
            #     command = gen_client_cmd_from_raw(inp)
            # except CommandGenerationError as e:
            #     print(f"Command not available: {inp.split(' ')[0]}")
            #     continue

            # Make sure that the command is an available command
            # if command not in [x.value for x in ClientCommands]:
            #    print(f"Command not available: {command}")
            #    continue
            # Make sure that the client is connect before running
            # any other command
            # elif (command not in ClientCommands.CONNECT.value) and self.connected == False:
            #    print(f"Must be connected to a server before running command: {command}")
            #    continue

            # match command.name:
            #     case ClientCommands.CONNECT.value:
            #         if self.connected:
            #             print("Already connected")
            #             continue
            #     #joining the main group
            #     case ClientCommands.JOIN.value:
            #         print("joined group")
            #     #sending a message to the main group
            #     case ClientCommands.POST.value:
            #         print("posting shit")
            #     #responds with a list of users in the main group
            #     case ClientCommands.USERS.value:
            #         print("listing shit")
            #     #command to open a message
            #     case ClientCommands.MESSAGE.value:
            #         print("listing message")
            #     #command to see all of the groups avaliable
            #     case ClientCommands.GROUPS.value:
            #         print("listing shit")
            #     #command to join one of the groups
            #     case ClientCommands.GROUPJOIN.value:
            #         print("group join shit")
            #     #command to see a message in the group
            #     case ClientCommands.GROUPMESSAGE.value:
            #         print("viewing group shit")
            #     #command to send a message to the group
            #     case ClientCommands.GROUPPOST.value:
            #         print()
            #     #command to see all the users in the group
            #     case ClientCommands.GROUPUSERS.value:
            #         print()
            #     #command to leave the current group
            #     case ClientCommands.GROUPLEAVE.value:
            #         print()
            #     #command to leave the main group
            #     case ClientCommands.LEAVE.value:
            #         print()
            #     #the command to leave the server
            #     case ClientCommands.EXIT.value:
            #         # Quit the program
            #         print("Quitting")
            #         return
            #     case ClientCommands.JOIN.value:
            #         print(f"Command: {command.name} not done")

    # upon exit, the bool value of discontinue is true
    # prints refresh text
    # then uses the keyboard library to press enter without an physcial key command

    def exit_(self):
        self.discontinue = True
        print("\n")
        print("30 seconds without refresh... updating feed")
        keyboard.press_and_release('enter')

    # when handling the inputs from the client
    def handleInput(self):

        self.discontinue = False
        # input time to judge how long the input will stay open before refreshing
        input_time = 10
        # timer, with a conditional for when the timer is done, which is the exit function above
        t = Timer(input_time, self.exit_, )
        # starting timer
        t.start()
        loop_index = 0

        start_time = time.time()
        new_time = 0

        # loops for one loop until listening again

        while (new_time - start_time < 0):

            new_time = time.time()
            # input(prompt)
            #sys.stdout.write(">> ")

            # initializing the input as, well, nothing
            inp = "nothing"

            # input with prompt depending on the refresh boolean
            # use normal input if no refresh has been triggered
            # else if a refresh has been triggered, use the typewrite method

            if (self.refresh == False):
                inp = str(input(self.prompt))
                self.timeInput = inp

            elif (self.refresh == True):
                typewrite(self.timeInput)
                inp = input(" >> ")
                self.timeInput = inp

            # if there is an input, and it reaches here, cancel timer
            t.cancel()

            # if there is dicsontinutation, via timer refresh, and the refresh bool is false
            # with the boolean value of discontinued given by the exit function
            # then set refresh bool to true, and break loop
            if (self.discontinue == True):
                self.refresh = True
                print("\n")
                break

            # if no refresh, or no current discontinue, set them back to defaults
            self.discontinue = False
            self.refresh = False
            self.prompt = " >> "

            # if a refresh has been triggered by the enter key, no other command
            if (inp == ""):
                self.prompt = " >> "
                self.discontinue = False
                print("\n")
                break

            tryCommand = True
            try:
                command = gen_client_cmd_from_raw(inp)
            except CommandGenerationError as e:
                tryCommand = False
                print(f"Command not available: {inp.split(' ')[0]}")

                # Make sure that the command is an available command
                # if command not in [x.value for x in ClientCommands]:
                #    print(f"Command not available: {command}")
                #    continue
                # Make sure that the client is connect before running
                # any other command
                # elif (command not in ClientCommands.CONNECT.value) and self.connected == False:
                #    print(f"Must be connected to a server before running command: {command}")
                #    continue

            if (tryCommand == True):
                match command.name:
                    case ClientCommands.CONNECT.value:
                        if self.connected:
                            print("Already connected")

                            # joining the main group
                    case ClientCommands.JOIN.value:
                        print("joined group")

                        # sending a message to the main group
                    case ClientCommands.POST.value:
                        print("posting shit")
                        # responds with a list of users in the main group
                    case ClientCommands.USERS.value:
                        print("listing shit")
                        # command to open a message
                    case ClientCommands.MESSAGE.value:
                        print("listing message")
                        # command to see all of the groups avaliable
                    case ClientCommands.GROUPS.value:
                        print("listing shit")
                        # command to join one of the groups
                    case ClientCommands.GROUPJOIN.value:
                        print("group join shit")
                        # command to see a message in the group
                    case ClientCommands.GROUPMESSAGE.value:
                        print("viewing group shit")
                        # command to send a message to the group
                    case ClientCommands.GROUPPOST.value:
                        print()
                        # command to see all the users in the group
                    case ClientCommands.GROUPUSERS.value:
                        print()
                        # command to leave the current group
                    case ClientCommands.GROUPLEAVE.value:
                        print()
                        # command to leave the main group
                    case ClientCommands.LEAVE.value:
                        command.args
                        print()
                        # the command to leave the server
                    case ClientCommands.EXIT.value:
                        # Quit the program
                        print("Quitting")
                    case ClientCommands.JOIN.value:
                        print(f"Command: {command.name} not done")
            loop_index = loop_index + 1

    def setup_username(self):
        '''
            Invoked immediately when the connection is 
            first started
        '''

        print("Listening for server username request...")
        resp = self.server_sock.recv(1024)
        #print(f"Before unpickled: {resp}")
        recieved_packet = unserialize_packet(resp)
        #print(f"After unpickle: {recieved_packet}")
        if "username" not in recieved_packet.contents.lower():
            # This is really an error, the first request from
            # The server should ALWAYS be a username command
            print("did not get username resp")
            self.setup_username()

        # If we get here the server has now requested
        #   for the username from this client
        #   prompt the user and ask for username
        username = input("Input Username:")

        resp_str = f"username {username}"
        serial_packet = gen_serialized_packet(
            PayloadTypes.CLIENT_INFO, resp_str)
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
        start_time = time.time()
        while not done:
            new_time = time.time()
            if (new_time - start_time) > 3:
                done = True
            msg = self.recv_from_server()
            if (msg != None):
                print(f"msg: {msg}")
                done = True

            # Protocol from the server is:
            # | PayloadType | Content

            match msg.split(" ")[0]:
                case PayloadTypes.SERVER_INFO:
                    pass

                case PayloadTypes.SERVER_COMMAND:
                    # if ServerCommands.Username = msg.split(" ")[1]:
                    pass

    def recv_from_server(self):
        data = ''
        done = False
        start_time2 = time.time()
        while not done:
            new_time2 = time.time()
            if (new_time2 - start_time2) > 2:
                done = True
            new_data = ''
            data = new_data
            if data == '':
                done = True
        return data

    def send_raw_command_in(self, raw_inp):
        self.server_sock()


if __name__ == "__main__":
    client_one = socketClient()
    client_one.enter_shell()
