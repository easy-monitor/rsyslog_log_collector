#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_

import subprocess
import logging



def run_cmd(command, shell=False, close_fds=True):
    logging.info("run command %s", command)
    proc = subprocess.Popen(
        command,
        close_fds=close_fds,  # only set to True when on Unix, for WIN compatibility
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.wait()
    output, err = proc.communicate()

    result = err or output
    return proc.returncode, result
