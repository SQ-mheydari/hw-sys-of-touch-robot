"""
This file handles multiprocessing for HSUP analysis. There are three time consuming operations
that all run in separate process pools. Currently all have been configured for one process.
Three operations for different processes are:
- Storing images captured with camera into disk
- Running analysis processing for the captured image
- Storing image modified as part of analysis processing into disk
"""

import importlib
import logging
import multiprocessing
import time
from queue import Empty

import diskcache
import socket_logger
from hsup.analysis import Result

STORAGE_POOL_SIZE = 1
PRE_PROCESS_POOL_SIZE = 1
ANALYSIS_POOL_SIZE = 1


def api_locker(func):
    """
    Function decorator for ensuring functions are called from one source at a time.
    :param func: Function to decorate.
    :return: Decorated function.
    """
    def wrapper(*args, **kwargs):
        with args[0].api_lock:  # first argument is reference to caller object instance
            # Log decorated function name and arguments here if needed.
            output = func(*args, **kwargs)

        return output
    return wrapper


def get_queue_size(queue):
    """
    Raises NotImplementedError on Mac OSX because of broken sem_getvalue()
    Parameters
    ----------
    queue: the queue of which we want get size

    Returns: size of queue
    -------

    """
    qsize = 0
    try:
        qsize = queue.qsize()
    except Exception:
        pass
    return qsize


class BaseWorker(multiprocessing.Process):
    """
    Logging is being setup and it has both in_queue and out_queue
    that can be used during runtime
    """
    def __init__(self, *args, **kwargs):
        try:
            super().__init__()
            self.in_queue = kwargs.get('in_queue', None)
            self.out_queue = kwargs.get('out_queue', None)
            self.log = None
            self.abort_event = multiprocessing.Event()
            self.run_started = multiprocessing.Event()
            self.run_started.clear()

        except Exception as e:
            name = getattr('name', 'Unknown worker')
            logger = logging.getLogger(name)
            logger.exception(e)

    def initialize_logging(self):
        """
        Just setup logging here, this is multiprocessing.Process subclass so it won't inherit any logging
        settings from main process. Current idea is to use socket handler to send messages to server
        that's (hopefully) listening to those.
        :return:
        """
        self.log = logging.getLogger()      # use root logger to add socket_handler to
        self.log.setLevel(logging.INFO)     # set logging level to INFO to prevent log file pollution
        # get socket handler with default socket_logger values
        socket_handler = socket_logger.get_socket_handler()
        self.log.addHandler(socket_handler)
        self.log.debug('starting {}'.format(self.name))

    def run(self):
        """
        Just example. Will exit after getting None in queue.
        Read data from in_queue and log it
        :return:
        """
        self.initialize_logging()
        self.run_started.set()
        while True:
            data = self.in_queue.get(block=True)
            if data is not None:
                self.log.debug('Received {} from queue.'.format(data))
            else:
                self.log.info('BaseWorker: exiting')
                break
        self.log.info('Run method finished')


class ImgStorageMp(BaseWorker):
    """
    Multiprocess worker for storing images in diskcache.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diskcache_directory = kwargs.get('diskcache_directory')
        self.dc = None

    def run(self):
        self.initialize_logging()
        self.dc = diskcache.Cache(directory=self.diskcache_directory)
        self.dc.clear()
        # disable automatic culling of keys
        self.dc.reset('cull_limit', 0)
        index = 0
        self.run_started.set()
        while True:
            hsup_img = self.in_queue.get(block=True)

            if self.abort_event.is_set():
                self.log.info("Received shutdown signal, exiting.")
                break

            # incoming None signals end of image stream
            if hsup_img is not None:
                self.dc.add(index, hsup_img)
                index += 1
            else:
                self.log.debug('Received None from the queue')
                self.log.info('Exiting')
                break

        self.log.info('Run method finished')
        self.dc.close()


class ImgReadingMp(BaseWorker):
    """
    Read image from diskcache and put to queue
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diskcache_directory = kwargs.get('diskcache_directory')
        self.dc = None

    def run(self):
        self.initialize_logging()
        self.dc = diskcache.Deque(directory=self.diskcache_directory)
        self.log.info('Trying to read images from {}'.format(self.diskcache_directory))
        self.run_started.set()
        while True:
            try:
                self.log.info('Deque length = {}'.format(
                    len(self.dc)
                ))
                hsup_input = self.dc.popleft()
                # convert to int16 if needed
                self.out_queue.put(hsup_input)
            except IndexError as e:
                # empty deque
                self.log.exception(e)
                break
        self.out_queue.put(None)
        self.log.info('Run method finished')


