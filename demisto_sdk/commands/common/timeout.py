#!/usr/bin/env python3
import threading, time, ctypes
from contextlib import contextmanager

'''
-----------------------------------------------------------------------
Copyright (c) 2021 Levi M. Luke, LIU Wei, Brett Husar, and others
-----------------------------------------------------------------------
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files
(the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

@contextmanager
def timeout(seconds: int = 0):
    """context manager for timeout

    Args:
        seconds (int):  Number of seconds to timeout. Defaults to 0.

    Raises:
        TimeoutError: if reached timeout raise error
    """
    if not seconds:  # run without timeout
        yield
        return

    def raise_caller():
        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(caller_thread._ident),
                                                         ctypes.py_object(TimeoutError))
        if ret == 0:
            raise ValueError("Invalid thread ID")
        elif ret > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(caller_thread._ident, NULL)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    caller_thread = threading.current_thread()
    timer = threading.Timer(seconds, raise_caller)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
