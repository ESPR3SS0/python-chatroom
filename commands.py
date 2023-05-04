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
    POST = "post"
    USERS = "users"
    LEAVE = "leave"
    MESSAGE = "message"
    EXIT = "exit"
    GROUPS = "groups"
    GROUPJOIN = "groupjoin"
    GROUPPOST = "grouppost"
    GROUPUSERS = "groupusers"
    GROUPLEAVE = "groupleave"
    GROUPMESSAGE = "groupmessage"


class ClientCommandInfo(Enum):
    CONNECT = CommandInfo("connect",
                          "usage: connect <host> <port>",
                          [
                              'host',
                              'port'
                          ]
                          )

    POST = CommandInfo("post",
                       "usage: post <subject>; <msg>",
                       ['subject', 'msg']
                       )

    USERS = CommandInfo("users",
                        "usage: users",
                        []
                        )

    LEAVE = CommandInfo("leave",
                        "usage: leave",
                        []
                        )

    MESSAGE = CommandInfo("message",
                          "usage: message <id>",
                          ['msg_id']
                          )

    EXIT = CommandInfo("exit", "usage: exit", [])

    GROUPS = CommandInfo("groups", "usage: groups", [])

    GROUPJOIN = CommandInfo("groupjoin", "usage: groupjoin <group>", ['group'])

    GROUPPOST = CommandInfo("grouppost", "usage: grouppost <group>; <subject>; <msg>", [
                            'group', 'subject', 'msg'])

    GROUPUSERS = CommandInfo(
        "groupusers", "usage: groupusers <group>", ['group'])
    GROUPLEAVE = CommandInfo(
        "groupleave", "usage: groupleave <group>", ['group'])
    GROUPMESSAGE = CommandInfo("groupmessage", "usage: groupmessage <group> <msg_id>",
                               ['group', 'msg_id'])


def check_client_cmd_args(cmd_args: list[str], cmd: CommandInfo) -> None:
    '''
        Check that the number of arguments in a 
        command is the expected number for that command
    '''
    if len(cmd_args) != len(cmd.expected_args):
        raise ClientCommandError
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

    # Raise a command error for non existant names
    if command_name not in [x.value for x in ClientCommands]:
        raise ClientCommandError(f"Cmd {command_name} doesn't exist")

    for cmd in [x.value for x in ClientCommandInfo]:
        # Skip over not matching names
        if cmd.name != command_name:
            continue

        # Pop the command name from the list
        split_inp.remove(command_name)

        if cmd.name in [ClientCommands.POST.value, ClientCommands.GROUPPOST.value]:
            #inp_cmd_args = " ".joingsplit_inp.split(";")
            inp_cmd_args = raw_inp.strip().replace(command_name, "").strip().split(";")
            inp_cmd_args = [x.strip() for x in inp_cmd_args]
        else:
            inp_cmd_args = split_inp

        # Check for the correct number of args
        check_client_cmd_args(inp_cmd_args, cmd)

        # If we get here the expected number of args is
        # present, create the args dictionary
        args = {arg_name: inp_cmd_args[i] for i, arg_name
                in enumerate(cmd.expected_args)}

        # If we get here pack the command and return
        return Command(cmd.name, cmd.info, args)

    # If we get here, the command doesn't exists
    raise CommandGenerationError


def gen_client_cmd(command_name: str, **kwargs) -> Command:
    '''
        Generate a Command object from none raw inp
    '''

    for cmd in [x.value for x in ClientCommandInfo]:
        # Skip over not matching names
        if cmd.name != command_name:
            continue

        # Check for the correct number of args
        check_client_cmd_args(list(kwargs.keys()), cmd)

        # If we get here pack the command and return
        return Command(cmd.name, cmd.info, kwargs)

    # If we get here, the command doesn't exists
    raise CommandGenerationError


if __name__ == "__main__":
    inp = "connect 0.0.0.0 8000"
    cmd = gen_client_cmd_from_raw(inp)
    print(cmd)

    new_cmd = gen_client_cmd("connect", host="0.0.0.0", port="8000")
    print(new_cmd)
#ClientCommandList = [x.value.name for x in ClientCommand]
