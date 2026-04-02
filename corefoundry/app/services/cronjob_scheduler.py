"""Cronjob scheduler service using APScheduler."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from corefoundry.app.db.connection import SessionLocal
from corefoundry.app.db.models import Cronjob
from corefoundry.app.services.cronjob_executor import CronjobExecutor

logger = logging.getLogger(__name__)


class CronjobScheduler:
    """
    Scheduler service for managing and executing cronjobs.
    
    This service runs in the background and checks for active cronjobs
    every minute, executing those that are due.
    """
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.executor = CronjobExecutor(timeout=30)
        self.is_running = False
        logger.info("CronjobScheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Schedule the main task to run every minute
            self.scheduler.add_job(
                func=self._check_and_execute_cronjobs,
                trigger=IntervalTrigger(minutes=1),
                id="cronjob_checker",
                name="Check and execute cronjobs",
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("CronjobScheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start CronjobScheduler: {e}", exc_info=True)
            raise
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            # Close the executor's HTTP client
            asyncio.create_task(self.executor.close())
            self.is_running = False
            logger.info("CronjobScheduler shutdown successfully")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}", exc_info=True)
    
    async def _check_and_execute_cronjobs(self):
        """
        Check for active cronjobs and execute those that are due.
        
        This method is called every minute by the scheduler.
        """
        db: Session = SessionLocal()
        try:
            # Get all active cronjobs
            active_cronjobs = db.query(Cronjob).filter(
                Cronjob.is_active == True
            ).all()
            
            if not active_cronjobs:
                logger.debug("No active cronjobs found")
                return
            
            logger.info(f"Checking {len(active_cronjobs)} active cronjobs")
            
            now = datetime.utcnow()
            executed_count = 0
            
            for cronjob in active_cronjobs:
                try:
                    # Check if this cronjob is due to run
                    if self._is_due(cronjob, now):
                        logger.info(f"Executing cronjob {cronjob.id} ({cronjob.name})")
                        await self.executor.execute_cronjob(cronjob, db)
                        executed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error executing cronjob {cronjob.id}: {e}", exc_info=True)
                    # Continue with next cronjob even if one fails
                    continue
            
            if executed_count > 0:
                logger.info(f"Executed {executed_count} cronjobs")
            
        except Exception as e:
            logger.error(f"Error in _check_and_execute_cronjobs: {e}", exc_info=True)
        
        finally:
            db.close()
    
    def _is_due(self, cronjob: Cronjob, now: datetime) -> bool:
        """
        Check if a cronjob is due to run.
        
        Args:
            cronjob: The Cronjob instance
            now: Current datetime
            
        Returns:
            bool: True if the cronjob should run now
        """
        # If never run before, it's due
        if not cronjob.last_run_at:
            return True
        
        # Calculate next run time based on interval
        next_run_time = cronjob.last_run_at + timedelta(minutes=cronjob.interval_minutes)
        
        # Check if it's time to run
        return now >= next_run_time


# Global scheduler instance
_scheduler_instance: Optional[CronjobScheduler] = None


def get_scheduler() -> CronjobScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CronjobScheduler()
    return _scheduler_instance


def start_scheduler():
    """Start the global scheduler instance."""
    scheduler = get_scheduler()
    scheduler.start()


def shutdown_scheduler():
    """Shutdown the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.shutdown()
        _scheduler_instance = None
