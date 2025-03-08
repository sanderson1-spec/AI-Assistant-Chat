"""
Task Scheduler for AI Assistant
Handles scheduling and execution of time-based tasks
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import json

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.schedulers import SchedulerAlreadyRunningError
    SCHEDULER_AVAILABLE = True
except ImportError:
    print("Warning: APScheduler not installed. Using a minimal scheduler implementation.")
    SCHEDULER_AVAILABLE = False
    # Create stub exception for compatibility
    class SchedulerAlreadyRunningError(Exception):
        pass

class MinimalScheduler:
    """Minimal scheduler implementation when APScheduler is not available"""
    def __init__(self):
        self.logger = logging.getLogger("ai-assistant.minimal-scheduler")
        self.jobs = {}
        self.running = False
        self._task = None
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            return  # Already running, do nothing
            
        self.running = True
        self._task = asyncio.create_task(self._run())
        self.logger.info("Minimal scheduler started")
    
    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                now = datetime.now()
                # Check for jobs to run
                jobs_to_run = []
                jobs_to_remove = []
                
                for job_id, job in self.jobs.items():
                    if job["run_date"] <= now:
                        jobs_to_run.append(job)
                        # If not recurring, mark for removal
                        if not job.get("interval"):
                            jobs_to_remove.append(job_id)
                        else:
                            # Update run_date for next execution
                            job["run_date"] = now + timedelta(seconds=job["interval"])
                
                # Remove completed non-recurring jobs
                for job_id in jobs_to_remove:
                    del self.jobs[job_id]
                
                # Run due jobs
                for job in jobs_to_run:
                    try:
                        asyncio.create_task(job["func"](*job["args"]))
                    except Exception as e:
                        self.logger.error(f"Error running job {job['id']}: {str(e)}")
                
                # Sleep for a short time before checking again
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(5)  # Sleep longer on error
    
    def add_job(self, func, trigger, args=None, id=None, replace_existing=False):
        """Add a job to the scheduler"""
        job_id = id or str(uuid.uuid4())
        
        if job_id in self.jobs and not replace_existing:
            return
        
        # Handle different trigger types
        if isinstance(trigger, dict) and trigger.get("run_date"):
            run_date = trigger["run_date"]
        else:
            # Default to running soon
            run_date = datetime.now() + timedelta(seconds=5)
        
        # Handle interval trigger
        interval = None
        if hasattr(trigger, "interval") and trigger.interval:
            interval = trigger.interval
        
        self.jobs[job_id] = {
            "id": job_id,
            "func": func,
            "args": args or (),
            "run_date": run_date,
            "interval": interval
        }
    
    def remove_job(self, job_id):
        """Remove a job from the scheduler"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()


