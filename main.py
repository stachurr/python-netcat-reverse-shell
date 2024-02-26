from time       import time, sleep
from signal     import signal, SIGINT
from builtins   import print as builtin_print

from socket     import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from select     import select
from nclib      import Netcat
from sys        import version_info, stdin
from re         import sub
import ansi

if version_info.major >= 3:
    if version_info.major == 3 and version_info.minor < 10:
        _use_new_cur_thread = False
    else:
        _use_new_cur_thread = True
if _use_new_cur_thread:
    from threading import Thread, current_thread
    current_thread = current_thread
else:
    from threading import Thread, currentThread
    current_thread = currentThread

# from named_functions import Name
from tty        import setcbreak, setraw
from termios    import tcgetattr, tcsetattr, TCSANOW, TCSAFLUSH, TCSADRAIN

farb = int(0xff).to_bytes(length=1, byteorder='big', signed=False)

# Globals
g_do_quit               = False
g_thread_print_names    = dict()



# Override to prefix user-defined thread name
def print(*args, no_name = False, **kwargs):
    global g_thread_print_names

    if not no_name:
        id = current_thread().ident
        prefix = g_thread_print_names.get(id, None)
        if prefix is not None:
            args = (prefix, *args)

    builtin_print(*args, **kwargs)
    return

# Set/clear the calling thread's print name.
def set_thread_name(name: str = None, prefix: str = '[', suffix: str = ']'):
    global g_thread_print_names

    id = current_thread().ident
    if name is None or name == '':
        g_thread_print_names.pop(id, None)
    else:
        g_thread_print_names[id] = prefix + name + suffix
    return

# Catch interrupts.
def _signal_handler(signum, _frame):
    global g_do_quit

    g_do_quit = True
    print('-=-=- Caught signal %d -=-=-' % signum)

    return

# Cheeky use of `g_thread_print_names` to give a function a name.
def _name(name: str, func, *args, **kwargs):
    global g_thread_print_names

    prev_name = g_thread_print_names.get(current_thread().ident, None)[1:-1]
    set_thread_name(name)
    ret = func(*args, **kwargs)
    set_thread_name(prev_name)

    return ret


def cursor_save_pos():
    builtin_print('\x1b[s', end='', flush=True)

def cursor_load_pos():
    builtin_print('\x1b[u', end='', flush=True)

def cursor_left(n: int = 1):
    n = min(255, max(0, n))
    builtin_print('\x1b[%dD' % n, end='', flush=True)




# Advanced Interact let's us Ctrl+C to exit among other things:
# TODO:
#   - Make it more obvious what was typed vs what was received.
#   - Arrow-key history (may not be possible without a key-logger or etc.)
#   - Tab completion    (may not be possible without a key-logger or etc.)
DO_TERMIOS = True
def _stdin_monitor(newline_callback):
    global g_do_quit

    set_thread_name('STDIN Monitor')
    print('Hello, World!')

    user_stdin = ''
    history = []

    while not g_do_quit:
        _in = stdin.read(1) # TODO: How does one avoid a blocking call here?
        print(_in.encode('utf-8'))
        
        # Ctrl-c
        if _in.encode('utf-8') == b'\x03':
            g_do_quit = True
        # Newline
        elif _in == '\n' or _in == '\r':
            history.append(user_stdin)
            # builtin_print()

            do_continue = newline_callback(user_stdin)
            if not do_continue:
                break
            
            user_stdin = ''
        # Backspace
        elif _in == '\x7f':
            user_stdin = user_stdin[:-1]
            # cursor_left()
            # builtin_print(' ', end='', flush=True)
            # cursor_left()
        # Other
        else:
            user_stdin += _in
            # builtin_print(user_stdin[-1], end='', flush=True)
    
    print('Terminating...')
    return

