import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger('yarb')


@dataclass
class RSSState:
    """RSS源状态"""
    url: str
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    last_articles: List[str] = None
    failure_count: int = 0
    success_count: int = 0
    last_checked: Optional[str] = None
    
    def __post_init__(self):
        if self.last_articles is None:
            self.last_articles = []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RSSState':
        """从字典创建"""
        return cls(**data)
    
    def get_url_hash(self) -> str:
        """获取URL的哈希值"""
        return hashlib.md5(self.url.encode()).hexdigest()


class ResumeManager:
    """断点续传管理器"""
    
    def __init__(self, state_file: str = 'rss_state.json'):
        self.state_file = Path(state_file)
        self.states: Dict[str, RSSState] = {}
        self._load_state()
    
    def _load_state(self):
        """从文件加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.states = {
                        url: RSSState.from_dict(state_data)
                        for url, state_data in data.items()
                    }
                logger.info(f"从文件加载RSS状态: {len(self.states)} 个RSS源")
        except Exception as e:
            logger.error(f"加载RSS状态失败: {str(e)}")
            self.states = {}
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            # 先保存到临时文件
            temp_file = self.state_file.with_suffix('.tmp')
            data = {url: state.to_dict() for url, state in self.states.items()}
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 替换原文件
            temp_file.replace(self.state_file)
            
        except Exception as e:
            logger.error(f"保存RSS状态失败: {str(e)}")
    
    def get_state(self, url: str) -> Optional[RSSState]:
        """获取RSS源状态"""
        return self.states.get(url)
    
    def update_success(self, url: str, articles: List[str]):
        """更新成功状态"""
        if url not in self.states:
            self.states[url] = RSSState(url=url)
        
        state = self.states[url]
        state.last_success = datetime.now().isoformat()
        state.last_articles = articles
        state.success_count += 1
        state.last_checked = datetime.now().isoformat()
        state.failure_count = 0  # 重置失败计数
        
        self._save_state()
        logger.debug(f"更新成功状态: {url}")
    
    def update_failure(self, url: str, error: str):
        """更新失败状态"""
        if url not in self.states:
            self.states[url] = RSSState(url=url)
        
        state = self.states[url]
        state.last_failure = datetime.now().isoformat()
        state.failure_count += 1
        state.last_checked = datetime.now().isoformat()
        
        self._save_state()
        logger.debug(f"更新失败状态: {url} - {error}")
    
    def get_last_articles(self, url: str) -> List[str]:
        """获取上次处理的文章列表"""
        state = self.get_state(url)
        return state.last_articles if state else []
    
    def should_skip(self, url: str, max_failure_count: int = 5) -> bool:
        """判断是否应该跳过该RSS源"""
        state = self.get_state(url)
        if not state:
            return False
        
        # 如果失败次数过多，跳过
        if state.failure_count >= max_failure_count:
            logger.warning(f"RSS源 {url} 失败次数过多 ({state.failure_count})，跳过")
            return True
        
        return False
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.states)
        success_count = sum(1 for s in self.states.values() if s.last_success)
        failure_count = sum(1 for s in self.states.values() if s.last_failure and not s.last_success)
        total_failures = sum(s.failure_count for s in self.states.values())
        total_successes = sum(s.success_count for s in self.states.values())
        
        return {
            'total_rss': total,
            'successful_rss': success_count,
            'failed_rss': failure_count,
            'total_failures': total_failures,
            'total_successes': total_successes,
            'success_rate': f"{(total_successes / (total_successes + total_failures) * 100):.2f}%" if (total_successes + total_failures) > 0 else "0%"
        }
    
    def clear_old_states(self, days: int = 30):
        """清除旧的状态"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        to_remove = []
        
        for url, state in self.states.items():
            if state.last_checked:
                checked_time = datetime.fromisoformat(state.last_checked).timestamp()
                if checked_time < cutoff_date:
                    to_remove.append(url)
        
        for url in to_remove:
            del self.states[url]
        
        if to_remove:
            self._save_state()
            logger.info(f"清除 {len(to_remove)} 个超过 {days} 天的旧状态")
    
    def reset_failure_counts(self, urls: Optional[List[str]] = None):
        """重置失败计数"""
        if urls is None:
            # 重置所有
            for state in self.states.values():
                state.failure_count = 0
                state.last_failure = None
        else:
            # 重置指定的URL
            for url in urls:
                if url in self.states:
                    self.states[url].failure_count = 0
                    self.states[url].last_failure = None
        
        self._save_state()
        logger.info(f"重置失败计数: {len(urls) if urls else '全部'} 个RSS源")
    
    def export_state(self, export_file: str):
        """导出状态到文件"""
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {url: state.to_dict() for url, state in self.states.items()},
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            logger.info(f"状态已导出到: {export_file}")
        except Exception as e:
            logger.error(f"导出状态失败: {str(e)}")
    
    def import_state(self, import_file: str, merge: bool = True):
        """从文件导入状态"""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if merge:
                # 合并状态
                for url, state_data in data.items():
                    self.states[url] = RSSState.from_dict(state_data)
            else:
                # 替换状态
                self.states = {
                    url: RSSState.from_dict(state_data)
                    for url, state_data in data.items()
                }
            
            self._save_state()
            logger.info(f"状态已从 {import_file} 导入: {len(data)} 个RSS源")
        except Exception as e:
            logger.error(f"导入状态失败: {str(e)}")


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, progress_file: str = 'progress.json'):
        self.progress_file = Path(progress_file)
        self.progress: Dict = {}
        self._load_progress()
    
    def _load_progress(self):
        """从文件加载进度"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress = json.load(f)
                logger.debug(f"加载进度: {self.progress}")
        except Exception as e:
            logger.error(f"加载进度失败: {str(e)}")
            self.progress = {}
    
    def _save_progress(self):
        """保存进度到文件"""
        try:
            temp_file = self.progress_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.progress_file)
        except Exception as e:
            logger.error(f"保存进度失败: {str(e)}")
    
    def start_session(self, session_id: str, total_tasks: int):
        """开始一个会话"""
        self.progress[session_id] = {
            'total': total_tasks,
            'completed': 0,
            'failed': 0,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'status': 'running'
        }
        self._save_progress()
        logger.info(f"开始会话 {session_id}: {total_tasks} 个任务")
    
    def update_progress(self, session_id: str, completed: int = 0, failed: int = 0):
        """更新进度"""
        if session_id not in self.progress:
            logger.warning(f"会话 {session_id} 不存在")
            return
        
        self.progress[session_id]['completed'] += completed
        self.progress[session_id]['failed'] += failed
        self._save_progress()
    
    def complete_session(self, session_id: str):
        """完成会话"""
        if session_id in self.progress:
            self.progress[session_id]['completed_at'] = datetime.now().isoformat()
            self.progress[session_id]['status'] = 'completed'
            self._save_progress()
            logger.info(f"会话 {session_id} 完成")
    
    def get_progress(self, session_id: str) -> Optional[Dict]:
        """获取会话进度"""
        return self.progress.get(session_id)
    
    def get_all_sessions(self) -> List[Dict]:
        """获取所有会话"""
        return [
            {'session_id': sid, **data}
            for sid, data in self.progress.items()
        ]
    
    def clear_old_sessions(self, days: int = 7):
        """清除旧会话"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        to_remove = []
        
        for sid, data in self.progress.items():
            if data.get('completed_at'):
                completed_time = datetime.fromisoformat(data['completed_at']).timestamp()
                if completed_time < cutoff_date:
                    to_remove.append(sid)
        
        for sid in to_remove:
            del self.progress[sid]
        
        if to_remove:
            self._save_progress()
            logger.info(f"清除 {len(to_remove)} 个超过 {days} 天的旧会话")