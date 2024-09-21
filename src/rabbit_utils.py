from PySide6.QtCore import QObject, Slot, Signal
import pika
from rabbit_host_provider import RabbitHostProvider

class RabbitMQPublisher(QObject):
    published = Signal(str)

    def __init__(self, queue, exchange):
        super().__init__()

        self.queue = queue
        self.exchange = exchange
        self.host = RabbitHostProvider().getHost()
        print(self.host)

    @Slot()
    def start(self):
        try:
            urlParams = pika.URLParameters(self.host)
            self.connection = pika.BlockingConnection(urlParams)
            self.channel = self.connection.channel()
        except:
            print(f'Puslisher could not establish connection with provided host {self.host}')

    @Slot(str)
    def publish(self, message):
        self.channel.queue_declare(queue=self.queue)

        self.channel.basic_publish(exchange=self.exchange,
                              routing_key='',
                              body=message)

        self.published.emit(message)


    def terminate(self):
        self.connection.close()




class RabbitMQConsumer(QObject):
    received = Signal(str)

    def __init__(self, queue):
        super().__init__()

        self.queue = queue
        self.host = RabbitHostProvider().getHost()

    @Slot()
    def start(self):
        try:
            urlParams = pika.URLParameters(self.host)
            self.connection = pika.BlockingConnection(urlParams)
            self.channel = self.connection.channel()

            self.channel.queue_declare(queue=self.queue)

            self.channel.basic_consume(queue=self.queue,
                                       auto_ack=True,
                                       on_message_callback=self.onMessage)

            self.channel.start_consuming()
        except:
            print(f'Consumer could not establish connection with provided host {self.host}')


    @Slot(str)
    def onMessage(self, channel, method, properties, body):
        self.received.emit(body.decode("utf-8"))


