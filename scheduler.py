import threading
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models import db, Website, Schedule, ScrapeLog
from scraper import scrape_website


class SchedulerManager:
    """Manages scheduled scraping tasks"""
    
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.jobs = {}
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Scheduler stopped")
    
    def add_job(self, schedule_id):
        """Add a scheduled job"""
        with self.app.app_context():
            schedule = Schedule.query.get(schedule_id)
            if not schedule:
                return
            
            if schedule.id in self.jobs:
                self.remove_job(schedule.id)
            
            job = self.scheduler.add_job(
                func=self._run_scrape,
                trigger=IntervalTrigger(seconds=schedule.interval_seconds),
                args=[schedule.website_id],
                id=f'scrape_{schedule.id}',
                name=f'Scrape {schedule.website.name}',
                replace_existing=True
            )
            
            self.jobs[schedule.id] = job
            print(f"Added scheduled job for {schedule.website.name}")
    
    def remove_job(self, schedule_id):
        """Remove a scheduled job"""
        if schedule_id in self.jobs:
            self.scheduler.remove_job(self.jobs[schedule_id].id)
            del self.jobs[schedule_id]
            print(f"Removed scheduled job {schedule_id}")
    
    def _run_scrape(self, website_id):
        """Internal method to run scrape"""
        with self.app.app_context():
            try:
                result = scrape_website(website_id)
                
                # Update schedule stats
                schedule = Schedule.query.filter_by(website_id=website_id).first()
                if schedule:
                    schedule.last_run = datetime.utcnow()
                    schedule.next_run = datetime.utcnow() + timedelta(seconds=schedule.interval_seconds)
                    schedule.total_runs += 1
                    if result['success']:
                        schedule.successful_runs += 1
                    db.session.commit()
                    
            except Exception as e:
                print(f"Scheduled scrape error: {e}")
                db.session.rollback()


# Global scheduler instance
scheduler_manager = None


def init_scheduler(app):
    """Initialize scheduler with app"""
    global scheduler_manager
    scheduler_manager = SchedulerManager(app)
    return scheduler_manager


def create_schedule(website_id, interval_seconds=3600):
    """Create a new schedule for a website"""
    schedule = Schedule(
        website_id=website_id,
        interval_seconds=interval_seconds,
        is_active=True,
        next_run=datetime.utcnow() + timedelta(seconds=interval_seconds)
    )
    db.session.add(schedule)
    db.session.commit()
    
    if scheduler_manager:
        scheduler_manager.add_job(schedule.id)
    
    return schedule


def delete_schedule(schedule_id):
    """Delete a schedule"""
    schedule = Schedule.query.get(schedule_id)
    if schedule:
        if scheduler_manager:
            scheduler_manager.remove_job(schedule_id)
        db.session.delete(schedule)
        db.session.commit()


def update_schedule(schedule_id, interval_seconds=None, is_active=None):
    """Update a schedule"""
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return None
    
    if interval_seconds is not None:
        schedule.interval_seconds = interval_seconds
    
    if is_active is not None:
        schedule.is_active = is_active
    
    db.session.commit()
    
    # Update scheduler
    if scheduler_manager:
        if is_active and schedule.is_active:
            scheduler_manager.add_job(schedule.id)
        elif not is_active:
            scheduler_manager.remove_job(schedule_id)
        else:
            # Recreate job with new interval
            scheduler_manager.remove_job(schedule_id)
            scheduler_manager.add_job(schedule.id)
    
    return schedule


def run_all_schedules():
    """Manually run all active schedules"""
    schedules = Schedule.query.filter_by(is_active=True).all()
    
    results = []
    for schedule in schedules:
        try:
            result = scrape_website(schedule.website_id)
            results.append({
                'website': schedule.website.name,
                'result': result
            })
        except Exception as e:
            results.append({
                'website': schedule.website.name,
                'error': str(e)
            })
    
    return results
