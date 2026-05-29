from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pandas as pd
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)
    
database_url = config["database"]["DATABASE_URL"]
engine = create_engine(database_url)
metadata = MetaData()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base(metadata=metadata)
Base.metadata.create_all(engine)

def get_engagement_data(db_session, customer_id: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Get customer engagement data for the specified period
    
    Args:
        db_session: SQLAlchemy session object
        customer_id (str): The customer ID to retrieve data for
        start_date (datetime): Start date for the data retrieval
        end_date (datetime): End date for the data retrieval

    Returns:
        pd.DataFrame: DataFrame containing engagement data    
    """
    engagement_sql = text("""
        SELECT 
          customer_id,
          course_type,
          course_title,
          SUM(view_time) AS total_viewtime
        FROM user_engage
        WHERE customer_id = :cust_id
          AND date_viewed BETWEEN :start_date AND :end_date
        GROUP BY
          customer_id,
          course_type,
          course_title
    """)
    
    result = db_session.execute(
        engagement_sql,
        {
            "cust_id": customer_id,
            "start_date": start_date,
            "end_date": end_date
        }
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_last_active_date(db_session, customer_id: str) -> Optional[datetime]:
    """Get the customer's last active date"""
    last_active_sql = text("""
        SELECT 
          MAX(date_viewed) AS last_active
        FROM user_engage
        WHERE customer_id = :cust_id
    """)
    
    result = db_session.execute(
        last_active_sql,
        {"cust_id": customer_id}
    )
    return result.scalar_one_or_none()

def get_profile_data(db_session, customer_id: str) -> pd.DataFrame:
    """
    Get customer profile data
    
    Args:
        db_session: SQLAlchemy session object
        customer_id (str): The customer ID to retrieve data for 
    
    Returns:
        pd.DataFrame: DataFrame containing profile data

    """
    profile_sql = text("""
        SELECT 
          *
        FROM user_profiles
        WHERE customer_id = :cust_id
    """)
    
    result = db_session.execute(
        profile_sql,
        {"cust_id": customer_id}
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())

def get_feedback_data(db_session, customer_id: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Get customer feedback data for the specified period
    
    Args:
        db_session: SQLAlchemy session object
        customer_id (str): The customer ID to retrieve data for
        start_date (datetime): Start date for the data retrieval
        end_date (datetime): End date for the data retrieval

    Returns:
        pd.DataFrame: DataFrame containing feedback data
    """
    feedback_sql = text("""
        SELECT 
          customer_id,
          course_type,
          course_title,
          answer,
          date_created
        FROM user_feedback
        WHERE customer_id = :cust_id
          AND date_created BETWEEN :start_date AND :end_date
    """)
    
    result = db_session.execute(
        feedback_sql,
        {
            "cust_id": customer_id,
            "start_date": start_date,
            "end_date": end_date
        }
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def get_customer_analytics(customer_id: str, days_back: int = 7, end_date: Optional[str] = None, config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Retrieve comprehensive customer analytics data
    
    Args:
        customer_id (str): The customer ID to analyze
        days_back (int): Number of days to look back for engagement/feedback data (default: 7)
        end_date (str, optional): End date in YYYY-MM-DD format. If None, uses current date
        config_path (str): Path to the config.yaml file
    
    Returns:
        Dict containing engagement data, last active date, profile data, and feedback data
    """
    try:
        # Parse end_date or use current date
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        else:
            end_dt = datetime.now().replace(hour=23, minute=59, second=59)
        
        start_dt = end_dt - timedelta(days=days_back)
        
        # Setup database connection
        db_session = SessionLocal()
        
        # Get all data
        engagement_data = get_engagement_data(db_session, customer_id, start_dt, end_dt)
        last_active_date = get_last_active_date(db_session, customer_id)
        profile_data = get_profile_data(db_session, customer_id)
        feedback_data = get_feedback_data(db_session, customer_id, start_dt, end_dt)
        
        db_session.close()
        
        return {
            "customer_id": customer_id,
            "analysis_period": {
                "start_date": start_dt,
                "end_date": end_dt,
                "days_analyzed": days_back
            },
            "profile_data": profile_data.to_dict('records') if not profile_data.empty else [],
            "last_active_date": last_active_date if last_active_date else None,
            "engagement_data": engagement_data.to_dict('records') if not engagement_data.empty else [],
            "feedback_data": feedback_data.to_dict('records') if not feedback_data.empty else []
        }
        
    except Exception as e:
        return {"error": f"Failed to retrieve customer analytics: {str(e)}"}