class TaskScheduler:
    """Scheduler for time-based tasks with database persistence"""
    
    def __init__(self, database, bot_registry, notification_service):
        self.database = database
        self.bot_registry = bot_registry
        self.notification_service = notification_service
        self._initialized = False
        
        # Initialize scheduler based on availability
        if SCHEDULER_AVAILABLE:
            self.scheduler = AsyncIOScheduler()
        else:
            self.scheduler = MinimalScheduler()
            
        self.logger = logging.getLogger("ai-assistant.task-scheduler")
    
    async def initialize(self):
        """Initialize the scheduler and load persisted tasks"""
        # Skip if already initialized
        if self._initialized:
            self.logger.info("Task Scheduler already initialized, skipping")
            return
            
        self.logger.info("Initializing Task Scheduler")
        
        try:
            # Start the scheduler
            try:
                self.scheduler.start()
                self.logger.info("Scheduler started successfully")
            except SchedulerAlreadyRunningError:
                self.logger.warning("Scheduler is already running, continuing with existing scheduler")
            
            # Load persisted tasks from database
            await self.load_persisted_tasks()
            
            self._initialized = True
            self.logger.info("Task Scheduler initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing task scheduler: {str(e)}", exc_info=True)
            raise
    
    async def load_persisted_tasks(self):
        """Load tasks from database and schedule them"""
        try:
            tasks = await self.database.get_all_tasks()
            scheduled_count = 0
            
            for task in tasks:
                try:
                    # Parse task data
                    task_id = task['id']
                    execute_at = datetime.fromisoformat(task['execute_at'])
                    now = datetime.now()
                    
                    # Skip tasks that are too old
                    if not task['recurring'] and execute_at < now - timedelta(hours=1):
                        self.logger.info(f"Skipping old task {task_id} scheduled for {execute_at}")
                        continue
                    
                    # For missed one-time tasks, execute them now if they're recent
                    if not task['recurring'] and execute_at < now:
                        execute_at = now + timedelta(seconds=5)  # Give a small buffer
                    
                    # Schedule the task
                    await self.schedule_task_internal(
                        task_id=task_id,
                        task_type=task['task_type'],
                        bot_id=task['bot_id'],
                        user_id=task['user_id'],
                        execute_at=execute_at,
                        params=json.loads(task['params']),
                        recurring=bool(task['recurring']),
                        interval=task['interval']
                    )
                    scheduled_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error loading task {task.get('id')}: {str(e)}", exc_info=True)
            
            self.logger.info(f"Loaded {scheduled_count} tasks from database")
        except Exception as e:
            self.logger.error(f"Error loading tasks from database: {str(e)}", exc_info=True)
    
    async def schedule_task(
        self, 
        task_type: str, 
        bot_id: str,
        user_id: str,
        execute_at: datetime, 
        params: Dict[str, Any],
        recurring: bool = False,
        interval: Optional[int] = None
    ) -> str:
        """
        Schedule a task to be executed at a specific time
        
        Args:
            task_type: Type of task to execute
            bot_id: ID of the bot that will execute the task
            user_id: ID of the user the task is for
            execute_at: When to execute the task
            params: Parameters for the task
            recurring: Whether this is a recurring task
            interval: Interval in seconds (for recurring tasks)
            
        Returns:
            Task ID
        """
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Schedule the task
        await self.schedule_task_internal(
            task_id=task_id,
            task_type=task_type,
            bot_id=bot_id,
            user_id=user_id,
            execute_at=execute_at,
            params=params,
            recurring=recurring,
            interval=interval
        )
        
        return task_id
    
    async def schedule_task_internal(
        self, 
        task_id: str,
        task_type: str,
        bot_id: str, 
        user_id: str,
        execute_at: datetime,
        params: Dict[str, Any],
        recurring: bool = False,
        interval: Optional[int] = None
    ):
        """Internal method to schedule a task"""
        # Store task in database for persistence
        await self.database.store_task(
            task_id=task_id,
            user_id=user_id,
            bot_id=bot_id,
            task_type=task_type,
            execute_at=execute_at.isoformat(),
            params=json.dumps(params),
            recurring=recurring,
            interval=interval
        )
        
        # Create job in scheduler
        if recurring and interval:
            if SCHEDULER_AVAILABLE:
                self.scheduler.add_job(
                    self.execute_task,
                    IntervalTrigger(seconds=interval, start_date=execute_at),
                    args=[task_id, task_type, bot_id, user_id, params],
                    id=task_id,
                    replace_existing=True
                )
            else:
                # Minimal scheduler implementation
                trigger = {"run_date": execute_at, "interval": interval}
                self.scheduler.add_job(
                    self.execute_task,
                    trigger,
                    args=[task_id, task_type, bot_id, user_id, params],
                    id=task_id,
                    replace_existing=True
                )
        else:
            if SCHEDULER_AVAILABLE:
                self.scheduler.add_job(
                    self.execute_task,
                    DateTrigger(run_date=execute_at),
                    args=[task_id, task_type, bot_id, user_id, params],
                    id=task_id,
                    replace_existing=True
                )
            else:
                # Minimal scheduler implementation
                trigger = {"run_date": execute_at}
                self.scheduler.add_job(
                    self.execute_task,
                    trigger,
                    args=[task_id, task_type, bot_id, user_id, params],
                    id=task_id,
                    replace_existing=True
                )
    
    async def execute_task(
        self, 
        task_id: str, 
        task_type: str, 
        bot_id: str,
        user_id: str,
        params: Dict[str, Any]
    ):
        """Execute a scheduled task"""
        self.logger.info(f"Executing task {task_id} of type {task_type}")
        
        try:
            # Update last executed time
            await self.database.update_task_execution_time(
                task_id, 
                datetime.now().isoformat()
            )
            
            # Special handling for notification delivery task
            if task_type == "deliver_notification" and bot_id == "notification_service":
                notification_id = params.get("notification_id")
                if notification_id:
                    await self.notification_service.deliver_scheduled_notification(notification_id)
                return
            
            # For regular tasks, get the bot that handles this task type
            bot = self.bot_registry.get_bot(bot_id)
            if not bot:
                self.logger.error(f"Bot {bot_id} not found for task {task_id}")
                return
            
            # Execute the task
            result = await bot.execute_task(task_type, params)
            
            # Handle any notifications that came from task execution
            if result.get("notifications"):
                for notification in result["notifications"]:
                    await self.notification_service.send_notification(
                        user_id=user_id,
                        message=notification["message"],
                        source_bot_id=bot_id,
                        metadata=notification.get("metadata")
                    )
            
            # If task was one-time, remove from database after execution
            task = await self.database.get_task(task_id)
            if task and not task.get("recurring"):
                await self.database.remove_task(task_id)
                
            self.logger.info(f"Task {task_id} execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}", exc_info=True)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        try:
            # Remove from scheduler
            self.scheduler.remove_job(task_id)
            
            # Remove from database
            await self.database.remove_task(task_id)
            
            self.logger.info(f"Task {task_id} cancelled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {str(e)}")
            return False
    
    async def get_upcoming_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming tasks for a user"""
        try:
            tasks = await self.database.get_user_tasks(user_id)
            
            # Sort by execute_at
            tasks.sort(key=lambda t: datetime.fromisoformat(t["execute_at"]))
            
            # Limit the number of results
            return tasks[:limit]
        except Exception as e:
            self.logger.error(f"Error getting upcoming tasks: {str(e)}")
            return []
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if not self._initialized:
            return
            
        self.logger.info("Shutting down Task Scheduler")
        try:
            self.scheduler.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down scheduler: {str(e)}")