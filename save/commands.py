from dataclasses import dataclass

from enum import Enum

from errors import ClientCommandError, CommandGenerationError

class Status(Enum):
    OK = "OK"
    ERROR = "ERROR"
    NOT_FOUND = "not_found"

class ServerCommands(Enum):
    '''
        Used when the server needs information 
        from a client, or when a server sends the 
        client something to be displayed
    '''
    SEND_USERNAME = "send_username"
    EXIT = "exit"

@dataclass
class Command:
    name: str
    info: str
    args: dict


@dataclass 
class CommandInfo:
    name: str
    info: str
    expected_args: list


class ClientCommands(Enum):
    CONNECT = "connect"
    JOIN = "join"
    POST = "post"
    USERS = "users"
    LEAVE = "leave"
    MESSAGE = "message"
    EXIT = "exit"
    GROUPS = "groups"
    GROUPJOIN = "groupjoin"
    GROUPPOST  = "grouppost"
    GROUPUSERS = "groupusers"
    GROUPLEAVE  = "groupleave"
    GROUPMESSAGE = "groupmessage"


class ClientCommandInfo(Enum):
    CONNECT = CommandInfo("connect",
                "usage: connect <host> <port>",
                [
                    'host' ,
                    'port'
                    ]
            )

    JOIN = CommandInfo("join",
            "usage: join",
            []
            )

    POST = CommandInfo("post",
            "usage: post <msg>",
            ['msg']
            )

    USERS = CommandInfo("users",
            "usage: users",
            []
            )

    LEAVE = CommandInfo("leave",
            "usge: leave",
            []
            )
    
    MESSAGE = CommandInfo("message",
            "usage: message <id>",
            ['msg_id']
            )

    EXIT = CommandInfo("exit", "usage: exit", {})

    GROUPS = CommandInfo("groups", "usage: groups", {})

    GROUPJOIN = CommandInfo("groupjoin", "usage: groupjoin <group_name>", ['group'])

    GROUPPOST = CommandInfo("grouppost", "usage: grouppost <msg>", ['msg'])

    GROUPUSERS   = CommandInfo("groupusers", "usage: groupusers <group_name>",['group'])
    GROUPLEAVE   = CommandInfo("groupleave", "usage: groupleave <group_name>",['group'])
    GROUPMESSAGE = CommandInfo("groupmessage", "usage: groupmessage <group_name> <msg_id>",
            ['group', 'msg_id'])

def check_client_cmd_args(cmd_args: list[str], cmd: CommandInfo)->None:
    '''
        Check that the number of arguments in a 
        command is the expected number for that command
    '''
    if len(cmd_args) != len(cmd.expected_args): raise ClientCommandError
    return

def gen_client_cmd_from_raw(raw_inp: str) -> Command:
    '''
        Generate a command object from a raw 
        input line (usually the raw input from a 
        user)
    '''

    # The the input into a list for processing
    split_inp = raw_inp.strip().split(" ")

    # The first word in the list is the command
    command_name = split_inp[0]
    
    for cmd in [x.value for  x in ClientCommandInfo]:
        # Skip over not matching names
        if cmd.name != command_name:
            continue

        # Pop the command name from the list
        split_inp.remove(command_name)
        inp_cmd_args = split_inp

        # Check for the correct number of args
        check_client_cmd_args(inp_cmd_args, cmd)

        # If we get here the expected number of args is 
        # present, create the args dictionary
        args = {arg_name : inp_cmd_args[i] for i, arg_name 
                in enumerate(cmd.expected_args)}

        #If we get here pack the command and return
        return Command(cmd.name, cmd.info, args)


    # If we get here, the command doesn't exists
    raise CommandGenerationError

def gen_client_cmd(command_name: str, **kwargs) -> Command:
    '''
        Generate a Command object from none raw inp
    '''

    for cmd in [x.value for  x in ClientCommandInfo]:
        # Skip over not matching names
        if cmd.name != command_name:
            continue

        # Check for the correct number of args
        check_cmd_args(kwargs.keys(), cmd)

        #If we get here pack the command and return
        return Command(cmd.name, cmd.info, kwargs)

    # If we get here, the command doesn't exists
    raise CommandGenerationError

if __name__ == "__main__": 
    inp = "connect 0.0.0.0 8000"
    cmd = gen_cmd_from_raw(inp)
    print(cmd)

    new_cmd = gen_cmd("connect", host="0.0.0.0", port="8000")
    print(new_cmd)
#ClientCommandList = [x.value.name for x in ClientCommand]
