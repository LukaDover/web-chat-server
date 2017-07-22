import signal
import socket
import threading
import time
import sys
from message import MessageHandler
from codes import Code


class Server:
    ID = 0
    lock = threading.Lock()

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = None              # Server has one socket that accepts connections
        self.client_threads = {}        # thread: socket
        self.client_names = ['Public']
        self.conversations = {}         # id: Conversation
        self.context = None

    def exit(self, client_thread):
        self.exit_conversation(client_thread, 'ALL')
        del self.client_threads[client_thread]

    def update(self):
        with Server.lock:
            self.client_names = ['Public'] + [t.name for t in self.client_threads]

    def exit_conversation(self, client_thread, conversation_id):
        with Server.lock:
            if conversation_id == 'ALL':
                Conversation.remove_client_from_all_conversations(client_thread)
            else:
                self.conversations[int(conversation_id)].remove(client_thread)

    def forward_message(self, cid, message):
        self.conversations[cid].notify(0, message)

    def send_users_info(self, client_socket):
        self.update()  # TODO: Place update call when client logs in and logs out
        message = '{}:{}'.format(Code.USERS_INFO, str(self.client_names))
        MessageHandler.send_message(message, client_socket)

    def acknowledge_login(self, client_socket):
        MessageHandler.send_message('{}:OK'.format(Code.ACK_LOGIN), client_socket)

    def create_conversation(self, user_names):
        if 'Public' in user_names:
            user_threads = list(self.client_threads.keys())
        else:
            user_threads = [t for t in self.client_threads if t.name in user_names]
        with Server.lock:
            self.conversations[Conversation.ID - 1] = Conversation(user_threads)

    def setup(self):
        print('Setting up server.')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.address, self.port))
        self.socket.listen(1)
        print("Server socket configured...")

    def spawn_client_thread(self):
        client_sock, client_addr = self.socket.accept()
        print('Spawning new ClientThread, client socket: {}, client address: {}'.format(client_sock, client_addr))
        thread = ClientThread(self, client_sock)
        thread.start()
        return thread

    def start(self):
        print('Starting server...')
        while True:
            try:
                new_client_thread = self.spawn_client_thread()
                with Server.lock:
                    self.client_threads[new_client_thread] = new_client_thread.socket
            except KeyboardInterrupt:
                self.socket.close()  # close Server.socket
                break
        print('Exiting server...')
        sys.exit()


class ClientThread(threading.Thread):

    def __init__(self, server, socket):
        super().__init__(daemon=True)
        self.server = server
        self.socket = socket
        self.name = None
        self.actions = {
                        Code.MESSAGE: self.forward_message,
                        Code.USERS: self.create_conversation,
                        Code.REQUEST_CONVERSATION: self.send_users_info,
                        Code.EXIT_CONVERSATION: self.exit_conversation,
                        Code.EXIT: self.exit,
                        Code.LOGIN: self.receive_user_name
                        }

    def exit(self, redundant):
        self.server.exit(self)
        self.socket.close()

    def exit_conversation(self, cid):
        """Exit conversation with id 'cid'"""
        self.server.exit_conversation(self, cid)

    def receive_user_name(self, name):
        self.name = name
        self.server.acknowledge_login(self.socket)

    def forward_message(self, cid, data):
        """cid = conversation id, data = message"""
        self.server.forward_message(int(cid), '{} {} [{}]'.format(self.stamp(), data, self.time_stamp()))

    def send_users_info(self, *redundant):
        self.server.send_users_info(self.socket)

    def create_conversation(self, users):
        users = eval(users)
        users.append(self.name)
        self.server.create_conversation(users)

    def stamp(self):
        return '[{}] '.format(self.name)

    @staticmethod
    def time_stamp():
        t = time.localtime()
        return '{:02}:{:02}:{:02}'.format(t.tm_hour, t.tm_min, t.tm_sec)

    def run(self):
        while True:
            code, data = MessageHandler.receive_message(self.socket)
            if int(code) not in self.actions:
                print('Unknown code {}'.format(code))
                continue
            if code.startswith('0'):
                self.actions[0](code[1:], data)
                continue
            self.actions[int(code)](data)


class Conversation:
    ID = 0
    _conversations = []

    def __init__(self, clients):
        self.participants = clients
        self.cid = Conversation.ID
        Conversation.ID += 1
        Conversation._conversations.append(self)
        self.notify(Code.CONVERSATION_ID, self.cid)

    def __contains__(self, client_thread):
        return client_thread in self.participants

    def remove(self, client_thread):
        if client_thread in self.participants:
            self.participants.remove(client_thread)
            self.notify(Code.MESSAGE, '------{} has exited conversation------'.format(client_thread.name))

    @staticmethod
    def remove_client_from_all_conversations(client_thread):
        for c in Conversation._conversations:
            c.remove(client_thread)

    def notify(self, code, data):
        """Sends Conversation IDs, forwards messages and exit statuses"""
        message = '{}:{}'.format(code, data)
        MessageHandler.send_message(message, *[t.socket for t in self.participants])


if __name__ == '__main__':
    ip = 'localhost'
    port = 6777
    if input("Use default port and ip address? [y/n]") is 'n':
        ip = input('IP: ')
        port = input('Port: ')

    server = Server(ip, int(port))
    server.setup()
    server.start()
