import struct


class MessageHandler:

    @staticmethod
    def receive_fixed_length_msg(socket, msglen):
        message = b''  # byte format
        while len(message) < msglen:
            try:
                chunk = socket.recv(msglen - len(message))  # preberi nekaj bajtov
                if chunk == b'':  # Check if there is anything to receive
                    raise RuntimeError("Socket connection broken")
                message += chunk  # pripni prebrane bajte sporocilu
            except Exception:  # TODO: Isn't there a better way to do this?
                pass
        return message

    @staticmethod
    def receive_message(socket):
        header = MessageHandler.receive_fixed_length_msg(socket, 2)
        message_length = struct.unpack("!H", header)[0]
        message = None
        if message_length > 0:
            message = MessageHandler.receive_fixed_length_msg(socket, message_length)
            message = message.decode('utf-8')
        return message.split(':', maxsplit=1)

    @staticmethod
    def make_message(message):
        encoded_message = message.encode('utf-8')
        header = struct.pack('!H', len(encoded_message))
        return header + encoded_message

    @staticmethod
    def send_message(msg, *socket_list):
        msg = MessageHandler.make_message(msg)
        for socket in socket_list:
            socket.sendall(msg)


