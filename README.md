Authors: Duncan, Ryan

README
======


Requirements pip install the following 
======================================
- pyautogui
- dataclasses
- socket
- typing
- select
- queue
- keyboard
- threading
- time
- datetime


Compiling Instruction: 
=====================
- Preferably, this program should be ran using vscode on a Windows OS. 
  I am unsure how the program would pan out on other operating systems, 
  as we both used Windows OS to build it. However, it may run fine. 

  Once on windows, open the file in vscode and make sure the prior requirements 
  are installed. When they are installed, use the command prompt or any 
  terminal of your choice to execute the new_server.py and THEN the 
  term_and_msg_listener_client.py. 
  
  *Note: in order to run this successfully, you will need to have the commands.py, 
   errors.py, packet.py, term_and_msg_listener_client.py, and new_server.py ALL in
   the SAME directory/folder.

  You can run the client.py in multiple different terminals in order to get 
  multiple clients in the server. 

  *Note: if you would like to change the servers IP adress of port number to 
   somthing other than the default, it is located at the very bottom of the 
   new_server.py file on line 862. 



Commands/Requests
=================

1. connect
    - usage:
        >> connect <ip> <port>
    - example: 
        >>> connect localHost 8000
    
    - purpose: this command allows the client to connect to the server, using the associated IP Adress/Host
      and the port number that it is running on. This is called upon right when the client enters the client program. 

2. username (not a command) but still important. 
    - example: 
        Input Username: Johnny

    - this is not a command, but the initial request from the server as soon as you enter it. This is how the server will reference
     you to other people in the server. There cannot be duplicates. 

3. post
    - usage:
        >>> post <msg_subject> ; <msg_body>
    
    -example: 
        >>> post cookies ; I like cookies

    - purpose: 
        Posts a message to all the groups that the current 
        user is apart of 

4. users
    - usage: 
        >>> user
        
    - example: 
        >>> users       #returns a list of users in the server 

    - purpose: 
        Returns a list of all the users in all the groups that 
        the current user is apart of 

5. leave
    - usage:
        >>> leave
        
    - example: 
        >>> leave

    - purpose: 
        To leave the server. 

6. message
    - usage:
        >>> message <msg_id>
        
    - example: 
        >>> message 10

    - purpose: 
        View the body of the message with the corresponding msg_id. 
        This will query msgs from all the groups that the current 
        users is apart of. 
    
. exit
    - usage:
        >>> exit 
    - example: 
        >>> exit

    - purpose: 
        To exit the client & server program 

8. groups
    - usage:
        >>> groups 
    - example: 
        >>> groups

    - purpose: 
        The purpose of this command is to output a list of all the group names

9. groupjoin
    - usage:
        >>> groupjoin <group_name>
    - example: 
        >>> groupjoin Group1

    - purpose: 
        The purpose of group join is to join a group with other clients,
        which is seperate from those who are not in the group. 

10. grouppost
    - usage:
        >>> grouppost <group_name> ; <msg_subject> ; <msg_body>
    - example: 
        >>> grouppost Group1; Subject; message    # grouppost GroupID; Subject; Message - the subject is what the message 
                                                    is identified by, and the message is the actual contents of the message

    - purpose:  
        The purpose is to send a message into a single group, that will then be sent to others in that same group who 
        will view that message using groupmessage command. 

11. groupusers
    - usage:
        >>> groupusers <group_name>
    - example: 
        >>> groupusers Group1
    
    - purpose: 
        The purpose of this command is to list all the members in a specific group. 

12. groupleave
    - usage:
        >>> groupleave <group_name>
    - example: 
        >>> groupleave Group1
    
    - purpose: 
        To leave a certain group. 

13. groupmessage
    - usage:
        >>> groupmessage <group_name> <msg_id>
    - example: 
        >>> groupmessage Group1; subject

    - purpose: 
        The purpose is to read a message that was sent to the group that you are in, which is identified by the 
        subject. 


MAJOR ISSUES:
=============
** Major issues during designing **

- Originally the server implementation was one thread per connect, however this cause 
    many issues with shared memory, especially for task2 where many threads were 
    access similar memory. This result in us choosing to use a synchoronous design 
    pattern using the select.select() function, switching between readable and 
    writable sockets, and using a Queue for sending out packets. This required 
    no shared memory, and produced a server that matched the functionaly of a server 
    based on threading (atleast for task1)

- Handling the variety of errors that can occur during a socket connection, of which
    changes with the context of the socket, whether its being read or being written 
    too, or whether it's queued to be read or written too. In the majority of cases 
    the error forces a socket connection close, however if this occured during serial
    transfer, and the serial payload that was recieved was malformed this produced 
    an annoyingly wierd error, specifically when trying to decode the malformed packet.
    Thus, inorder to handle this, the error was caught, and the client connection 
    socket was completely wiped from all the group rooms, and wiped from the server

- Had a design decision to make regarding the commands, and how the commands 'join' 
    'post' and 'users' would work for a client that is in multiple groups. Decided 
    to treat theses commands as broadcast commands, where a post would post to every 
    group that the user is currently apart of. This required some extra logic and 
    convient design decisions on the SingleGroupServer to make doing so easy.


- When dealing with refresing the clients screen we originally decided to go with 
multithreading. However, it soon became clear that two threads could not both listen 
and write at the same time. Therefore we had to implement an algorithm that would work 
as a non blocking receive. To do so, we used a timer, which timed the users input for a
period of time (30 seconds), and then would switch to the listen thread (for about 2 seconds).
However, a major problem occured with the state being changed (what if the user was in the middle
of writing somthing when the threads switched? would their command be saved?). Thats why we also 
incorperated the typewriting() feature, with some conditional boolean values associated with weather 
or not the state should be saved upon returning, and if it was, it would be maluable as well. Given 
that raw_input is no longer avaliable on python 3, and the prompt given with input("prompt") is immutable
during execution, we had to look outwards to other options, like typewriting form the pyautogui install. 
Overall, this allowed the server to send messages to the server every so often if the client is not 
being active. We also had designed it so that the feed from the server would refresh every time 
the 'enter' key is pressed. 
