# This Python file uses the following encoding: utf-8

from PySide6.QtCore import QObject, Slot, Signal
import pika

class RabbitMQPublisher(QObject):
    published = Signal(str)

    def __init__(self, stationName):
        super().__init__()

        self.queue = f'frequency{stationName}'
        self.exchange = f'frequency{stationName}'

    @Slot()
    def start(self):
        urlParams = pika.URLParameters('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria')
        self.connection = pika.BlockingConnection(urlParams)
        self.channel = self.connection.channel()

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

    def __init__(self, stationName):
        super().__init__()

        self.queue = f'RSSI{stationName}'


    @Slot()
    def start(self):
        urlParams = pika.URLParameters('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria')
        self.connection = pika.BlockingConnection(urlParams)
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=self.queue)

        self.channel.basic_consume(queue=self.queue,
                              auto_ack=True,
                              on_message_callback=self.onMessage)

        self.channel.start_consuming()


    @Slot(str)
    def onMessage(self, channel, method, properties, body):
        self.received.emit(body)


