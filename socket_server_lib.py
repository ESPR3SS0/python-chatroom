from enum import Enum

class ClientCommands(Enum):
    # List of acceptable commands from the client
    # Part 1 commands (The public group commands)
    CONNECT = "connect"
    JOIN = "join"
    POST = "post"
    USERS = "users"
    LEAVE = "leave"
    MESSAGE = "message"
    EXIT = "exit"
    # Part 2 commands:
    GROUPS = "groups"
    GROUPJOIN = "groupjoin"
        #  CAN ONLY USE THE FOLLOW IF THE USER IS 
        #  IN THE GROUP
    GROUPPOST = "grouppost"
    GROUPUSERS = "groupusers"
    GROUPLEAVE = "groupleave"
    GROUPMESSAGE = "groupmessage"


class ServerCommands(Enum):
    EXIT = "exit"
    USERNAME = "username"


class PayloadTypes(Enum):
    '''
        Enum for payload type
    '''
    SERVER_INFO = "server_info"         # 
    SERVER_COMMAND = "server_command"
    CLIENT_INFO = "client_info"
    CLIENT_COMMAND = "client_command"


def try_sock_send(data_to_send, conn, num_attempts: int = 0):
    '''
        Function to attempt to send a message
        over a socket
    '''
    for attempt in num_attempts:
        try:
            connection.send(data_to_send)
        except Exception as e:
            raise e

def try_sock_recv(buffer_size: int, conn):
    '''
        Function to attempt to recieve a message
        over a socket
    '''
    data = "".encode()
    done = False
    print("SOCK RECV: pre loop")
    while not done:
        new_data = conn.recv(buffer_size)
        print(f"SOCK RECV: pre in loop: {new_data.decode()}")
        print(f"Length of data: {len(new_data)}")

        data+=new_data
        # Had an issue with telling when a socket was 
        # done recieving, this is a bit of a hack
        if (len(new_data) < buffer_size): #and '\n' in new_data.decode():
            #if not new_data:
            done = True

    return data


