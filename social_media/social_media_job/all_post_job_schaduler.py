# scheduler_service.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
import atexit
import logging
from fastapi import logger
from sqlalchemy.orm import Session
from auth.models import LinkedinPost, FacebookPost, TwitterPost, Integration
from auth.auth import get_db
from social_media.social_media_job.linkedIn_job import main as publish_to_linkedin
from sqlalchemy.orm.attributes import flag_modified
import json
from settings.app_intergations.app_intergations_model import ProviderEnum
from auth.database import engine
from datetime import datetime, timezone
from dateutil.parser import isoparse
from tzlocal import get_localzone

def parse_with_local(dt_str: str):
    dt = isoparse(dt_str)          # will pick up any “+05:30” or “Z” if present
    if dt.tzinfo is None:
        # fall back to your host’s configured zone
        dt = dt.replace(tzinfo=get_localzone())
    return dt


# Move the publishing functions outside the class as standalone functions
def publish_linkedin_post_job(copy_uuid: str):
    """Standalone function to publish a scheduled LinkedIn post"""
    db = next(get_db())
    
    try:
        post = db.query(LinkedinPost).filter(LinkedinPost.copy_uuid == copy_uuid).first()
        
        access = (
        db.query(Integration)
        .filter(
            Integration.provider == ProviderEnum.LINKEDIN,
            Integration.user_id   == post.user_id
        )
        .first()
    )
        
        if not post:
            print(f"LinkedIn post {copy_uuid} not found")
            return False
        
        # Check if already published (post_id contains the platform ID from your logic)
        # if post.copy_uuid:
        #     print(f"LinkedIn post {copy_uuid} already published")
        #     return True
        
        content = post.content
        print(f"Content for LinkedIn post {copy_uuid}: {content}")
        
        content = json.loads(content) if isinstance(content, str) else content
        
        
        
        if not content:
            print(f"LinkedIn post {copy_uuid} has no content")
            return False
        # if isinstance(content, str):
        #     # If content is a string, parse it as JSON
        #     try:``
        #         content = json.loads(content)
        #     except json.JSONDecodeError:
        #         print(f"Invalid JSON content for post {copy_uuid}")
        #         return False
        # content = json.loads(content)
        
        # Build the post text from Subheadline + two line breaks + description
        # subheadline = "\n".join(content.get("Subheadline", [])) if content.get("Subheadline") else None
        description = "\n".join(content.get("discription", [])) if content.get("discription") else None 
        post_text = f"{description}"
        print(post_text)
        
        image_url = content.get('image') if content.get('image') else None
        
        # Publish to LinkedIn using your existing API
        response = publish_to_linkedin(
            access_token=access.access_token,
            post_text=post_text,    
            image_url=image_url
        )
        print(f"Response from LinkedIn API: {response}")
        linkedin_urn = response.get("id")
        if linkedin_urn:
            # Update with actual LinkedIn post ID
            Postid= linkedin_urn
            print(f"LinkedIn post ID: {Postid}")
            # db.commit()
            print(f"Successfully published LinkedIn post {copy_uuid}")
            return True
        else:
            print(f"Failed to publish LinkedIn post {copy_uuid}: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"Error publishing LinkedIn post {copy_uuid}: {str(e)}")
        return False
    finally:
        db.close()

class SocialMediaScheduler:
    def __init__(self, timezone='UTC'):
        # Configure job store to use your database
        jobstores = {
            'default': SQLAlchemyJobStore(engine=engine, tablename='apscheduler_jobs')
        }
        
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=timezone
        )
        
        # Start scheduler
        self.scheduler.start()
        
        # Ensure scheduler shuts down when app exits
        atexit.register(lambda: self.scheduler.shutdown())

    
    
    # def publish_facebook_post(self, post_id: int):
    #     """Publish a scheduled Facebook post"""
    #     db = next(get_db())
        
    #     try:
    #         post = db.query(FacebookPost).filter(FacebookPost.id == post_id).first()
            
    #         if not post:
    #             print(f"Facebook post {post_id} not found")
    #             return False
            
    #         # Check if already published
    #         if post.post_id and not post.post_id.startswith('facebook_'):
    #             print(f"Facebook post {post_id} already published")
    #             return True
            
    #         # Publish to Facebook
    #         response = publish_to_facebook(
    #             content=post.content,
    #             user_id=post.user_id,
    #             image_id=post.image_id
    #         )
            
    #         if response.get('success'):
    #             post.post_id = response.get('facebook_post_id')
    #             db.commit()
    #             print(f"Successfully published Facebook post {post_id}")
    #             return True
    #         else:
    #             print(f"Failed to publish Facebook post {post_id}: {response.get('error')}")
    #             return False
                
    #     except Exception as e:
    #         print(f"Error publishing Facebook post {post_id}: {str(e)}")
    #         return False
    #     finally:
    #         db.close()
    
    # def publish_twitter_post(self, post_id: int):
    #     """Publish a scheduled Twitter post"""
    #     db = next(get_db())
        
    #     try:
    #         post = db.query(TwitterPost).filter(TwitterPost.id == post_id).first()
            
    #         if not post:
    #             print(f"Twitter post {post_id} not found")
    #             return False
            
    #         # Check if already published
    #         if post.post_id and not post.post_id.startswith('twitter_'):
    #             print(f"Twitter post {post_id} already published")
    #             return True
            
    #         # Publish to Twitter
    #         response = publish_to_twitter(
    #             content=post.content,
    #             user_id=post.user_id,
    #             image_id=post.image_id
    #         )
            
    #         if response.get('success'):
    #             post.post_id = response.get('twitter_post_id')
    #             db.commit()
    #             print(f"Successfully published Twitter post {post_id}")
    #             return True
    #         else:
    #             print(f"Failed to publish Twitter post {post_id}: {response.get('error')}")
    #             return False
                
    #     except Exception as e:
    #         print(f"Error publishing Twitter post {post_id}: {str(e)}")
    #         return False
    #     finally:
    #         db.close()
    
    def schedule_post(self, platform: str, copy_uuid: str, schedule_time: datetime, time_zone: dict = None):
        """Schedule a post for publication"""
        try:
            job_id = f"{platform}_post_{copy_uuid}"
            time_zone = json.loads(time_zone) if isinstance(time_zone, str) else time_zone
            time_zone_name = time_zone.get('value') if time_zone else None

            # Remove existing job if exists
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Map platform to function
            platform_functions = {
                'linkedin': publish_linkedin_post_job,
                # 'facebook': self.publish_facebook_post,
                # 'twitter': self.publish_twitter_post
            }
            
            if platform not in platform_functions:
                logger.error(f"Unknown platform: {platform}")
                return False
            # run_date = parse_with_local(schedule_time)
            # print(f"Scheduling {platform} post {copy_uuid} at {run_date}")
            print(f"Schedule time: {schedule_time}")
            # Schedule the post
            self.scheduler.add_job(
                func=platform_functions[platform],
                args=[copy_uuid],
                trigger='date',
                run_date=schedule_time,
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace period
                timezone=time_zone_name if time_zone_name else 'UTC'  # Use local timezone if provided
            )
            

            print(f"Scheduled {platform} post {copy_uuid} for {schedule_time}")
            return True
            
        except Exception as e:
            print(f"Error scheduling {platform} post {copy_uuid}: {str(e)}")
            return False

    def cancel_scheduled_post(self, platform: str, copy_uuid: str):
        """Cancel a scheduled post"""
        try:
            job_id = f"{platform}_post_{copy_uuid}"
            self.scheduler.remove_job(job_id)
            print(f"Cancelled scheduled {platform} post {copy_uuid}")
            return True
        except Exception as e:
            print(f"Error cancelling {platform} post {copy_uuid}: {str(e)}")
            return False

    def reschedule_post(self, platform: str, copy_uuid: str, new_schedule_time: datetime):
        """Reschedule an existing post"""
        try:
            job_id = f"{platform}_post_{copy_uuid}"
            self.scheduler.modify_job(job_id, next_run_time=new_schedule_time)
            print(f"Rescheduled {platform} post {copy_uuid} to {new_schedule_time}")
            return True
        except Exception as e:
            print(f"Error rescheduling {platform} post {copy_uuid}: {str(e)}")
            # Try to schedule as new job if modify fails
            return self.schedule_post(platform, copy_uuid, new_schedule_time)
        
        
    def get_scheduler_status(self):
        """Get current scheduler status and job information"""
        try:
            return {
                "running": self.scheduler.running,
                "state": self.scheduler.state,
                "total_jobs": len(self.scheduler.get_jobs()),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger),
                        "function": job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
                    }
                    for job in self.scheduler.get_jobs()
                ]
            }
        except Exception as e:
            return {"error": f"Failed to get scheduler status: {str(e)}"}    
        
    def list_scheduled_posts(self):
        """List all currently scheduled posts"""
        jobs = self.scheduler.get_jobs()
        scheduled_posts = []
        
        for job in jobs:
            if job.id.endswith('_post_'):  # Our job naming pattern
                parts = job.id.split('_')
                if len(parts) >= 3:
                    platform = parts[0]
                    copy_uuid = '_'.join(parts[2:])  # Handle UUIDs with underscores
                    
                    scheduled_posts.append({
                        "platform": platform,
                        "copy_uuid": copy_uuid,
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "job_id": job.id
                    })
        
        return scheduled_posts    
    
    def initialize_existing_posts(self):
        """Initialize scheduler with existing unposted scheduled posts"""
        db = next(get_db())
        
        try:
            now = datetime.utcnow()
            print(f"Initializing existing posts at {now.isoformat()}")
            
            # Initialize LinkedIn posts
            linkedin_posts = db.query(LinkedinPost).filter(
                LinkedinPost.schedule_time > now,
                # Check if post_id is still the platform ID (not published)
                # LinkedinPost.post_id.like('linkedin_%')
            ).all()
            
            for post in linkedin_posts:
                self.schedule_post('linkedin', post.copy_uuid, post.schedule_time)
                print("Current Scheduled Jobs:", self.scheduler.get_jobs())
            
            # Initialize Facebook posts
            facebook_posts = db.query(FacebookPost).filter(
                FacebookPost.schedule_time > now,
                # FacebookPost.post_id.like('facebook_%')
            ).all()
            
            for post in facebook_posts:
                self.schedule_post('facebook', post.copy_uuid, post.schedule_time)
            
            # Initialize Twitter posts
            twitter_posts = db.query(TwitterPost).filter(
                TwitterPost.schedule_time > now,
                # TwitterPost.post_id.like('twitter_%')
            ).all()
            
            for post in twitter_posts:
                self.schedule_post('twitter', post.copy_uuid, post.schedule_time)
            
            total_posts = len(linkedin_posts) + len(facebook_posts) + len(twitter_posts)
            print(f"Initialized {total_posts} existing scheduled posts")
            
        except Exception as e:
            print(f"Error initializing existing posts: {str(e)}")
        finally:
            db.close()



# scheduler_service=SocialMediaScheduler()

# from datetime import datetime, timedelta

# copy_uuid = "d741a00189434516822454a1c0ffbdc9"
# schedule_time = datetime.utcnow() + timedelta(minutes=1)
# scheduler_service.schedule_post("linkedin", copy_uuid, schedule_time)
