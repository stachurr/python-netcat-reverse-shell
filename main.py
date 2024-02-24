from time       import time, sleep
from signal     import signal, SIGINT
from threading  import Thread, currentThread
from builtins   import print as builtin_print

from socket     import socket, socketpair, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from select     import select
from nclib      import Netcat


# Globals
g_was_signal_caught       = False
g_thread_print_names      = dict()

# Override to prefix user-defined thread name
def print(*args, **kwargs):
    global g_thread_print_names

    id = currentThread().ident
    prefix = g_thread_print_names.get(id)
    if prefix is not None:
        args = (prefix, *args)
    builtin_print(*args, **kwargs)
    return

# Set/clear the calling thread's print name.
def set_thread_print_name(name: str = None):
    global g_thread_print_names

    id = currentThread().ident
    if name is None or len(name) == 0:
        g_thread_print_names.pop(id, None)
    else:
        g_thread_print_names[id] = f'[{name}]'
    return

# Catch interrupts.
def signal_handler(signum, _frame):
    global g_was_signal_caught

    g_was_signal_caught = True
    print('-=-=- Caught signal %d -=-=-' % signum)
    return




def _advanced_interact(client: Netcat):
    command = ''
    while command != 'exit':
        try:
            # get output until dollar sign (bash --posix forces bash-X.X$)
            recv_bytes = client.read_until('$')
            print(recv_bytes.decode('utf-8'), end='') # print string of received bytes

            # get user input command and write command to socket
            command = input(' ')
            client.write(command + '\n')

        except KeyboardInterrupt:
            print('Keyboard Interrupt')
            break
        
        except Exception as e:
            print('Unknown error:', e)
            break
    return

def listener(ip: str, port: int, advanced_interact: bool = False, **nc_kwargs):
    global g_was_signal_caught

    sock: socket        = socket(type=SOCK_STREAM)
    host: tuple         = (ip, port)
    client: Netcat      = None
    is_connected: bool  = False

    # Create TCP server
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.bind(host)
    sock.listen(5)
    print('Listening on %s:%d' % host)

    # Wait for a connection...
    timeout = 1.0
    while True:
        rfds, wfds, efds = select([sock], [], [], timeout)

        # Did we receive an incoming connection request?
        if rfds:
            _client, _addr = sock.accept()
            client = Netcat(sock=_client, server=_addr, **nc_kwargs)
            
            # How should we interact?
            if advanced_interact:
                _advanced_interact(client=client)
            else:
                client.interact()

            print('Disconnected.')
            break

        # Should we stop waiting for requests?
        if g_was_signal_caught:
            print('Canceled before a connection request was received.')
            break

    # Clean up
    if not client.closed:
        client.close()
    sock.close()
    return








if __name__ == '__main__':
    signal(SIGINT, signal_handler)
    set_thread_print_name('Main')
    listener('0.0.0.0', 6969, advanced_interact=False)
    print('Done')
