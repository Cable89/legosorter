import argparse
import logging
import signal
from functools import partial
import threading
import queue
import machine_controller
from queue_rows import *



class LegoSorter():
    def __init__(self):

        self.running = False

        # Start machine controller thread
        self.controller_tasks_queue  = queue.Queue()
        self.controller_events_queue = queue.Queue()

        self.machine_controller = machine_controller.MachineController(self.controller_tasks_queue, self.controller_events_queue)
        self.machine_controller.name = "Machine Controller"
        

        self.controller_tasks_queue.put("wololo")

    def start(self):
        if self.running:
            return
        self.running = True
        logging.info("Starting")
        signal.signal(signal.SIGINT, partial(signal_handler, self.machine_controller)) # see signal_handler function
        self.machine_controller.start()
        self.controller_tasks_queue.put("ping")
        self.run()

    def run(self):
        while self.machine_controller.running:
            for event in queue_rows(self.controller_events_queue, timeout=1):
                logging.info("Event: {}".format(event))

    # Do cleanup tasks here
    def stop(self):
        if not self.running:
            return
        logging.info("Stopping")
        self.running = False
        #self.controller_tasks_queue.put("stop")
        #self.machine_controller.stop()
        #self.machine_controller.join()

    def __del__(self):
        self.stop()


# This function captures SIGINT (Keyboard interrupt i.e.) and stops the child thread gracefully before exiting the main thread.
def signal_handler(mc, *args):
    logging.debug("signal_handler")
    mc.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--loglevel')
    args = parser.parse_args()

    #loglevel = "INFO"
    loglevel = "DEBUG"
    if args.loglevel:
        loglevel = args.loglevel
    getattr(logging, loglevel.upper())
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level, format='(%(threadName)-10s):%(levelname)-8s: %(message)s')
    logging.info("Loglevel set to: {}".format(loglevel))

    legosorter = LegoSorter()
    legosorter.start()
