import socket
import threading
import sys
import time
from codes import Code
from message import MessageHandler


class Client:
    _event = threading.Event()
    _message_receiver_event = threading.Event()
    options = """
                1. enter conversation
                2. request conversation
                3. exit conversation
                4. switch conversation
                5. exit
                """

    def __init__(self, name, address, port):
        self.name = name
        self.address = address
        self.port = port
        self.socket = None
        self.conversation_ids = []
        self.current_conversation = None
        self.logged_in = False
        self.user_actions = {
            1: self.enter_conversation,
            2: self.request_conversation,
            3: self.exit_conversation,
            4: self.switch_conversation,
            5: self.exit
        }
        self.thread_actions = {
            Code.MESSAGE: self.display_message,
            Code.CONVERSATION_ID: self.save_conversation_id,
            Code.USERS_INFO: self.display_online_users,
            Code.ACK_LOGIN: self.set_login_event
        }
        self.setup_socket()

    def login(self):
        self.send_message(Code.LOGIN, self.name)
        Client._event.wait(5)
        if Client._event.is_set():
            self.logged_in = True
            print('Successfully logged in.')
        else:
            if input('Unable to login. Try again? [y/n]: ') == 'y':
                self.login()
            else:
                sys.exit(1)

    def set_login_event(self, ack):
        if ack == 'OK':
            Client._event.set()

    def setup_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.address, self.port))
        except socket.error as e:
            print('Unable to connect to the server: {}'.format(e))
            if input("Try again? [y/n]") == 'y':
                self.setup_socket()
            else:
                sys.exit(1)

    def display_online_users(self, data):
        print('\n'.join(user for user in eval(data)))

    def display_message(self, data):
        print('{}'.format(data))

    def save_conversation_id(self, cid):
        self.conversation_ids.append(cid)
        print('Conversation with id {} is available.'.format(cid))
        choice = input('Enter conversation {}? [yes/no]: '.format(cid))
        if choice == 'yes':
            self.current_conversation = cid

    def message_receiver(self):
        while True:
            code, data = MessageHandler.receive_message(self.socket)
            Client._message_receiver_event.set()  # Interrupt main loop
            self.thread_actions[int(code[0])](data)
            Client._message_receiver_event.clear()  # Continue with main loop

    def enter_conversation(self):
        if not self.conversation_ids:
            print('You have no active conversations!')
        else:
            self.switch_conversation()

    def request_conversation(self):
        self.send_message(Code.REQUEST_CONVERSATION)
        time.sleep(0.5)
        choice = input('Enter users (use "," delimiter): ')
        if choice:
            choice = [c.strip() for c in choice.split(',')]
            self.send_message(Code.USERS, choice)
        time.sleep(0.5)  # wait for reply

    def exit_conversation(self):
        self.send_message(Code.EXIT_CONVERSATION, self.current_conversation)
        self.conversation_ids.remove(self.current_conversation)
        self.enter_conversation()

    def switch_conversation(self):
        print('Your conversations:\n{}'.format('\n'.join(self.conversation_ids)))
        while True:
            cid = input('Enter Conversation ID: ')
            if cid not in self.conversation_ids:
                continue
            self.current_conversation = cid
            break

    def send_message(self, code, data=None):
        MessageHandler.send_message('{}:{}'.format(code, data), self.socket)

    def exit(self):
        print('Sending exit message to server')
        self.send_message(Code.EXIT)
        time.sleep(1)
        self.socket.close()
        print('Socket closed')
        sys.exit(0)

    def run(self):
        print(Client.options)
        self.login()
        while True:
            if Client._message_receiver_event.is_set():
                continue
            try:
                in_data = input("{} > ".format(self.current_conversation))
                if in_data.isdigit() and len(in_data) == 1:
                    self.user_actions[int(in_data[0])]()
                else:
                    if in_data and self.current_conversation:
                        self.send_message('{}{}'.format(Code.MESSAGE, self.current_conversation), in_data)
            except KeyboardInterrupt:
                self.exit()
                sys.exit()


if __name__ == '__main__':
    ip = 'localhost'
    port = 6777
    if input("Use default port and ip address? [y/n]") is 'n':
        ip = input('IP: ')
        port = input('Port: ')

    user_name = input("Enter your user name: ")
    if not user_name:
        sys.exit(1)

    client = Client(user_name, ip, port)
    thread = threading.Thread(target=client.message_receiver)
    thread.daemon = True
    thread.start()
    client.run()
