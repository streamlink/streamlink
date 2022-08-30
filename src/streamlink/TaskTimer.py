import datetime
import time
from threading import Thread
from time import sleep


class TaskTimer:
    __instance = None

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        self.thread = None
        self.is_running = None
        if not hasattr(self, 'task_queue'):
            setattr(self, 'task_queue', [])

        if not hasattr(self, 'is_running'):
            setattr(self, 'is_running', False)

    def write_log(self, level, msg):
        """
        cur_time = datetime.datetime.now()
        with open('./task.log', mode='a+', encoding='utf8') as file:
            s = "[" + str(cur_time) + "][" + level + "]   " + msg
            print(s)
            file.write(s + "\n")
        """
        cur_time = datetime.datetime.now()
        s = "[" + str(cur_time) + "][" + level + "]   " + msg
        print(s)

    def work(self):

        """
        处理任务队列
        """
        while True:
            if not self.is_running:
                return
            for task in self.task_queue:
                if task['interval']:
                    self.cycle_task(task)
                elif task['timing']:
                    self.timing_task(task)

            sleep(5)

    def cycle_task(self, task):
        """
        周期任务
        """
        if task['next_sec'] <= int(time.time()):
            try:
                task['fun'](*task['arg'])
                self.write_log("正常", "周期任务：" + task['fun'].__name__ + " 已执行")
            except Exception as e:
                self.write_log("异常", "周期任务：" + task['fun'].__name__ + " 函数内部异常：" + str(e))
            finally:
                task['next_sec'] = int(time.time()) + task['interval']

    def timing_task(self, task):
        """
        定时任务
        """
        # 今天已过秒数
        today_sec = self.get_today_until_now()

        # 到了第二天，就重置任务状态
        if task['today'] != self.get_today():
            task['today'] = self.get_today()
            task['today_done'] = False

        # 第一次执行
        if task['first_work']:
            if today_sec >= task['task_sec']:
                task['today_done'] = True
                task['first_work'] = False
            else:
                task['first_work'] = False

        # 今天还没有执行
        if not task['today_done']:
            if today_sec >= task['task_sec']:  # 到点了，开始执行任务
                try:
                    task['fun'](*task['arg'])
                    self.write_log("正常", "定时任务：" + task['fun'].__name__ + " 已执行")
                except Exception as e:
                    self.write_log("异常", "定时任务：" + task['fun'].__name__ + " 函数内部异常：" + str(e))
                finally:
                    task['today_done'] = True
                    if task['first_work']:
                        task['first_work'] = False

    def get_today_until_now(self):
        """
        获取今天凌晨到现在的秒数
        """
        i = datetime.datetime.now()
        return i.hour * 3600 + i.minute * 60 + i.second

    def get_today(self):
        """
        获取今天的日期
        """
        i = datetime.datetime.now()
        return i.day

    def join_task(self, fun, arg, interval=None, timing=None):
        """
        interval和timing只能存在1个
        :param fun: 你要调用的任务
        :param arg: fun的参数
        :param interval: 周期任务，单位秒
        :param timing: 定时任务，取值：[0,24)
        """
        # 参数校验
        if (interval != None and timing != None) or (interval == None and timing == None):
            raise Exception('interval和timing只能选填1个')

        if timing and not 0 <= timing < 24:
            raise Exception('timing的取值范围为[0,24)')

        if interval and interval < 5:
            raise Exception('interval最少为5')

        # 封装一个task
        task = {
            'fun': fun,
            'arg': arg,
            'interval': interval,
            'timing': timing,
        }
        # 封装周期或定时任务相应的参数
        if timing:
            task['task_sec'] = timing * 3600
            task['today_done'] = False
            task['first_work'] = True
            task['today'] = self.get_today()
        elif interval:
            task['next_sec'] = int(time.time()) + interval

        # 把task加入任务队列
        self.task_queue.append(task)

        self.write_log("正常", "新增任务：" + fun.__name__)

    def start(self):
        """
        开始执行任务
        返回线程标识符
        """
        if not self.is_running:
            self.thread = Thread(target=self.work)

            self.thread.start()

            self.is_running = True

            self.write_log("正常", "TaskTimer已开始运行！")

        self.write_log("警告", "TaskTimer已运行，请勿重复启动！")

    def stop(self):
        if self.is_running:
            # self.thread.stop()
            self.is_running = False
            self.write_log("正常", "TaskTimer正在停止运行！")
