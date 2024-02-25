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


# Globals
g_do_quit               = False
g_thread_print_names    = dict()



# Override to prefix user-defined thread name
def print(*args, **kwargs):
    global g_thread_print_names

    id = current_thread().ident
    prefix = g_thread_print_names.get(id)
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



# Advanced Interact let's us Ctrl+C to exit.
# TODO:
#   - Make it more obvious what was typed vs what was received.
#   - Arrow-key history (may not be possible without a key-logger).
#   - Tab completion    (may not be possible without a key-logger).
def _advanced_interact(client: Netcat):
    global g_do_quit

    fds_to_watch = [client.fileno(), stdin]
    while not g_do_quit:
        rfds, _, efds = select(fds_to_watch, [], fds_to_watch, 0.2)

        # Did an exceptional condition occur?
        if efds:
            print('Exceptional condition occured during advanced interaction.')
            break

        # Data is available! From who?
        elif rfds:
            for who in rfds:
                # From STDIN -- send it to client.
                if who == stdin:
                    command = stdin.readline()
                    if command == 'exit\n':
                        return
                    else:
                        client.send(command)

                # From client -- print it to console.
                else:
                    data = b''
                    # Read all available data...
                    while True:
                        recv = client.recv(timeout=0.05)
                        if len(recv) == 0:
                            break
                        elif g_do_quit:     # We don't want the client to be able to spam.
                            return          # It could potentially lock us in this read-loop.
                        else:
                            data += recv
                    # idx = data.rfind(b'\n')
                    # if idx == -1:
                    #     data = b'[evil] ' + data
                    # else:
                    #     idx += 1
                    #     data = data[:idx] + b'[evil] ' + data[idx:]
                    s = data.decode('utf-8').strip()
                    # s = sub('\x1b\[[\\d;]+?m', '', s)
                    # for c in s:
                    #     print(c.encode(), ord(c))
                    # return
                    print(s, end=' ', flush=True)
    return

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
            print('Connected to %s:%d' % addr)
            
            # How should we interact?
            if advanced_interact:
                # _advanced_interact(client=client)
                _name('Advanced Interact', _advanced_interact, client=client)
            else:
                # client.interact()
                _name('Interact', client.interact)

            print(ansi.red('Disconnected.'))
            break

    # Clean up
    if not client.closed:
        client.close()
    tcp_sock.close()
    return




HOST = '0.0.0.0'
PORT = 6969
if __name__ == '__main__':
    signal(SIGINT, _signal_handler)
    set_thread_name('TCP Server')
    tcp_server(HOST, PORT, advanced_interact=True)
    print('Done')
