import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import feedparser
from pathlib import Path

from retry_utils import retry_with_backoff, RetryConfig, circuit_breaker, async_retry_with_backoff, async_circuit_breaker
from resume_manager import ResumeManager, ProgressTracker

logger = logging.getLogger('yarb')


class AsyncRSSFetcher:
    """异步RSS获取器"""
    
    def __init__(
        self,
        max_concurrent: int = 50,
        timeout: int = 30,
        resume_manager: Optional[ResumeManager] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.resume_manager = resume_manager or ResumeManager()
        self.progress_tracker = progress_tracker
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_feed(
        self,
        url: str,
        proxy_url: str = '',
        headers: Optional[Dict] = None
    ) -> Optional[str]:
        """获取单个RSS源的内容"""
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
        
        proxy = proxy_url if proxy_url else None
        
        @async_circuit_breaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
        )
        @async_retry_with_backoff(
            config=RetryConfig(
                max_attempts=2,
                base_delay=1.0,
                max_delay=10.0,
                retryable_exceptions=(
                    aiohttp.ClientError,
                    asyncio.TimeoutError
                )
            )
        )
        async def _fetch():
            async with self.session.get(url, headers=headers, proxy=proxy) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )
                return await response.text()
        
        try:
            result = await _fetch()
            logger.debug(f"成功获取RSS源: {url}")
            return result
        except Exception as e:
            # 只在最终失败时输出error，避免重复日志
            error_msg = str(e) if str(e) else type(e).__name__
            logger.error(f"获取RSS源失败 {url}: {error_msg}")
            return None
    
    async def parse_feed(
        self,
        content: str,
        url: str,
        exclude_keywords: List[str],
        verbose: bool = False
    ) -> Tuple[str, Dict[str, str]]:
        """解析RSS源内容"""
        try:
            feed = feedparser.parse(content)
            title = getattr(feed.feed, 'title', 'Unknown')
            
            result = {}
            yesterday = datetime.today().date() + timedelta(days=-1)
            
            for entry in feed.entries:
                # 获取发布日期
                d = entry.get('published_parsed') or entry.get('updated_parsed')
                if not d:
                    continue
                
                pubday = datetime(d[0], d[1], d[2])
                
                # 只获取昨天的文章
                if pubday == yesterday:
                    # 过滤关键词
                    if not any(keyword in entry.title for keyword in exclude_keywords):
                        result[entry.title] = entry.link
                        if verbose:
                            print(f"  - {entry.title}")
            
            if verbose:
                logger.info(f"[+] {title}\t{url}\t{len(result.values())}/{len(feed.entries)}")
            
            return title, result
        except Exception as e:
            logger.error(f"解析RSS源失败 {url}: {str(e)}")
            return '', {}
    
    async def fetch_and_parse(
        self,
        url: str,
        proxy_url: str = '',
        exclude_keywords: List[str] = None,
        verbose: bool = False
    ) -> Tuple[str, Dict[str, str]]:
        """获取并解析RSS源（带断点续传）"""
        if exclude_keywords is None:
            exclude_keywords = []
        
        # 检查是否应该跳过该RSS源
        if self.resume_manager.should_skip(url):
            logger.warning(f"跳过RSS源: {url}")
            return '', {}
        
        content = await self.fetch_feed(url, proxy_url)
        if content:
            title, articles = await self.parse_feed(content, url, exclude_keywords, verbose)
            
            if articles:
                # 更新成功状态
                self.resume_manager.update_success(url, list(articles.values()))
            else:
                # 没有获取到文章，记录为成功但没有新文章
                self.resume_manager.update_success(url, [])
            
            return title, articles
        else:
            # 获取失败，更新失败状态
            self.resume_manager.update_failure(url, "获取RSS内容失败")
            return '', {}
    
    async def fetch_all_feeds(
        self,
        urls: List[str],
        proxy_url: str = '',
        exclude_keywords: List[str] = None,
        verbose: bool = False
    ) -> List[Tuple[str, Dict[str, str]]]:
        """并发获取所有RSS源（带进度显示）"""
        if exclude_keywords is None:
            exclude_keywords = []
        
        total = len(urls)
        logger.info(f"开始并发获取 {total} 个RSS源，最大并发数: {self.max_concurrent}")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        completed = 0
        lock = asyncio.Lock()
        
        async def fetch_with_semaphore(url):
            nonlocal completed
            async with semaphore:
                result = await self.fetch_and_parse(url, proxy_url, exclude_keywords, verbose)
                async with lock:
                    completed += 1
                    # 每完成50个或完成时显示进度
                    if completed % 50 == 0 or completed == total:
                        progress_pct = completed * 100 // total
                        print(f"[进度] {completed}/{total} ({progress_pct}%)", end='\r', flush=True)
                return result
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"获取RSS源时发生异常: {str(result)}")
            elif result and result[1]:  # result[1] 是文章字典
                valid_results.append(result)
        
        print()  # 换行，清除进度显示
        logger.info(f"成功获取 {len(valid_results)} 个RSS源")
        return valid_results


async def async_parse_thread(
    conf: dict,
    url: str,
    proxy_url: str = '',
    verbose: bool = False
) -> Tuple[str, Dict[str, str]]:
    """异步版本的parseThread函数"""
    async with AsyncRSSFetcher(max_concurrent=50, timeout=10) as fetcher:
        exclude_keywords = conf.get('exclude', [])
        return await fetcher.fetch_and_parse(url, proxy_url, exclude_keywords, verbose)


async def async_fetch_all_articles(
    conf: dict,
    urls: List[str],
    proxy_url: str = '',
    verbose: bool = False,
    session_id: Optional[str] = None
) -> List[Dict[str, Dict[str, str]]]:
    """异步获取所有文章（带进度跟踪）"""
    # 创建断点续传管理器和进度跟踪器
    resume_manager = ResumeManager()
    progress_tracker = ProgressTracker()
    
    # 开始会话
    if session_id:
        progress_tracker.start_session(session_id, len(urls))
    
    async with AsyncRSSFetcher(
        max_concurrent=50,
        timeout=10,
        resume_manager=resume_manager,
        progress_tracker=progress_tracker
    ) as fetcher:
        exclude_keywords = conf.get('exclude', [])
        results = await fetcher.fetch_all_feeds(urls, proxy_url, exclude_keywords, verbose)
        
        # 转换为与原格式一致的结构
        formatted_results = []
        for title, articles in results:
            if articles:
                formatted_results.append({title: articles})
        
        # 完成会话
        if session_id:
            progress_tracker.complete_session(session_id)
        
        # 打印统计信息
        stats = resume_manager.get_statistics()
        logger.info(f"RSS源统计: {stats}")
        
        return formatted_results