def __advanced_interact(client: Netcat):
    global g_do_quit

    response_lpad = '    '
    prompt_prefix = '(%s:%d) ' % client.peer
    fds_to_watch  = [client.fileno(), stdin]
    if DO_TERMIOS:
        fds_to_watch = [client.fileno()]

    client_prompt_suffix = b''
    command_history      = []
    is_first_recv        = True

    # t = Thread(target=_stdin_monitor) # DO_TERMIOS
    # t.start() # DO_TERMIOS
    # t.join() # DO_TERMIOS
    # return # DO_TERMIOS
    ### WARNING
    ### Need to modify this loop to not return without joining thread!!!!!!!!!
    
    while not g_do_quit:
        # _in = stdin.read(1)
        # # print(f'{_in = }')
        # continue
        
        # Wait for any fd to become available for reading.
        rfds, _, efds = select(fds_to_watch, [], fds_to_watch, 0.2)

        # Did an "exceptional condition" occur?
        if efds:
            print('Exceptional condition occured during advanced interaction.')
            break

        # Data is available! From who?
        elif rfds:
            for who in rfds:
                # From STDIN -- send it to client.
                if who == stdin:
                    command = stdin.readline().strip()
                    if command == 'exit':
                        return
                    
                    client.send_line(command)
                    command_history.append(command)

                # From client -- print it to console.
                else:
                    # Read all available data...
                    data_bytes = b''
                    while True:
                        # Greedy timeout since we know `client_prompt_suffix`.
                        # Note: This may leave unread trailing whitespace in the buffer.
                        if not is_first_recv:
                            recv = client.recv(timeout=0.05)
                            if g_do_quit:           # We don't want the client to be able to spam.
                                return              # It could potentially lock us in this read-loop.
                            elif len(recv) > 0:
                                data_bytes += recv

                                # Did we get the full response yet?
                                if recv.endswith(client_prompt_suffix):
                                    break

                        # Generous timeout. We want to make sure we get the full response on
                        # the first time we communicate because we use the client prompt to
                        # parse all future responses.
                        else:
                            recv = client.recv(timeout=0.25)
                            if g_do_quit:           # We don't want the client to be able to spam.
                                return              # It could potentially lock us in this read-loop.
                            elif len(recv) == 0:
                                break
                            
                            data_bytes += recv

                    # Convert bytes to list of lines as strings.
                    data_str_raw = data_bytes.decode('utf-8')
                    data_str     = data_str_raw.strip()
                    lines        = data_str.split('\n')

                    # # Remove ANSI sequences.
                    # s = sub('\x1b\[[\\d;]+?m', '', s)
                    # for c in s:
                    #     print(c.encode(), ord(c))
                    # return

                    # If the last command entered is prefixed in the
                    # clients response, remove it before printing.
                    if not DO_TERMIOS:
                        if not is_first_recv:
                            if lines[0] == command_history[-1]:
                                lines = lines[1:]
                    
                    # Upon initial connection, determine the suffix of the clients prompt.
                    # This is used for the remaining duration of the connection to parse
                    # responses from the client.
                    else:
                        last_visible_char = data_str[-1]
                        idx = data_str_raw.rfind(last_visible_char)
                        if idx == -1:
                            raise 'Failed to parse client prompt for suffix!'
                        client_prompt_suffix = data_str_raw[idx:].encode('utf-8')

                    # Save the client prompt and remove it from list of lines.
                    client_prompt = lines.pop(-1)
                    
                    # Format client response then print.
                    s = '\x1b[93m%s%s\x1b[0m\n%s%s' % (response_lpad, f'\n{response_lpad}'.join(lines), prompt_prefix, client_prompt)
                    print(s, no_name=True, end=' ', flush=True)

                    # if DO_TERMIOS:
                    #     cursor_save_pos()

        is_first_recv = False          
    return

def _advanced_interact(client: Netcat):
    prev_termios_config = None
    t = None

    if DO_TERMIOS:
        def ___newline_callback(line: str) -> bool:
            client.send_line(line)
            return line != 'exit'
        prev_termios_config = tcgetattr(stdin)
        # setcbreak(stdin, TCSADRAIN)
        setraw(stdin, TCSADRAIN)
        t = Thread(target=_stdin_monitor, args=(___newline_callback,))
        t.start()
    
    try:
        __advanced_interact(client=client)
    except Exception as e:
        print('Exception in __advanced_interact:', e)

    if DO_TERMIOS:
        t.join()
        tcsetattr(stdin, TCSADRAIN, prev_termios_config)

# Starts a TCP server and listens for a single connection.
# @Name('[TCP Server]')
def tcp_server(ip: str, port: int, advanced_interact: bool = False, **nc_kwargs):
    global g_do_quit, g_thread_print_names

    # Remove Netcat constuctor arguments which are used by us.
    if nc_kwargs.pop('sock', None) is not None:
        print('Keyword argument "sock" will be ignored.')
    elif nc_kwargs.pop('server', None) is not None:
        print('Keyword argument "server" will be ignored.')

    # Create TCP server.
    where    = (ip, port)
    backlog  = 0    # The number of unaccepted connections to allow
                    # before refusing new connections.
    tcp_sock = socket(family=AF_INET, type=SOCK_STREAM)
    tcp_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcp_sock.bind(where)
    tcp_sock.listen(backlog)
    print('Listening on %s:%d' % where)

    # Wait for a connection...
    while True:
        # Wait for any event. Using a timeout gives us execution time periodically.
        timeout = 0.2
        rfds, _, efds = select([tcp_sock], [], [tcp_sock], timeout)
    
        # 1) Should we stop waiting for requests?
        if g_do_quit:
            print('Signal caught -- no longer accepting connections.')
            break

        # 2) Did an exceptional condition occur?
        elif efds:
            print('Exceptional condition on TCP socket. Potentially out-of-band data.')
            break

        # 3) Did we receive an incoming connection request?
        elif rfds:
            client, addr = tcp_sock.accept()
            client = Netcat(sock=client, server=addr, **nc_kwargs)
            addr_str = '%s:%d' % addr
            print('Connected to', addr_str)
            
            # How should we interact?
            if advanced_interact:
                # _advanced_interact(client=client)
                _name(addr_str, _advanced_interact, client=client)
            else:
                # client.interact()
                _name('Interact', client.interact)

            # Close connection.
            if not client.closed:
                client.close()

            print(ansi.red('Disconnected.'))
            break

    # Close TCP server.
    tcp_sock.close()
    return




HOST = '0.0.0.0'
PORT = 6969
if __name__ == '__main__':
    signal(SIGINT, _signal_handler)
    set_thread_name('TCP Server')
    tcp_server(HOST, PORT, advanced_interact=True)
    print('Done')