class ImgAnalyseMp(BaseWorker):
    """
    Multiprocessing worker for analysing images for SPA analyser
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_queue = kwargs.get('storage_queue')
        self.analysis = kwargs.get('analysis')
        self.analysis_kwargs = kwargs.get('analysis_kwargs')

    def run(self):
        self.initialize_logging()

        # dynamically load analysis class and create instance with given keyword arguments
        driver_module = importlib.import_module('hsup.' + self.analysis.lower())
        driver_class = getattr(driver_module, self.analysis)
        analysis = driver_class(**self.analysis_kwargs)

        final_results = None
        self.run_started.set()
        while True:
            hsup_image = self.in_queue.get(block=True)
            if self.abort_event.is_set():
                self.log.info("Received shutdown signal, exiting.")
                break

            if hsup_image is not None:
                self.log.debug('Analysing image {}'.format(hsup_image.countervalue))
                # here analyse
                try:
                    return_image = analysis.process_image(hsup_image, **self.analysis_kwargs)

                # in case of an exception, clear process queue and exit
                except Exception as e:
                    self.log.exception(e)
                    final_results = Result.create_error_result(self.analysis, {}, str(e))
                    # send stop signal to results storage process
                    self.storage_queue.put(None)
                    self.log.debug("Clearing analysis input queue due to exception")
                    if not self.in_queue.empty():
                        while True:
                            try:
                                self.in_queue.get(timeout=1)
                            except Empty:
                                break
                    break
                if return_image is not None:  # don't put None in storage queue of returned images from analysis
                    self.log.debug("Putting image {} analysis result to storage queue".format(hsup_image.countervalue))
                    self.storage_queue.put(
                        {
                            'image': return_image,
                            'countervalue': hsup_image.countervalue
                        }
                        )
            else:
                self.log.info("Received None from in_queue, queue size now {}".format(get_queue_size(self.in_queue)))
                self.log.info('Exiting')
                break

        if self.abort_event.is_set():
            final_results = Result.create_error_result(self.analysis, {}, "Analysis computation timed out.")

        # after getting None from in_queue go here:
        # Only calculate results if there was no error in previous step.
        elif final_results is None or final_results.status != Result.HSUP_RESULT_STATUS_FAIL:
            try:
                # Wait while ResultsStorageMp consumes and stores all result images.
                while not self.storage_queue.empty():
                    self.log.debug("Waiting for storage queue to be empty")
                    time.sleep(1)
                final_results = analysis.calculate_results()
            except Exception as e:
                self.log.exception(e)
                final_results = Result.create_error_result(self.analysis, {}, str(e))
        self.log.info('Returning final result {}'.format(final_results))
        self.out_queue.put(final_results)
        self.log.info('Run method finished')


class ResultsStorageMp(BaseWorker):
    """
    Multiprocessing worker for saving images from analysis results
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diskcache_directory = kwargs.get('diskcache_directory')
        self.dc = None

    def run(self):
        self.initialize_logging()
        self.dc = diskcache.Cache(directory=self.diskcache_directory)
        self.dc.clear()
        # disable automatic culling of keys
        self.dc.reset('cull_limit', 0)
        index = 0
        self.run_started.set()
        while True:
            results = self.in_queue.get(block=True)
            if results is not None:
                self.log.debug('Saving analysis result image {}'.format(results['countervalue']))
                image = results['image']
                self.dc.add(index, image)
                index += 1
            elif self.abort_event.is_set():
                self.log.info("Received shutdown signal, exiting.")
                break
            else:
                self.log.info('Exiting')
                break
        self.log.info('Run method finished')


class StoragePool:
    """
    Multiprocess pool of workers for storing images into diskcache.
    """
    def __init__(self, diskcache_directory):
        self.diskcache_directory = diskcache_directory
        self.in_queue = multiprocessing.Queue()
        self.img_storage_pool = []
        for _ in range(STORAGE_POOL_SIZE):
            img_storage_mp = ImgStorageMp(
                in_queue=self.in_queue,
                diskcache_directory=diskcache_directory
            )
            self.img_storage_pool.append(img_storage_mp)

    def start(self):
        for i in range(len(self.img_storage_pool)):
            self.img_storage_pool[i].start()

    def close(self, join_timeout=1):
        logging.info('closing {}'.format(self.__class__.__name__))
        try:
            logging.debug('in_queue empty {}'.format(
                self.in_queue.empty(),
            ))
            for i in range(STORAGE_POOL_SIZE):
                self.in_queue.put(None, timeout=1)
                self.img_storage_pool[i].join(timeout=join_timeout)
        except Exception as e:
            logging.exception(e)
        # make sure that processes are dead
        for i in range(STORAGE_POOL_SIZE):
            process = self.img_storage_pool[i]
            if process.is_alive():
                logging.warning('StoragePool: had to terminate process {}'.format(process.name))
                process.terminate()

        logging.info('closed {}'.format(self.__class__.__name__))

    def store_image(self, image):
        self.in_queue.put_nowait(image)

    def clear_diskcache(self):
        dc = diskcache.Deque(directory=self.diskcache_directory)
        logging.info('Clearing diskcache at: {}, from {} elements'.format(
            self.diskcache_directory, len(dc)))
        dc.clear()

    def is_started(self):
        """
        Check if processes have been started.
        :return: Return True if all processes in the pool have been started.
        """
        started = True
        for process in self.img_storage_pool:
            started = started and process.run_started.is_set()
        return started

    def is_running(self):
        for process in self.img_storage_pool:
            if process.is_alive():
                return True
        return False

    def storage_is_running(self):
        return self.img_storage_pool[0].is_alive()

    @property
    def images_remaining(self):
        return get_queue_size(self.in_queue)


