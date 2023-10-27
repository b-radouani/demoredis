# init_container.py
import redis
import os

r = redis.StrictRedis(host='your-redis-host', port=6379, db=0)

def can_run_job(job_id):
    dependencies = r.lrange(f'job:{job_id}:dependencies', 0, -1)
    for dep in dependencies:
        status = r.hget(f'job:{dep}', 'status')
        if status != b'Completed':
            return False
    return True

def init_container_function():
    job_id = os.environ.get('JOB_ID')
    if not can_run_job(job_id):
        exit(1)
    exit(0)
# side_container.py
import redis
import time
import os

r = redis.StrictRedis(host='your-redis-host', port=6379, db=0)

def update_status_and_trigger_dependents(job_id, status):
    r.hset(f'job:{job_id}', 'status', status)
    if status == 'Completed':
        dependents = r.lrange(f'job:{job_id}:dependents', 0, -1)
        for dependent in dependents:
            r.hset(f'job:{dependent}', 'status', 'Pending')

def sidecar_function():
    job_id = os.environ.get('JOB_ID')
    while True:
        try:
            with open('/shared/status.txt', 'r') as f:
                status = f.read().strip()
            if status in ['Completed', 'Failed']:
                update_status_and_trigger_dependents(job_id, status)
                break
        except FileNotFoundError:
            pass
        time.sleep(5)


# admin.py
import redis

r = redis.StrictRedis(host='your-redis-host', port=6379, db=0)

def set_dependencies(job_id, dependencies):
    r.delete(f'job:{job_id}:dependencies')
    for dep in dependencies:
        r.rpush(f'job:{job_id}:dependencies', dep)
        r.rpush(f'job:{dep}:dependents', job_id)

def admin_function():
    # Here we're setting dependencies as an example; in reality, this might be dynamic or read from a file or external source.
    set_dependencies(30, [29])
    set_dependencies(29, [23, 24, 25, 26, 27, 28])

# clean_up.py
import redis

r = redis.StrictRedis(host='your-redis-host', port=6379, db=0)

def clean_up_function():
    # As an example, let's delete jobs that are marked as "Completed". 
    # Adjust this logic to whatever cleanup you want to achieve.
    for key in r.scan_iter("job:*:status"):
        if r.hget(key, 'status') == b'Completed':
            r.delete(key)

# main.py
import os
from init_container import init_container_function
from side_container import sidecar_function
from admin import admin_function
from clean_up import clean_up_function

if __name__ == '__main__':
    role = os.environ.get('ROLE')
    if role == 'init':
        init_container_function()
    elif role == 'side':
        sidecar_function()
    elif role == 'admin':
        admin_function()
    elif role == 'cleanup':
        clean_up_function()
    else:
        raise ValueError("ROLE environment variable must be one of ['init', 'side', 'admin', 'cleanup']")
