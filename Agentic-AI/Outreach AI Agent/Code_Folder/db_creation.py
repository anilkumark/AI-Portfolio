from sqlalchemy import create_engine, Column, String, DateTime, MetaData, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml
import pandas as pd

# Open and load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

database_url = config["database"]["DATABASE_URL"]
metadata = MetaData()
Base = declarative_base(metadata=metadata)

engine = create_engine(database_url)

# User profile storage
class UserProfile(Base):
    __tablename__ = "user_profiles"
    customer_id = Column(String, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    customer_email = Column(String, index=True)
    phone_number = Column(String, index=True)
    date_joined = Column(DateTime, index=True)
    is_material_downloaded = Column(Boolean, index=True)
    is_path_created = Column(Boolean, index=True)
    field_of_interest = Column(String, index=True)
    profession = Column(String, index=True)

    
class UserEngagement(Base):
    __tablename__ = "user_engage"
    engage_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    course_id = Column(String, index=True)
    course_title = Column(String, index=True)
    course_type = Column(String, index=True)
    view_time = Column(Float, index=True)
    date_viewed = Column(DateTime, index=True)

    

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    feedback_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    course_id = Column(String, index=True)
    course_title = Column(String, index=True)
    course_type = Column(String, index=True)
    feedback_questions_id = Column(String, index=True)
    answer = Column(String, index=True)
    date_created = Column(DateTime)


class CallHistory(Base):
    __tablename__ = "call_history"
    campaign_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    customer_name = Column(String, index=True)
    customer_email = Column(String, index=True)
    customer_phone = Column(String, index=True)
    campaign_started_at = Column(DateTime, index=True)
    campaign_completed_at = Column(DateTime, index=True)
    campaign_status = Column(String, index=True)  # completed, failed, in_progress
    
    # Call details
    call_advice = Column(Text)
    conversation_id = Column(String, index=True)
    call_sid = Column(String, index=True)
    call_status = Column(String, index=True)  # initiated, in-progress, done, failed
    call_outcome = Column(String, index=True)  # completed, failed, did_not_pick, error
    call_initiated_at = Column(DateTime)
    call_completed_at = Column(DateTime)
    transcript = Column(Text)
    call_analysis = Column(Text)
    
    # Email details  
    email_sent = Column(Boolean, index=True)
    email_subject = Column(String, index=True)
    email_content = Column(Text)
    email_message_id = Column(String, index=True)
    email_sent_at = Column(DateTime)
    email_status = Column(String, index=True)  # success, failed
    
    # Error tracking
    errors = Column(Text)  # JSON string of errors




SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 2) Create tables
Base.metadata.create_all(engine)

# 3) Define a helper to read, clean, and bulk-insert
def bulk_load(model, csv_path, parse_dates=None, dtype=None):
    """
    Reads csv_path into a DataFrame, parses dates, casts dtypes,
    and bulk-inserts into the given SQLAlchemy model.
    Only loads data if table doesn't exist or is empty.
    """
    with SessionLocal() as session:
        try:
            # Check if table has any data
            existing_count = session.query(model).count()
            if existing_count > 0:
                print(f"Table {model.__tablename__} already has {existing_count} records. Skipping data load.")
                return
        except Exception:
            # Table might not exist yet, continue with loading
            pass
    
    print(f"Loading {csv_path} into {model.__tablename__}...")
    try:
        df = pd.read_csv(csv_path, dtype=dtype, parse_dates=parse_dates)
        records = df.to_dict(orient="records")
        
        with SessionLocal() as session:
            session.bulk_insert_mappings(model, records)
            session.commit()
        print(f"Successfully inserted {len(records)} rows into {model.__tablename__}.")
        
    except Exception as e:
        print(f"Error loading data into {model.__tablename__}: {str(e)}")
        print("Continuing execution...")
 
enroll_dir= config["csv_dir"]["user_profiles"]
video_engage_dir = config["csv_dir"]["user_video_engage"]
feedback_dir = config["csv_dir"]["user_feedback"]

#UserProfile: parse datetime cols
bulk_load(
        model= UserProfile,
        csv_path = enroll_dir,
        parse_dates=["date_joined"],
        dtype={
            "customer_id": str,
            "customer_name": str,
            "customer_email": str,
            "phone_number": str,
            "is_material_downloaded": bool,
            "is_path_created": bool,    
            "field_of_interest": str,
            "profession": str
        },
    )

#UserVideoEngage
bulk_load(
        model = UserEngagement,
        csv_path = video_engage_dir,
        parse_dates=["date_viewed"],
        dtype={
            "engage_id": str,
            "customer_id": str,
            "course_id": str,
            "course_title": str,
            "course_type": str,
            "view_time": float,
        },
    )



#UserFeedback
bulk_load(
        model=UserFeedback,
        csv_path=feedback_dir,
        parse_dates=["date_created"],
        dtype={
            "feedback_id": str,
            "customer_id": str,
            "course_id": str,
            "course_title": str,
            "feedback_questions_id": str,
            "answer": str,
        },
    )



# 4) Close the session
SessionLocal.close_all()