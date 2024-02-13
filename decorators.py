import signal
import time
from functools import wraps


class TimeoutError(Exception):
    pass


def func_timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError("Function execution timed out")

            # Raised when the signal is received
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Reset the alarm
                signal.alarm(0)

            return result

        return wrapper

    return decorator


@func_timeout(2)  # Set the timeout to 2 seconds
def my_function():
    time.sleep(5)
    print("Function executed successfully")


if __name__ == '__main__':
    try:
        my_function()
    except TimeoutError as e:
        print(e)  # Output: Function execution timed out
