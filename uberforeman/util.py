import threading,time
try:
    import queue
except:
    # python 2.x fallback
    import Queue as queue

def run_parallel(target, args_list):
    result = queue.Queue()
    # wrapper to collect return value in a Queue
    def task_wrapper(*args):
        result.put(target(*args))
    threads = [threading.Thread(target=task_wrapper, args=args) for args in args_list]
    for t in threads:
        t.daemon = True
        t.start()
    for t in threads:
        while t.isAlive():
            time.sleep(0.1)
    return result

