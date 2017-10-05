import http.client as client
import ssl
from queue import Queue, Empty
from threading import Thread
from time import time

ssl._create_default_https_context = ssl._create_unverified_context

import socks

from request_package.response_object import ResponseObject


class Worker(Thread):
    """ Thread executing tasks from a given tasks queue """

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True

    def run(self):
        while True:
            try:
                func, args, kargs = self.tasks.get(block=False)
            except Empty as e:
                # Если очередь tasks пустая
                break

            try:
                func(*args, **kargs)
            except Exception as e:
                # An exception happened in this thread
                print(e)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """

    def __init__(self, num_threads):
        self.tasks = Queue()
        self.workers = []
        for _ in range(num_threads):
            self.workers.append(Worker(self.tasks))

    def add_task(self, func, *args, **kargs):
        """ Add a task to the queue """
        self.tasks.put((func, args, kargs))

    def map(self, func, args_list):
        """ Add a list of tasks to the queue """
        for args in args_list:
            self.add_task(func, args)

    def run(self):
        for worker in self.workers:
            worker.start()

    def is_running(self):
        if any([worker.is_alive() for worker in self.workers]):
            return True
        return False

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()


# TODO: редирект
class Requester:
    def __init__(self, requests=None, response_queue=None, properties=None):
        self.response_queue = response_queue
        self.requests = requests
        self.properties = properties

        self.num_threads = int(self.properties['Main']['threads'])
        self.pool = ThreadPool(self.num_threads)

        if requests:
            self.pool.map(self._send_request, self.requests)

    def run(self):
        self.pool.run()

    def is_running(self):
        return self.pool.is_running()

    def add_response(self, response):
        """ Add a response to the response_queue """
        self.response_queue.put(response)

    def _send_request(self, request):
        scheme = self.properties['RequestInfo']['scheme'].lower()
        port = int(self.properties['RequestInfo']['port'])

        if scheme == 'http':
            connection = client.HTTPConnection
        elif scheme == 'https':
            connection = client.HTTPSConnection
        else:
            raise Exception('Протокол {} не поддерживается'.format(scheme))

        proxy = self.properties['Proxy']['scheme'], self.properties['Proxy']['host'], self.properties['Proxy']['port']

        if all(conf for conf in proxy):
            proxy_scheme, proxy_host, proxy_port = proxy
            connection = connection(proxy_host, int(proxy_port))
            connection.set_tunnel(request.host, port)

            if proxy_scheme.startswith('socks'):
                connection.sock = socks.socksocket()
                sock_type = socks.PROXY_TYPE_SOCKS4 if proxy_scheme.startswith('socks4') else socks.PROXY_TYPE_SOCKS5
                connection.sock.set_proxy(sock_type, proxy_host, int(proxy_port))
                connection.sock.connect((request.host, port))
        else:
            connection = connection(request.host, port)

        try:
            request_time = time()
            connection.request(request.method, request.url_path, request.data.encode('utf8'), headers=request.headers)
            resp = connection.getresponse()
            request_time = time() - request_time
            connection.close()

            raw_response = resp.read()
            headers = dict(resp.getheaders())

            raw_response = self._decode_response(raw_response, headers)

            response_code = resp.getcode()

        except Exception as e:
            print('[-] Ошибка в requester.py: {}'.format(e))

            raw_response = ''
            response_code = -1
            request_time = -1
            headers = dict()

        kwargs = {
            'request_object': request,
            'raw_response': raw_response,
            'request_time': request_time,
            'response_code': response_code,
            'response_headers': headers
        }

        response_obj = ResponseObject(**kwargs)
        self.add_response(response_obj)

    def _decode_response(self, raw_response, headers):
        encodings = ResponseObject.determine_charsets(raw_response, headers)
        error_msg = None

        for encoding in encodings:
            try:
                raw_response = raw_response.decode(encoding=encoding)
                error_msg = None
                break
            except Exception as e:
                error_msg = e

        if error_msg:
            print(error_msg)
            return ''

        return raw_response

    def get_standard_response(self, request):
        self._send_request(request)
        return self.response_queue.get()

    def wait_completion(self):
        self.pool.wait_completion()
