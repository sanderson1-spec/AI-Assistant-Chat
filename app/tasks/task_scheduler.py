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

class TaskScheduler:
    """Scheduler for time-based tasks with database persistence"""
    
    def __init__(self, database, bot_registry, notification_service):
        self.database = database
        self.bot_registry = bot_registry
        self.notification_service = notification_service
        self._initialized = False
        self.running = False
        self._task = None
        self.jobs = {}
        self.logger = logging.getLogger("ai-assistant.task-scheduler")
        self.controller = None
    
    def set_controller(self, controller):
        """Set the central controller reference"""
        self.controller = controller
        self.logger.info("Central controller reference set in TaskScheduler")
    
    async def initialize(self):
        """Initialize the scheduler and load persisted tasks"""
        # Skip if already initialized
        if self._initialized:
            self.logger.info("Task Scheduler already initialized, skipping")
            return
            
        self.logger.info("Initializing Task Scheduler")
        
        try:
            # Load persisted tasks from database first
            await self.load_persisted_tasks()
            
            # Start the scheduler only if we successfully loaded tasks
            self.running = True
            self._task = asyncio.create_task(self._run())
            self.logger.info("Scheduler started successfully")
            
            self._initialized = True
            self.logger.info("Task Scheduler initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing task scheduler: {str(e)}", exc_info=True)
            # Don't raise the error, just log it and continue
            # This allows the application to start even if the task scheduler has issues
            self._initialized = False
            self.running = False
    
    async def load_persisted_tasks(self):
        """Load tasks from the database"""
        try:
            tasks = await self.database.get_all_tasks()
            loaded_count = 0
            
            for task in tasks:
                try:
                    # Ensure task has required fields
                    required_fields = ['id', 'user_id', 'bot_id', 'task_type', 'execute_at', 'params']
                    if not all(field in task for field in required_fields):
                        self.logger.warning(f"Task missing required fields: {task}")
                        continue
                    
                    # Parse execute_at time
                    try:
                        execute_at = datetime.fromisoformat(task['execute_at'])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid execute_at time for task {task.get('id')}")
                        continue
                    
                    # Skip old non-recurring tasks
                    if not task.get('recurring') and execute_at < datetime.now() - timedelta(hours=1):
                        self.logger.info(f"Skipping old task {task['id']} scheduled for {execute_at}")
                        continue
                    
                    # For missed one-time tasks, execute them soon
                    if not task.get('recurring') and execute_at < datetime.now():
                        execute_at = datetime.now() + timedelta(seconds=5)
                        task['execute_at'] = execute_at.isoformat()
                    
                    # Add task to jobs dictionary
                    self.jobs[task['id']] = task
                    loaded_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error loading task {task.get('id', 'unknown')}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully loaded {loaded_count} tasks from database")
            
        except Exception as e:
            self.logger.error(f"Error loading tasks from database: {str(e)}")
            # Clear any partially loaded jobs
            self.jobs = {}
    
    async def _run(self):
        """Main scheduler loop"""
        self.logger.info("Task scheduler loop starting")
        while self.running:
            try:
                now = datetime.now()
                # Check for jobs to run
                jobs_to_run = []
                jobs_to_remove = []
                
                for job_id, job in self.jobs.items():
                    try:
                        execute_at = datetime.fromisoformat(job["execute_at"])
                        if execute_at <= now:
                            jobs_to_run.append(job)
                            # If not recurring, mark for removal
                            if not job.get("recurring"):
                                jobs_to_remove.append(job_id)
                            else:
                                # Update execute_at for next execution
                                next_execution = now + timedelta(seconds=job["interval"])
                                job["execute_at"] = next_execution.isoformat()
                                # Update in database
                                await self.database.store_task(
                                    job["id"],
                                    job["user_id"],
                                    job["bot_id"],
                                    job["task_type"],
                                    job["execute_at"],
                                    job["params"],
                                    job["recurring"],
                                    job["interval"]
                                )
                    except (ValueError, KeyError) as e:
                        self.logger.error(f"Error processing job {job_id}: {str(e)}")
                        jobs_to_remove.append(job_id)
                
                # Remove completed non-recurring jobs and invalid jobs
                for job_id in jobs_to_remove:
                    if job_id in self.jobs:
                        del self.jobs[job_id]
                        try:
                            await self.database.remove_task(job_id)
                        except Exception as e:
                            self.logger.error(f"Error removing task {job_id}: {str(e)}")
                
                # Run due jobs
                for job in jobs_to_run:
                    try:
                        bot = self.bot_registry.get_bot(job["bot_id"])
                        if bot:
                            await bot.execute_task(
                                task_type=job["task_type"],
                                params=json.loads(job["params"]) if isinstance(job["params"], str) else job["params"],
                                user_id=job["user_id"]
                            )
                            # Update last execution time
                            await self.database.update_task_execution_time(
                                job["id"],
                                datetime.now().isoformat()
                            )
                        else:
                            self.logger.warning(f"Bot {job['bot_id']} not found for task {job['id']}")
                    except Exception as e:
                        self.logger.error(f"Error executing job {job['id']}: {str(e)}", exc_info=True)
                
                # Sleep for a short time before checking again
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Sleep longer on error
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.logger.info("Shutting down task scheduler")
        self.running = False
        if self._task:
            self._task.cancel()
        self._initialized = False