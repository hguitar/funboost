# -*- coding: utf-8 -*-
# @Author  : ydf
# @Time    : 2021-04-15 0008 12:12
import json
import nb_log



from kombu import Connection, Exchange, Queue, Consumer, Producer
from kombu.transport.virtual.base import Channel
import kombu
from nb_log import LogManager

from function_scheduling_distributed_framework.publishers.base_publisher import AbstractPublisher, deco_mq_conn_error
from function_scheduling_distributed_framework import frame_config

nb_log.get_logger(name=None,log_level_int=10)
"""
https://www.cnblogs.com/shenh/p/10497244.html

rabbitmq  交换机知识。

https://docs.celeryproject.org/projects/kombu/en/stable/introduction.html
kombu 教程
"""

class MyBase64():
    def encode(self, s):
        # return bytes_to_str(base64.b64encode(str_to_bytes(s)))
        return s

    def decode(self, s):
        # return base64.b64decode(str_to_bytes(s))
        return s

Channel.codecs['base64'] = MyBase64()   # 打猴子补丁，不使用base64更分方便查看内容


class KombuPublisher(AbstractPublisher, ):
    """
    使用redis作为中间件,这种是最简单的使用redis的方式，此方式不靠谱很容易丢失大量消息。非要用reids作为中间件，请用其他类型的redis consumer
    """

    def custom_init(self):
        logger_name = f'{self._logger_prefix}{self.__class__.__name__}--{self._queue_name}--{frame_config.KOMBU_URL.split(":")[0]}'
        self.logger = LogManager(logger_name).get_logger_and_add_handlers(self._log_level_int,
                                                                          log_filename=f'{logger_name}.log' if self._is_add_file_handler else None,
                                                                          formatter_template=frame_config.NB_LOG_FORMATER_INDEX_FOR_CONSUMER_AND_PUBLISHER,
                                                                          )  #

        self.logger.warning('替换了 kombu 的 base64')


    def init_broker(self):
        self.exchange = Exchange('distributed_framework_exchange', 'direct', durable=True)
        self.queue = Queue(self._queue_name, exchange=self.exchange, routing_key=self._queue_name)
        self.conn = Connection(frame_config.KOMBU_URL)
        self.queue(self.conn).declare()
        self.producer = self.conn.Producer(serializer='json')
        self.channel = self.producer.channel # type: Channel
        # self.channel = self.conn.channel()  # type: Channel
        # # self.channel.exchange_declare(exchange='distributed_framework_exchange', durable=True, type='direct')
        # self.queue = self.channel.queue_declare(queue=self._queue_name, durable=True)
        self.logger.warning(f'使用 kombu 库 连接中间件')

    @deco_mq_conn_error
    def concrete_realization_of_publish(self, msg):
        self.producer.publish(json.loads(msg),exchange=self.exchange,routing_key=self._queue_name,declare=[self.queue])

    @deco_mq_conn_error
    def clear(self):
        self.channel.queue_purge(self._queue_name)

    @deco_mq_conn_error
    def get_message_count(self):
        # queue = self.channel.queue_declare(queue=self._queue_name, durable=True)
        # return queue.method.message_count
        # self.logger.warning(self.channel._size(self._queue_name))
        return self.channel._size(self._queue_name)

    def close(self):
        self.channel.close()
        self.conn.close()
        self.logger.warning('关闭 kombu 包 链接')