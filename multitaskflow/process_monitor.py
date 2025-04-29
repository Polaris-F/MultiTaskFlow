#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进程监控模块 (Process Monitor Module)

此模块提供了进程监控和消息推送功能，主要用于:
1. 监控长时间运行的进程状态
2. 在进程完成或失败时发送通知
3. 提供简单的消息推送功能

主要组件:
- ProcessMonitor: 进程监控线程类，用于实时监控指定进程的运行状态
- Msg_push: 消息推送函数，用于发送通知到微信等平台
- setup_logger: 日志设置辅助函数

使用示例见文件末尾的 __main__ 部分
"""

import logging
import os
import subprocess
import time
import psutil
import requests
from threading import Thread
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Optional, Union, List

def Msg_push(title: str, content: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    发送消息到PushPlus平台，可用于向微信推送通知
    
    Args:
        title: 消息标题，显示在通知顶部
        content: 消息内容，支持HTML/文本格式
        logger: 可选的日志记录器，如不提供则创建一个新的
    
    Returns:
        bool: 发送是否成功
    
    示例:
        >>> Msg_push("任务完成", "训练已完成，准确率达到95%")
        >>> Msg_push("错误警告", "服务器CPU使用率超过90%，请检查", my_logger)
    
    注意:
        需要设置 MSG_PUSH_TOKEN 环境变量，可以通过以下方式设置：
        1. 在 ~/.bashrc 或 ~/.zshrc 中添加: export MSG_PUSH_TOKEN=your_token
        2. 在运行前临时设置: MSG_PUSH_TOKEN=your_token python your_script.py
        3. 在 .env 文件中设置（仅开发模式）
    """
    # 如果没有提供logger，创建一个简单的logger
    if logger is None:
        logger = logging.getLogger('Msg_push')
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    # 加载token
    load_dotenv()
    token = os.getenv('MSG_PUSH_TOKEN')
    
    # 详细的token检查和处理
    if not token:
        error_msg = """
        未找到 MSG_PUSH_TOKEN 环境变量！
        
        请通过以下方式之一设置 MSG_PUSH_TOKEN：
        1. 在 ~/.bashrc 或 ~/.zshrc 中添加:
           export MSG_PUSH_TOKEN=your_token
           
        2. 在运行前临时设置:
           MSG_PUSH_TOKEN=your_token python your_script.py
           
        3. 在 .env 文件中设置（仅开发模式）
        
        获取 token 的方法：
        1. 访问 https://www.pushplus.plus/
        2. 登录并获取您的 token
        3. 将 token 添加到上述配置中
        """
        logger.error(error_msg)
        return False

    # 检查token格式
    if not isinstance(token, str) or len(token.strip()) == 0:
        logger.error("MSG_PUSH_TOKEN 格式无效：应为非空字符串")
        return False

    data = {
        "token": token,
        "title": title,
        "content": content
    }

    # 增加重试次数和等待时间以应对频率限制
    max_retries = 5
    base_wait_time = 3  # 初始等待时间，秒
    
    for attempt in range(max_retries):
        try:
            # 指数退避策略
            wait_time = base_wait_time * (2 ** attempt)
            
            if attempt > 0:
                logger.info(f"尝试第 {attempt+1}/{max_retries} 次发送消息，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                
            response = requests.post(
                'https://www.pushplus.plus/send',
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15  # 增加超时时间
            )
            
            result = response.json()
            if response.status_code == 200 and result.get('code') == 200:
                logger.info("消息发送成功")
                return True
            elif result.get('code') == 429:  # 频率限制错误码
                logger.warning(f"消息发送受到频率限制，将在 {wait_time} 秒后重试...")
                time.sleep(wait_time)  # 遇到频率限制时额外等待
                continue
            else:
                error_msg = f"消息发送失败，状态码: {response.status_code}, 返回: {response.text}"
                logger.warning(error_msg)
                # 如果是token相关错误，提供更详细的提示
                if result.get('code') in [401, 403]:
                    logger.error("""
                    Token 验证失败，请检查：
                    1. MSG_PUSH_TOKEN 是否正确设置
                    2. Token 是否已过期
                    3. 是否在 pushplus.plus 平台正确配置
                    """)
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        except Exception as e:
            logger.error(f"发送通知时发生未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        
        # 如果不是最后一次尝试，等待一段时间后继续
        if attempt < max_retries - 1:
            time.sleep(wait_time)
    
    logger.error("多次尝试后仍无法发送消息")
    return False

class ProcessMonitor(Thread):
    """
    进程监控器类，用于监控特定进程并在进程结束时发送通知
    
    此类创建一个后台线程，定期检查指定进程是否仍在运行，
    当进程结束时发送通知消息。适用于监控长时间运行的训练任务等。
    
    Attributes:
        process_name: 进程名称，用于显示和日志
        process_cmd: 进程命令，用于查找进程
        pid: 进程ID
        start_time: 进程开始时间
        
    Methods:
        set_result: 设置任务执行结果和错误信息
        check_process: 检查进程是否仍在运行
        get_duration: 获取进程运行时长的格式化字符串
        send_notification: 发送进程结束通知
    """
    
    # 固定的消息模板
    MESSAGE_TEMPLATE = {
        "title": "任务执行通知",
        "content": """
        任务名称: {process_name}
        执行状态: {status}
        PID: {pid}
        运行时长: {duration}
        结束时间: {end_time}
        {error_msg}
        """
    }

    def __init__(self, process_name: str, process_cmd: str, logger: logging.Logger, start_time: datetime = None):
        """
        初始化进程监控器
        
        Args:
            process_name: 进程名称（用于显示和通知）
            process_cmd: 进程命令（用于查找进程）
            logger: 日志记录器
            start_time: 开始时间，默认为当前时间
        """
        super().__init__()
        self.process_name = process_name
        self.process_cmd = process_cmd
        self.logger = logger
        self.start_time = start_time or datetime.now()
        self.daemon = True  # 设置为守护线程，随主线程退出
        self.return_code = None
        self.error_message = None
        load_dotenv()
        self.pid = self._find_process_pid()

    def _find_process_pid(self) -> Optional[int]:
        """
        查找进程ID
        
        通过命令行参数匹配来查找进程，返回匹配的第一个PID
        
        Returns:
            Optional[int]: 如果找到则返回进程ID，否则返回None
        """
        pids = []
        self.logger.info(f"开始查找进程: {self.process_name}")
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = " ".join(proc.info['cmdline'] or [])
                if self.process_cmd in cmdline:
                    pids.append(proc.info['pid'])
                    self.logger.debug(f"找到匹配进程: PID={proc.info['pid']}, cmdline={cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        if not pids:
            self.logger.info(f"未找到匹配的进程: {self.process_name}")
            return None
            
        self.logger.info(f"进程 {self.process_name} 的PID列表: {pids}，使用第一个PID: {pids[0]}")
        return pids[0]

    def check_process(self) -> bool:
        """
        检查进程是否仍在运行
        
        Returns:
            bool: 进程是否仍在运行
        """
        if not self.pid:
            return False
        try:
            p = psutil.Process(self.pid)
            status = p.status()
            return p.is_running() and status != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    def get_duration(self) -> str:
        """
        获取进程运行时长的格式化字符串
        
        Returns:
            str: 格式化的时间字符串，如 "2h15m30s"
        """
        duration = datetime.now() - self.start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}h{minutes}m{seconds}s"
        elif minutes > 0:
            return f"{minutes}m{seconds}s"
        else:
            return f"{seconds}s"

    def set_result(self, return_code: int, error_message: str = None):
        """
        设置任务执行结果
        
        Args:
            return_code: 返回码，0表示成功
            error_message: 错误信息，失败时提供
        """
        self.return_code = return_code
        self.error_message = error_message

    def run(self):
        """
        线程运行的主方法，定期检查进程状态
        """
        if not self.pid:
            self.logger.error(f"未找到进程 {self.process_name}")
            return
        if not self.check_process():
            self.logger.error(f"进程 {self.process_name} (PID: {self.pid}) 未运行")
            return

        was_running = True
        while True:
            is_running = self.check_process()
            if was_running and not is_running:
                self.logger.info(f"进程 {self.process_name} (PID: {self.pid}) 已结束")
                self.send_notification()
                break
            time.sleep(10)  # 每10秒检查一次
            was_running = is_running

    def send_notification(self):
        """
        发送进程结束通知
        
        Returns:
            bool: 通知是否发送成功
        """
        status = "成功完成" if self.return_code == 0 else "执行失败"
        error_msg = f"错误信息: {self.error_message}" if self.error_message else ""
        
        content = self.MESSAGE_TEMPLATE["content"].format(
            process_name=self.process_name,
            status=status,
            pid=self.pid,
            duration=self.get_duration(),
            end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            error_msg=error_msg
        )
        
        return Msg_push(self.MESSAGE_TEMPLATE["title"], content, self.logger)

def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录，默认为"logs"
        
    Returns:
        logging.Logger: 配置好的日志记录器
    
    示例:
        >>> logger = setup_logger("my_app")
        >>> logger.info("应用启动")
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    fh = logging.FileHandler(
        f"{log_dir}/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        encoding='utf-8'
    )
    fh.setLevel(logging.INFO)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

if __name__ == "__main__":
    """
    模块使用示例
    """
    
    # ==================示例1：直接调用Msg_push发送自定义消息=================
    # 设置日志记录器
    logger = setup_logger("MessageDemo")
    
    # 自定义消息示例
    title = "训练任务完成"
    content = f"""
    【训练结果报告】
    模型：YOLOv8
    数据集：COCO
    准确率：98.5%
    训练轮数：100
    完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    备注：模型性能超出预期
    """

    # 发送自定义消息
    logger.info("发送自定义消息示例...")
    Msg_push(
        title, 
        content, 
        logger
    )
    
    # 等待消息发送完成
    time.sleep(2)
    
    # ==================示例2：使用本部分程序监控进程===================
    # 设置另一个日志记录器
    logger = setup_logger("ProcessMonitorDemo")
    
    # 模拟一个长时间运行的进程
    logger.info("启动一个模拟进程...")
    
    # 在实际使用中，这可能是一个训练脚本或其他长时间运行的任务
    # 这里我们使用sleep来模拟
    cmd = "python -c 'import time; print(\"模拟进程开始运行...\"); time.sleep(15); print(\"模拟进程完成\")'"
    process = subprocess.Popen(cmd, shell=True)
    
    # 创建并启动进程监控器
    logger.info("创建进程监控器...")
    monitor = ProcessMonitor(
        process_name="示例进程",
        process_cmd="python -c",
        logger=logger
    )
    monitor.start()
    
    # 等待进程和监控器完成
    process.wait()
    monitor.join(timeout=30)
    
    logger.info("示例完成") 