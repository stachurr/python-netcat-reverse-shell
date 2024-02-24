from time       import time, sleep
from signal     import signal, SIGINT
from threading  import Thread, currentThread
from builtins   import print as builtin_print

# Globals
g_server                  = None
g_client                  = None
g_connection_established  = False
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

# Set/clear the calling thread's print name.
def set_thread_print_name(name: str = None):
    global g_thread_print_names

    id = currentThread().ident

    if name is None or len(name) == 0:
        g_thread_print_names.pop(id, None)
    else:
        g_thread_print_names[id] = f'[{name}]'

# Catch interrupts.
def signal_handler(signum, _frame):
    global g_server, g_was_signal_caught

    g_was_signal_caught = True
    print('-=-=- Caught signal %d -=-=-' % signum)
    return




from nclib import TCPServer

def close_server():
    global g_server

    if g_server is not None:
        if not g_server.closed:
            g_server.sock.close()
            g_server.close()

def on_accept_callback(did_succeed: bool):
    global g_client, g_connection_established

    g_connection_established = did_succeed
    if did_succeed:
        print('Connected to %s:%d' % g_client.peer)

def _async_accept(ip: str, port: int, callback):
    global g_server, g_client, g_connection_established

    set_thread_print_name('TCP Server')

    host = (ip, port)
    g_server = TCPServer(host)
    print('Listening on %s:%d' % host)

    # Wait for a single connection.
    status = False
    try:
        for _client in g_server:
            g_client = _client
            break
        status = True
    except Exception as e:
        print('ERROR:', e)
    
    # Hit callback.
    callback(status)
    return

def _advanced_interact():
    global g_client, g_server

    command = ''
    while command != 'exit':
        # Exit the loop if the server was closed.
        if g_server is None or g_server.closed:
            print('Server closed unexpectedly.')
            break

        try:
            # get output until dollar sign (bash --posix forces bash-X.X$)
            recv_bytes = g_client.read_until('$')
            print(recv_bytes.decode('utf-8'), end='') # print string of received bytes

            # get user input command and write command to socket
            command = input(' ')
            g_client.write(command + '\n')

        except KeyboardInterrupt:
            print('Keyboard Interrupt')
            break
        
        except Exception as e:
            print('Unknown error:', e)
            break

def listener(ip: str, port: int, advanced_interact: bool = False):
    global g_client, g_connection_established, g_was_signal_caught

    # Start TCP server on a new thread.
    t = Thread(target=_async_accept, args=(ip, port, on_accept_callback))
    t.start()
    
    # Busy wait for a connection or ctrl+c interrupt.
    while not g_connection_established and not g_was_signal_caught:
        sleep(0.2)

    # Are we connected?
    if g_connection_established:
        if advanced_interact:
            _advanced_interact()
        else:
            g_client.interact()
        print('Disconnected.')
    else:
        print('Canceled before a connection request was received.')

    # Make sure server is dead so we can wrangle it's corpse.
    close_server()
    t.join()
    return




from socket import socket, socketpair, SOL_TCP, TCP_INFO, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from select import select
from struct import unpack
from nclib  import simplesock

def getTCPInfo(s):
    '''struct tcp_info
    {
        u_int8_t	tcpi_state;
        u_int8_t	tcpi_ca_state;
        u_int8_t	tcpi_retransmits;
        u_int8_t	tcpi_probes;
        u_int8_t	tcpi_backoff;
        u_int8_t	tcpi_options;
        u_int8_t	tcpi_snd_wscale : 4, tcpi_rcv_wscale : 4;

        u_int32_t	tcpi_rto;
        u_int32_t	tcpi_ato;
        u_int32_t	tcpi_snd_mss;
        u_int32_t	tcpi_rcv_mss;

        u_int32_t	tcpi_unacked;
        u_int32_t	tcpi_sacked;
        u_int32_t	tcpi_lost;
        u_int32_t	tcpi_retrans;
        u_int32_t	tcpi_fackets;

        /* Times */
        u_int32_t	tcpi_last_data_sent;
        u_int32_t	tcpi_last_ack_sent;
        u_int32_t	tcpi_last_data_recv;
        u_int32_t	tcpi_last_ack_recv;

        /* Metrics */
        u_int32_t	tcpi_pmtu;
        u_int32_t	tcpi_rcv_ssthresh;
        u_int32_t	tcpi_rtt;
        u_int32_t	tcpi_rttvar;
        u_int32_t	tcpi_snd_ssthresh;
        u_int32_t	tcpi_snd_cwnd;
        u_int32_t	tcpi_advmss;
        u_int32_t	tcpi_reordering;
    };'''

    x = unpack('B'*7+'I'*21, s.getsockopt(SOL_TCP, TCP_INFO, 1*7+4*21))
    print(x)

def netcat(hostname, port, content):
    host = (hostname, port)

    print('Creating socket')
    sock = socket(type=SOCK_STREAM)
    print('Setting options')
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    print('Binding')
    sock.bind(host)
    print('Listening')
    sock.listen()

    print('r/w pair')
    _rsock, _wsock = socketpair()
    print('select')
    rl, _, _ = select([sock, _rsock], [], [])
    if _rsock in rl:
        print('closing r/w')
        _rsock.close()
        _wsock.close()

    print('Waiting for connection...')
    client, addr = sock.accept()
    # yield Netcat(sock=client, server=addr)
    print('Connected to %s:%d' % addr)
    
    # print('  - blocking =', client.getblocking())
    # print('  - timeout  =', client.gettimeout())

    print('Setting blocking to False')
    client.setblocking(False)
    # print('  - blocking =', client.getblocking())
    # print('  - timeout  =', client.gettimeout())

    # client.sendall(b'ls -l')

    client = simplesock.wrap(client)
    timeout = None

    data = b''
    while not g_was_signal_caught:
        print('signal still not caught')
        deadline = None
        if timeout is not None:
            deadline = time() + timeout

        try:
            first_shot = True
            while True:
                print('still looping')
                if deadline is not None:
                    timeout = deadline - time()
                    if timeout < 0:
                        if first_shot:
                            timeout = 0
                        else:
                            raise 'TIMED OUT'
                first_shot = False

                if timeout is not None:
                    print('waiting for timeout')
                    r, _, _ = select([client], timeout=timeout)
                    if not r:
                        raise 'TIMED OUT (select)'
                
                try:
                    recv = client.recv(1)
                except ConnectionResetError:
                    recv = b''
                
                if not recv:
                    break

                data += recv

        except Exception as e:
            print('Exception:', e)
            break
            
    print('data =', data)
    client.close()
    sock.close()





if __name__ == '__main__':
    signal(SIGINT, signal_handler)
    set_thread_print_name('Main')

    print('-=-=- Start -=-=-')
    
    set_thread_print_name()
    listener('0.0.0.0', 6969, advanced_interact=True)
    # netcat('0.0.0.0', 6969, None)
    set_thread_print_name('Main')
    
    print('-=-=- Done -=-=-')