class AnalysisPool:
    """
    - Read images from input queue.
    - Feed images to analysis worker process.
    - Analysis result images are fed to results storage process via the output queue.
    """
    def __init__(self, analysed_images_directory, **kwargs):

        self.out_hsup_img_queue = multiprocessing.Queue()

        self.out_analysed_results = multiprocessing.Queue()
        self.out_analysed_images_storage = multiprocessing.Queue()
        self.img_analysis_pool = []
        self.api_lock = multiprocessing.Lock()

        img_analysis_mp = ImgAnalyseMp(
            in_queue=self.out_hsup_img_queue,
            out_queue=self.out_analysed_results,
            storage_queue=self.out_analysed_images_storage,
            analysis_class=kwargs.get('analysis_class', None),
            analysis=kwargs.get('analysis', None),
            analysis_kwargs=kwargs.get('analysis_kwargs', None)
        )
        self.img_analysis_pool.append(img_analysis_mp)
        # results storage pool (designed for single process)
        analysed_image_storage_mp = ResultsStorageMp(
            diskcache_directory=analysed_images_directory,
            in_queue=self.out_analysed_images_storage
        )
        self.results_storage_pool = [analysed_image_storage_mp]
        # hold reference to all pools
        self.process_pools = (
            # self.img_reading_pool,
            self.img_analysis_pool,
            self.results_storage_pool
        )
        self.queues = (
            self.out_hsup_img_queue,
            self.out_analysed_results,
            self.out_analysed_images_storage
        )

    def start(self):
        for i in range(len(self.img_analysis_pool)):
            self.img_analysis_pool[i].start()

        for i in range(len(self.results_storage_pool)):
            self.results_storage_pool[i].start()

    def read_results(self, timeout=1):
        while True:
            try:
                results = self.out_analysed_results.get(timeout=timeout)
                return results
            except Empty as e:
                logging.exception(e)
                return None

    def is_running(self):
        for pool in self.process_pools:
            for process in pool:
                if process.is_alive():
                    return True
        return False

    def is_started(self):
        """
        Check if processes have been started.
        :return: Return True if all processes in the pool have been started.
        """
        started = True
        for pool in self.process_pools:
            for process in pool:
                started = started and process.run_started.is_set()
        return started

    def analyse_image(self, image):
        self.out_hsup_img_queue.put_nowait(image)

    def analysis_is_running(self):
        return self.img_analysis_pool[0].is_alive()

    def result_storage_is_running(self):
        return self.results_storage_pool[0].is_alive()

    @property
    def images_remaining(self):
        return get_queue_size(self.out_hsup_img_queue)

    @property
    def storage_images_remaining(self):
        return get_queue_size(self.out_analysed_images_storage)

    @property
    def empty(self):
        return self.out_hsup_img_queue.empty()

    def abort(self):
        """
        Immediately stop all work in processes and shut them down.
        :return:
        """
        logging.info('aborting {}'.format(self.__class__.__name__))
        # Signal all processes to abort working
        for pool in self.process_pools:
            for process in pool:
                if process.is_alive():
                    process.abort_event.set()

    @api_locker
    def close(self):
        logging.info('closing {}'.format(self.__class__.__name__))
        try:
            # Clear queue of incoming HSUP images before closing process.
            if not self.out_hsup_img_queue.empty():
                while True:
                    try:
                        self.out_hsup_img_queue.get(timeout=1)
                    except Empty:
                        break

            logging.debug('img_queue empty {}, '
                          ', results_queue empty {}, analysed_images queue empty {}'.format(
                              self.out_hsup_img_queue.empty(),
                              self.out_analysed_results.empty(),
                              self.out_analysed_images_storage.empty()
                          ))
            # Send signal to processes to finish work
            # self.out_hsup_img_queue.put(None, timeout=1)

            logging.debug("Putting None to storage queue")

            # wait for analysis results storage to finish
            while not self.out_analysed_images_storage.empty():
                pass
            # signal end to results storage process
            self.out_analysed_images_storage.put(None)

            # Try to join all processes
            for pool in self.process_pools:
                for process in pool:
                    if process.is_alive():
                        # Looks like at least 2 seconds is needed to avoid the join() timeout.
                        process.join(timeout=2)  # TODO: investigate timeout value

        except Exception as e:
            logging.exception(e)
        # make sure that processes are dead
        for pool in self.process_pools:
            for process in pool:
                if process.is_alive():
                    logging.warning('AnalysisPool: had to terminate process {}'.format(process.name))
                    process.terminate()

        logging.info('closed {}'.format(self.__class__.__name__))
