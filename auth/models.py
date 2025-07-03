from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB 
from sqlalchemy.orm import relationship
from datetime import datetime
from auth.database import Base
from enum import Enum as PyEnum
from settings.app_intergations.app_intergations_model import ProviderEnum

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  
    role = Column(String, default="user")
    oAuthId = Column(String, unique=True, nullable=True)
    image_url = Column(String, nullable=True)

    # Relationship to permissions
    permissions = relationship("UserPermission", back_populates="user")
    files = relationship("FileStorage", back_populates="user")
    social_media_records = relationship("SocialMedia", back_populates="user")
    seo_csv_records = relationship("SEOCSV", back_populates="user")
    ppc_csv_records = relationship("PPCCSV", back_populates="user")
    seo_keyword_records = relationship("SEOKeywords", back_populates="user")
    ppc_keyword_records = relationship("PPCKeywords", back_populates="user")    
    seo_cluster_records = relationship("SEOCluster", back_populates="user")
    ppc_cluster_records = relationship("PPCCluster", back_populates="user")
    seo_file_records = relationship("SEOFile", back_populates="user")
    ppc_file_records = relationship("PPCFile", back_populates="user")
    SocialMedia_file_records = relationship("SocialMediaFile", back_populates="user")
    linkedin_posts = relationship("LinkedinPost", back_populates="user")
    facebook_posts = relationship("FacebookPost", back_populates="user")
    twitter_posts = relationship("TwitterPost", back_populates="user")
    content_generation_records = relationship("Contentgeneration", back_populates="user")
    content_generation_file_records = relationship("ContentgenerationFile", back_populates="user")
    # content_generation_dropdown = relationship("ContentgenerationDropdown", back_populates="user")
    source_file_records = relationship("SourceFileContent", back_populates="user")
    integrations_auth = relationship("Integration", back_populates="user", cascade="all, delete-orphan")
    # spreadsheet_data_record = relationship("SpreadSheet", back_populates="user")
    



class UserPermission(Base):
    __tablename__ = "user_permission"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_name = Column(String)
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="permissions")

class FileStorage(Base):
    __tablename__ = "file_storage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="files")

class SEOCSV(Base):
    __tablename__ = "seo_csv"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer)
    call_count = Column(Integer, default=0)
    file_count = Column(Integer)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="seo_csv_records")

class PPCCSV(Base):
    __tablename__ = "ppc_csv"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer)
    call_count = Column(Integer, default=0)
    file_count = Column(Integer)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ppc_csv_records")

class SEOKeywords(Base):
    __tablename__ = "seo_keywords"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="seo_keyword_records")

class PPCKeywords(Base):
    __tablename__ = "ppc_keywords"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ppc_keyword_records")

class SEOCluster(Base):
    __tablename__ = "seo_cluster"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="seo_cluster_records")

class PPCCluster(Base):
    __tablename__ = "ppc_cluster"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ppc_cluster_records")

class SocialMedia(Base):
    __tablename__ = "social_media"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    file_count = Column(Integer)
    total_tokens = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="social_media_records")
   
class SEOFile(Base):
    __tablename__ = "seo_file_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    upload_time = Column(DateTime, default=datetime.utcnow)
    json_data = Column(JSONB)

    user = relationship("User", back_populates="seo_file_records")

class PPCFile(Base):
    __tablename__ = "ppc_file_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    upload_time = Column(DateTime, default=datetime.utcnow)
    json_data = Column(JSONB)

    user = relationship("User", back_populates="ppc_file_records")

class SocialMediaFile(Base):    
    __tablename__ = "socialmedia_file_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    last_reset = Column(DateTime, default=datetime.utcnow)
    call_limit = Column(Integer, default=15)
    call_count = Column(Integer, default= 0)
    linkedIn_post = Column(JSONB)
    facebook_post = Column(JSONB)
    twitter_post = Column(JSONB)

    user = relationship("User", back_populates="SocialMedia_file_records")
    linkedin_posts = relationship("LinkedinPost", back_populates="linkedinfile")#), cascade="all, delete-orphan")
    facebook_posts = relationship("FacebookPost", back_populates="facebookfile")#, cascade="all, delete-orphan")
    twitter_posts = relationship("TwitterPost", back_populates="twitterfile")#, cascade="all, delete-orphan")

