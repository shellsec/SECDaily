import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import pickle

logger = logging.getLogger('yarb')


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    """任务数据类"""
    id: str
    url: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        """从字典创建"""
        data['status'] = TaskStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


class TaskQueue:
    """任务队列"""
    
    def __init__(self, queue_file: str = 'task_queue.pkl', max_concurrent: int = 50):
        self.queue_file = queue_file
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: List[str] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._load_queue()
    
    def _load_queue(self):
        """从文件加载队列"""
        try:
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'rb') as f:
                    data = pickle.load(f)
                    self.tasks = {k: Task.from_dict(v) for k, v in data.get('tasks', {}).items()}
                    self.pending_queue = data.get('pending_queue', [])
                logger.info(f"从文件加载任务队列: {len(self.tasks)} 个任务")
        except Exception as e:
            logger.error(f"加载任务队列失败: {str(e)}")
            self.tasks = {}
            self.pending_queue = []
    
    def _save_queue(self):
        """保存队列到文件"""
        try:
            data = {
                'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
                'pending_queue': self.pending_queue
            }
            with open(self.queue_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"保存任务队列失败: {str(e)}")
    
    def add_task(self, task_id: str, url: str, max_retries: int = 3) -> Task:
        """添加任务到队列"""
        if task_id in self.tasks:
            logger.warning(f"任务 {task_id} 已存在，跳过添加")
            return self.tasks[task_id]
        
        task = Task(
            id=task_id,
            url=url,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        self.pending_queue.append(task_id)
        self._save_queue()
        logger.info(f"添加任务: {task_id} - {url}")
        return task
    
    def add_tasks(self, urls: List[str]) -> List[Task]:
        """批量添加任务"""
        tasks = []
        for i, url in enumerate(urls):
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
            task = self.add_task(task_id, url)
            tasks.append(task)
        return tasks
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[Dict] = None, error: Optional[str] = None):
        """更新任务状态"""
        if task_id not in self.tasks:
            logger.warning(f"任务 {task_id} 不存在")
            return
        
        task = self.tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        
        self._save_queue()
        logger.debug(f"更新任务状态: {task_id} -> {status.value}")
    
    def increment_retry(self, task_id: str):
        """增加重试次数"""
        if task_id in self.tasks:
            self.tasks[task_id].retry_count += 1
            self.tasks[task_id].updated_at = datetime.now()
            self._save_queue()
    
    def get_next_task(self) -> Optional[str]:
        """获取下一个待处理任务"""
        while self.pending_queue:
            task_id = self.pending_queue.pop(0)
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                return task_id
        return None
    
    def mark_completed(self, task_id: str):
        """标记任务为完成"""
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        self.update_task_status(task_id, TaskStatus.COMPLETED)
    
    def mark_failed(self, task_id: str, error: str):
        """标记任务为失败"""
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        
        task = self.tasks.get(task_id)
        if task and task.retry_count < task.max_retries:
            self.update_task_status(task_id, TaskStatus.RETRYING)
            self.pending_queue.append(task_id)
            logger.info(f"任务 {task_id} 将重试 ({task.retry_count + 1}/{task.max_retries})")
        else:
            self.update_task_status(task_id, TaskStatus.FAILED, error=error)
    
    def get_statistics(self) -> Dict[str, int]:
        """获取队列统计信息"""
        stats = {
            'total': len(self.tasks),
            'pending': 0,
            'running': len(self.running_tasks),
            'completed': 0,
            'failed': 0,
            'retrying': 0
        }
        
        for task in self.tasks.values():
            stats[task.status.value] += 1
        
        return stats
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def clear_completed(self):
        """清除已完成的任务"""
        to_remove = [tid for tid, task in self.tasks.items() if task.status == TaskStatus.COMPLETED]
        for tid in to_remove:
            del self.tasks[tid]
        self._save_queue()
        logger.info(f"清除 {len(to_remove)} 个已完成任务")
    
    def get_failed_tasks(self) -> List[Task]:
        """获取失败的任务"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.FAILED]
    
    def retry_failed_tasks(self):
        """重试失败的任务"""
        failed_tasks = self.get_failed_tasks()
        for task in failed_tasks:
            task.status = TaskStatus.PENDING
            task.retry_count = 0
            task.error = None
            task.updated_at = datetime.now()
            self.pending_queue.append(task.id)
        self._save_queue()
        logger.info(f"重置 {len(failed_tasks)} 个失败任务为待处理状态")


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.is_running = False
    
    async def execute_task(self, task_id: str, fetch_func):
        """执行单个任务"""
        task = self.task_queue.get_task(task_id)
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return
        
        self.task_queue.update_task_status(task_id, TaskStatus.RUNNING)
        
        async with self.task_queue.semaphore:
            try:
                result = await fetch_func(task.url)
                self.task_queue.mark_completed(task_id)
                return result
            except Exception as e:
                self.task_queue.increment_retry(task_id)
                self.task_queue.mark_failed(task_id, str(e))
                logger.error(f"任务 {task_id} 执行失败: {str(e)}")
                return None
    
    async def process_queue(self, fetch_func):
        """处理队列中的所有任务"""
        self.is_running = True
        logger.info("开始处理任务队列")
        
        while True:
            task_id = self.task_queue.get_next_task()
            if not task_id:
                # 检查是否还有运行中的任务
                if not self.task_queue.running_tasks:
                    break
                await asyncio.sleep(0.1)
                continue
            
            # 创建并启动任务
            async_task = asyncio.create_task(self.execute_task(task_id, fetch_func))
            self.task_queue.running_tasks[task_id] = async_task
        
        # 等待所有任务完成
        if self.task_queue.running_tasks:
            await asyncio.gather(*self.task_queue.running_tasks.values(), return_exceptions=True)
        
        self.is_running = False
        logger.info("任务队列处理完成")
        
        # 打印统计信息
        stats = self.task_queue.get_statistics()
        logger.info(f"队列统计: {stats}")
    
    def stop(self):
        """停止执行"""
        self.is_running = False