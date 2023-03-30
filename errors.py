''' 
    Custom Errors for the server and 
    Client to throw
''' 

import re

class ServerError(Exception):
  def __init__(self, error_msg):
    error_msg = re.sub(r"[\n\s]+", ' ', error_msg)
    super().__init__(error_msg)

class CommunicationTypeError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
      error_msg = "CommunicationTypeError"
    super().__init__(error_msg)

class ClientParseError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
      error_msg = "ClientParseError"
    super().__init__(error_msg)

class ClientCommandError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "ClientCommandError"
    super().__init__(error_msg)

class CommandGenerationError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "ClientCommandError"
    super().__init__(error_msg)

class PayloadGenerationError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "PayloadGenerationError"
    super().__init__(error_msg)


class EmptyPacketError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "EmptyPacketError"
    super().__init__(error_msg)


class GroupInstanceKeyError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "EmptyPacketError"
    super().__init__(error_msg)


class PostGenerationError(ServerError):
  def __init__(self, error_msg = None):
    if error_msg == None:
        error_msg = "PostGenerationError"
    super().__init__(error_msg)
