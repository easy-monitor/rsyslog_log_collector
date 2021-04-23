#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_

import fcntl
import os
import logging
import time


def run_with_filelock(file_path):
    def deco(func):
        def run(*args, ** kwargs):
            file = open(file_path, "r+")
            for i in range(3):
                try:
                    fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logging.info('acquire lock')
                    func(args, kwargs)
                    break
                    # file.close()
                    # logging.info('release lock')
                except Exception as e:
                    logging.error("run error, will retry in 3s. %s", e.message)
                    time.sleep(3)

            file.close()
            logging.info('release lock')
            return
        return run
    return deco


def create_lock_file(file_path):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("0")

