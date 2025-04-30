from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from auth.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")

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

    user = relationship("User", back_populates="seo_file_records")

class PPCFile(Base):
    __tablename__ = "ppc_file_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    uuid = Column(String)  
    upload_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ppc_file_records")