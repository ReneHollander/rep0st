import calendar
import ctypes
import datetime
import logging
import sched
import threading
from threading import Thread
from typing import Callable, List

from crontab import CronTab
from injector import Module, inject, singleton
from prometheus_client.metrics import Gauge

from rep0st.framework.execute import execute
from rep0st.framework.signal_handler import on_shutdown

log = logging.getLogger(__name__)

framework_scheduler_tasks_running_z = Gauge(
    'framework_scheduler_tasks_running', 'Number of tasks currently running.')
framework_scheduler_tasks_scheduled_z = Gauge(
    'framework_scheduler_tasks_scheduled',
    'Number of tasks scheduled to be run in the future.')
framework_scheduler_exit_z = Gauge('framework_scheduler_exit',
                                   'Set to 1 if the scheduler is marked exit.')


class SchedulerModule(Module):

  def configure(self, binder):
    binder.bind(Scheduler)


class _SignalFinish(Exception):
  pass


class _Schedule:
  crontab: CronTab = None

  @classmethod
  def from_str(cls, timespec: str):
    s = _Schedule()
    if timespec != 'oneshot':
      s.crontab = CronTab(timespec)
    return s

  def next(self, now: datetime.datetime):
    if self.crontab:
      return self.crontab.next(now=now, delta=False, default_utc=True)
    else:
      return now

  def should_loop(self):
    return self.crontab


@singleton
class Scheduler:
  exit = threading.Event
  scheduler = sched.scheduler
  running_tasks = List[Thread]

  @inject
  def __init__(self) -> None:
    self.exit = threading.Event()
    self.scheduler = sched.scheduler(self._get_utc_time, self.exit.wait)
    self.running_tasks = []
    framework_scheduler_tasks_running_z.set_function(
        lambda: len(self.running_tasks))
    framework_scheduler_tasks_scheduled_z.set_function(
        lambda: len(self.scheduler.queue))
    framework_scheduler_exit_z.set_function(lambda: self.exit.is_set())

  def _get_utc_time(self) -> float:
    dts = datetime.datetime.utcnow()
    return calendar.timegm(dts.utctimetuple()) + dts.microsecond / 1e6

  def _run_task(self, schedule: _Schedule, fun: Callable[[], None]) -> None:
    log.debug(f'Executing job {fun.__module__}.{fun.__name__}')
    try:
      fun()
    except _SignalFinish:
      pass
    except:
      log.exception(f'Error executing job {fun.__name__}')
    finally:
      if not self.exit.is_set():
        if not schedule.should_loop():
          log.debug(f'Task {fun} will not be scheduled again')
        else:
          self._schedule_task(schedule, fun)
      self.running_tasks.remove(threading.current_thread())

  def _schedule_handler(self, schedule: _Schedule, fun: Callable[[],
                                                                 None]) -> None:
    thread = Thread(
        name=f'Job {fun.__module__}.{fun.__name__}',
        target=self._run_task,
        kwargs={
            'schedule': schedule,
            'fun': fun
        },
        daemon=True)
    self.running_tasks.append(thread)
    thread.start()

  def _schedule_task(self, schedule: _Schedule, fun: Callable[[],
                                                              None]) -> None:
    if self.exit.is_set():
      return
    now = self._get_utc_time()
    next_run_time = schedule.next(now)
    log.debug(
        f'Scheduling job {fun.__name__} to be run at {datetime.datetime.utcfromtimestamp(next_run_time)}'
    )
    self.scheduler.enterabs(
        next_run_time,
        1,
        self._schedule_handler,
        kwargs={
            'schedule': schedule,
            'fun': fun
        })

  def schedule(self, timespec: str, f: Callable[[], None]) -> None:
    if not timespec:
      log.debug(f'Task {f} is is ignored as the timespec is empty')
      return
    self._schedule_task(_Schedule.from_str(timespec), f)

  def _get_thread_id(self, t):
    # returns id of the respective thread
    if hasattr(t, '_thread_id'):
      return t._thread_id
    for id, thread in threading._active.items():
      if thread is t:
        return id
    raise RuntimeError('not found')

  @on_shutdown()
  def handle_shutdown(self) -> None:
    log.info('Shutting down scheduler')
    self.exit.set()
    with self.scheduler._lock:
      for e in self.scheduler.queue:
        self.scheduler.cancel(e)
    log.info('Cancelled all jobs in job queue')

    # Stop running jobs.
    for t in self.running_tasks:
      log.info(f'Sending finish signal to running {t.name}')
      res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
          ctypes.c_long(self._get_thread_id(t)),
          ctypes.py_object(_SignalFinish))
      if res == 0:
        log.error('Invalid thread id')
      elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(self._get_thread_id(t)), 0)
        log.error('Sending finish signal to thread failed')

    for t in self.running_tasks:
      log.info(f'Waiting 60 seconds for {t.name} to finish')
      t.join(timeout=60)
      if t.is_alive():
        log.error('Job did not finish after 60 second timeout. Forcing stop...')

    log.info('Finished scheduler shutdown')

  def _has_work(self):
    return len(self.running_tasks) > 0 or not self.scheduler.empty()

  def _run_scheduler(self):
    while not self.exit.is_set() and self._has_work():
      self.scheduler.run()

  @execute(order=float('inf'))
  def run_scheduler(self) -> Thread:
    thread = Thread(name='Scheduler', target=self._run_scheduler)
    thread.start()
    log.info(f'Started scheduler in thread {thread.name}')
    return thread
