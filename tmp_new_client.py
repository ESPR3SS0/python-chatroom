'''
    NEED TO USE select.select
'''

from pyautogui import typewrite

from packet import PayloadTypes, Packet, gen_packet, \
    gen_serialized_packet, unserialize_packet

from errors import CommandGenerationError, ClientCommandError

from commands import ClientCommands, ServerCommands, ClientCommandInfo, Command, gen_client_cmd_from_raw

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
        self.timeInput = " >>> "
        self.refresh = False
        self.discontinue = False
        self.port = None
        self.host = None
        self.server_sock = socket.socket()
        self.prompt = " >>> "

        self.connected = False

        self.readables = [self.server_sock, sys.stdin]

    def pre_connect(self):
        '''
            Before the client is connect, the only
            available commands are connect and exit

            some ascii art below 
        '''
        print("                _______  __   __  _______  _______  ______      _______  _______  _______  ___ ")
        print("               |       ||  | |  ||       ||       ||    _ |    |       ||       ||       ||   |      ")
        print("               |  _____||  | |  ||    _  ||    ___||   | ||    |       ||   _   ||   _   ||   |      ")
        print("               | |_____ |  |_|  ||   |_| ||   |___ |   |_||_   |       ||  | |  ||  | |  ||   |      ")
        print("               |_____  ||       ||    ___||    ___||    __  |  |      _||  |_|  ||  |_|  ||   |___   ")
        print("                _____| ||       ||   |    |   |___ |   |  | |  |     |_ |       ||       ||       |  ")
        print("               |_______||_______||___|    |_______||___|  |_|  |_______||_______||_______||_______|  ")
        print("   ")
        print("                _______  __   __  _______  _______    ______    _______  _______  __   __            ")
        print("               |       ||  | |  ||   _   ||       |  |    _ |  |       ||       ||  |_|  |           ")
        print("               |       ||  |_|  ||  |_|  ||_     _|  |   | ||  |   _   ||   _   ||       |           ")
        print("               |       ||       ||       |  |   |    |   |_||_ |  | |  ||  | |  ||       |           ")
        print("               |      _||       ||       |  |   |    |    __  ||  |_|  ||  |_|  ||       |           ")
        print("               |     |_ |   _   ||   _   |  |   |    |   |  | ||       ||       || ||_|| |           ")
        print("               |_______||__| |__||__| |__|  |___|    |___|  |_||_______||_______||_|   |_|           ")
        print("   ")
        print("  _________________________________   ")
        print(" |.--------_--_------------_--__--.|   ")
        print(" ||    /\\ |_)|_)|   /\\ | |(_ |_   ||   ")
        print(" ;;`,_/``\\|__|__|__/``\\|_| _)|__ ,:|   ")
        print("((_(-,-----------.-.----------.-.)`)   ")
        print(" \\__ )        ,'     `.        \\ _/           'Please connect to the server using the IP and port ")
        print(" :  :        |_________|       :  :               at which the server is currently running on.      ")
        print(" |-'|       ,'-.-.--.-.`.      |`-|               By default, this should be localHost, on port")
        print(" |_.|      (( (*  )(*  )))     |._|                 8000. Please use the following format. ")
        print(" |  |       `.-`-'--`-'.'      |  |                  ")
        print(" |-'|        | ,-.-.-. |       |._|                  connect yourIP/localHost portNumber")
        print(" |  |        |(|-|-|-|)|       |  |             for example, the default is connect localHost 8000")
        print(" :,':        |_`-'-'-'_|       ;`.;")
        print("  \\  \\     ,'           `.    /._/               if you have any questions about the commands, ")
        print("   \\/ `._ /_______________\\_,'  /                     please reference the readme.txt file ")
        print("    \\  / :   ___________   : \\,'                      associated with this code. Thanks!'   ")
        print("     `.| |  |           |  |,'                                  - Ryan & Duncan ")
        print("   ")

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
                sys.exit()
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

        # whle not done, run the handle input and listen funciton
        # this is an infinite loop, it does not let you leave until you exit the program

        while not done:

            self.handleInput()

            self.listen_thread()

    # exit function defined for the refresh timer, to save state and discontinue current execution

    def exit_(self):
        self.discontinue = True
        print("\n Refreshing feed... Saving State...")
        keyboard.press_and_release('enter')

    # when handling the inputs from the client
    def handleInput(self):

        self.discontinue = False
        # input time to judge how long the input will stay open before refreshing
        input_time = 20
        # timer, with a conditional for when the timer is done, which is the exit function above
        t = Timer(input_time, self.exit_, )
        # starting timer
        t.start()

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
                inp = input(" >>> ")
                self.timeInput = inp

            # if there is an input, and it reaches here, cancel timer
            t.cancel()

            # if there is dicsontinutation, via timer refresh, and the refresh bool is false
            # with the boolean value of discontinued given by the exit function
            # then set refresh bool to true, and break loop
            if (self.discontinue == True):
                self.refresh = True
                break

            # if no refresh, or no current discontinue, set them back to defaults
            self.discontinue = False
            self.refresh = False
            self.prompt = " >>> "

            # if a refresh has been triggered by the enter key, no other command
            if (inp == ""):
                self.prompt = "\n >> "
                self.discontinue = False
                break

            try:
                command = gen_client_cmd_from_raw(inp)
            except CommandGenerationError as e:
                print(f"\nCommand not available: {inp.split(' ')[0]}")
                break
            except ClientCommandError as e: 
                print(f"\nCommand does not exsist: {inp.split(' ')[0]}")
                break

                # Make sure that the command is an available command
                # if command not in [x.value for x in ClientCommands]:
                #    print(f"Command not available: {command}")
                #    continue
                # Make sure that the client is connect before running
                # any other command
                # elif (command not in ClientCommands.CONNECT.value) and self.connected == False:
                #    print(f"Must be connected to a server before running command: {command}")
                #    continue

            match command.name:
                case ClientCommands.CONNECT.value:
                    if self.connected:
                        print("  Already connected")

                        # sending a message to the main group
                case ClientCommands.POST.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # responds with a list of users in the main group
                case ClientCommands.USERS.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to open a message
                case ClientCommands.MESSAGE.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to see all groups
                case ClientCommands.GROUPS.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to join a group
                case ClientCommands.GROUPJOIN.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to see message in group
                case ClientCommands.GROUPMESSAGE.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to post in group
                case ClientCommands.GROUPPOST.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to see all the users in a group
                case ClientCommands.GROUPUSERS.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to leave a group
                case ClientCommands.GROUPLEAVE.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # command to leave
                case ClientCommands.LEAVE.value:
                    serial_packet = gen_serialized_packet(PayloadTypes.CLIENT_COMMAND, command)
                    self.server_sock.send(serial_packet)

                        # the command to leave the server
                case ClientCommands.EXIT.value:
                        # Quit the program
                    print("Leaving client and server program.... Bye")
                    print("        ~hasta la vista, baby~")
                    print("                     ______ ")
                    print("                   <((((((\\\\\\ ")
                    print("                   /      . }\\ ")
                    print("                   ;--..--._|} ")
                    print("(\\                 '--/\\--'  ) ")
                    print(" \\\\                | '-'  :'|")
                    print("  \\\\               . -==- .-|")
                    print("   \\\\               \\.__.'   \\--._")
                    print("   [\\\\          __.--|       //  _/'--.")
                    print("   \\ \\\\       .'-._ ('-----'/ __/      \\")
                    print("    \\ \\\\     /   __>|      | '--.       |")
                    print("     \\ \\\\   |   \\   |     /    /       /")
                    print("      \\ '\\ /     \\  |     |  _/       /")
                    print("       \\  \\       \\ |     | /        / ")
                    sys.exit()

    def setup_username(self):
        '''
            Invoked immediately when the connection is 
            first started
        '''

        # ################
        # Made is so that the client spams the user with usernames until it does
        # a good name. This way the server doesn't have to keep requesting
        ###############

        #print("Listening for server username request...")
        #resp = self.server_sock.recv(1024)
        ##print(f"Before unpickled: {resp}")
        #recieved_packet = unserialize_packet(resp)
        ##print(f"After unpickle: {recieved_packet}")
        # if "username" not in recieved_packet.contents.lower():
        #    # This is really an error, the first request from
        #    # The server should ALWAYS be a username command
        #    print("\ndid not get username resp")
        #    self.setup_username()

        # If we get here the server has now requested
        #   for the username from this client
        #   prompt the user and ask for username
        username = input("Input Username:")

        serial_packet = gen_serialized_packet(
            PayloadTypes.CLIENT_INFO, f"username {username}")
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
            Thread that listens for 
            messages from the server
            every time its called 

        '''

        # while true, check if the packet is currently readable, check contents, then print them

        while True:
            readable, _, _ = select.select([self.server_sock], [], [], 3)
            if (readable):
                data = self.server_sock.recv(1024)
                new_data_unserial = unserialize_packet(data)
                print(f"\n server msg:   {new_data_unserial.contents}")
            else:
                # if greter than 3 second, stop listening and return
                return

    def send_raw_command_in(self, raw_inp):
        self.server_sock()


if __name__ == "__main__":
    client_one = socketClient()
    client_one.enter_shell()
