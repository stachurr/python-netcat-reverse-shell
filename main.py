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

    was_connection_established = False

    host = (ip, port)
    sock = socket(type=SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.bind(host)
    sock.listen(5)
    _oob_rsock, _oob_wsock = socketpair()
    print('Listening on %s:%d' % host)
    while True:
        rl, _, _ = select([sock, _oob_rsock], [], [], 1.0)
        if _oob_rsock in rl:
            print('Something went wrong')
            _oob_rsock.close()
            _oob_wsock.close()
            break
        elif rl:
            _client, _addr = sock.accept()
            client = Netcat(sock=_client, server=_addr, **nc_kwargs)
            was_connection_established = True
            break
        elif g_was_signal_caught:
            break
        else:
            print('not yet')

    if g_was_signal_caught:
        print('Canceled before a connection request was received.')
    elif was_connection_established:
        if advanced_interact:
            _advanced_interact()
        else:
            client.interact()
        print('Disconnected.')

    if not client.closed:
        client.close()
    sock.close()
    return








if __name__ == '__main__':
    signal(SIGINT, signal_handler)
    set_thread_print_name('Main')

    print('-=-=- Start -=-=-')
    
    set_thread_print_name()
    listener('0.0.0.0', 6969, advanced_interact=True)
    # netcat('0.0.0.0', 6969, None)
    set_thread_print_name('Main')
    
    print('-=-=- Done -=-=-')