class LinkedinPost(Base):
    __tablename__ = "linkedin_posts"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("socialmedia_file_data.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_time = Column(DateTime, default=datetime.utcnow)
    content = Column(JSONB)
    image_id = Column(String, nullable=True)
    post_id = Column(String) 
    copy_uuid = Column(String) 
    time_zone = Column(JSONB, nullable=True)  
    

    linkedinfile = relationship("SocialMediaFile", back_populates="linkedin_posts", passive_deletes=True)
    user = relationship("User", back_populates="linkedin_posts")

class FacebookPost(Base):
    __tablename__ = "facebook_posts"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("socialmedia_file_data.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_time = Column(DateTime, default=datetime.utcnow)
    content = Column(JSONB)
    image_id = Column(String, nullable=True)
    post_id = Column(String) 
    copy_uuid = Column(String) 
    time_zone = Column(JSONB, nullable=True)

    facebookfile = relationship("SocialMediaFile", back_populates="facebook_posts", passive_deletes=True)
    user = relationship("User", back_populates="facebook_posts")

class TwitterPost(Base):
    __tablename__ = "twitter_posts"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("socialmedia_file_data.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_time = Column(DateTime, default=datetime.utcnow)
    content = Column(JSONB)
    image_id = Column(String, nullable=True)
    post_id = Column(String) 
    copy_uuid = Column(String) 
    time_zone = Column(JSONB, nullable=True)

    twitterfile = relationship("SocialMediaFile", back_populates="twitter_posts", passive_deletes=True)
    user = relationship("User", back_populates="twitter_posts")

class Contentgeneration(Base):
    __tablename__ = "content_generation"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    call_limit = Column(Integer)
    call_count = Column(Integer, default=0)
    file_count = Column(Integer)
    total_tokens = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="content_generation_records")

class ContentgenerationFile(Base):
    __tablename__ = "content_generation_file_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    last_reset = Column(DateTime, default=datetime.utcnow)
    content_type = Column(String)
    content_data = Column(JSONB)

    user = relationship("User", back_populates="content_generation_file_records")   

class SourceFileCategory(PyEnum):
    IDEAL_CUSTOMER_PROFILE = "Ideal Customer Profile"
    BUYER_PERSONA = "Buyer Persona"
    TONE_OF_VOICE = "Tone of voice"
    BRAND_IDENTITY = "Brand Identity"
    OFFERING = "Offering"
    COMMON_PAIN_POINTS = "Common Pain Points"
    VALUE_PROPOSITION = "Value Proposition"

class SourceFileContent(Base):
    __tablename__ = "SourceFileContent"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    uuid_id = Column(String, unique=True, nullable=False)
    category = Column(Enum(SourceFileCategory), nullable=False, index=True)
    extracted_text = Column(Text, nullable=True)
    file_name = Column(String, nullable=False)
    file_data = Column(JSON, nullable=True) 
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="source_file_records")

class Integration(Base):
    __tablename__ = "integrations_apps"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider      = Column(Enum(ProviderEnum), nullable=False)
    access_token  = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at    = Column(DateTime, nullable=True)
    scope         = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    selected_site = Column(String, nullable=True)

    user = relationship("User", back_populates="integrations_auth")

# class BrandedKeywords(Base):
#     __tablename__ = "branded_keywords"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     keywords = Column(String, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)

#     user = relationship("User", back_populates="branded_keywords_records")   

# class ContentgenerationDropdown(Base):
#     __tablename__ = "content_generation_dropdown"

#     id = Column(Integer, primary_key=True, index=True)
#     content_type = Column(String, nullable=False)

#     user = relationship("User", back_populates="content_generation_file_records")    

# class SpreadSheet(Base):
#     __tablename__ = "spreadsheet_data"
    
#     id = Column(Integer,primary_key=True, index=True)
#     uuid = Column(String)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     spreadsheet_id = Column(String, nullable=False)
#     spreadsheet_name = Column(String)
#     spreadsheet_url = Column(String)
    
#     user = relationship("User", back_populates="spreadsheet_data_record")