from auth.models import SEOCSV, PPCCSV, SEOKeywords, PPCKeywords, SEOCluster, PPCCluster, SocialMedia, SEOFile, SocialMediaFile, Contentgeneration
from auth.permission import get_default_permissions
from datetime import datetime, timedelta
from fastapi import  HTTPException
from sqlalchemy.orm import Session
from auth.models import User

def create_permissions_for_user(new_user, db: Session):
    # Get default permissions based on the user's role
    default_permissions = get_default_permissions(role=new_user.role)
    
    try:
        # Iterate over the default permissions and create permission entries
        for api_name, call_limit in default_permissions.items():
            try:
                if api_name == "ppc_cluster":
                    permission = PPCCluster(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        total_tokens=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "social_media":
                    permission = SocialMedia(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        total_tokens=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "seo_csv":
                    permission = SEOCSV(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        file_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "ppc_csv":
                    permission = PPCCSV(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        file_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "seo_keywords":
                    permission = SEOKeywords(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "seo_cluster":
                    permission = SEOCluster(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        total_tokens=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "ppc_keywords":
                    permission = PPCKeywords(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)     
                
                # elif api_name == "seo_file":
                #     # Assuming you have a model for SEOFile, add it here
                #     permission = SEOFile(
                #         user_id=new_user.id,
                #         call_limit=call_limit,
                #         call_count=0,
                #         last_reset=datetime.utcnow()
                #     )
                #     db.add(permission)
                elif api_name == "social_media_file":
                    permission = SocialMediaFile(
                        user_id=new_user.id,
                        call_limit=call_limit, 
                        last_reset = datetime.utcnow()
                    )
                    db.add(permission)

                elif api_name == "content_generation":
                    permission = Contentgeneration(
                        user_id=new_user.id,
                        call_limit=call_limit,
                        call_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)    

            except Exception as e:
                        # Handle errors for each specific API insertion
                        db.rollback()  # Rollback the transaction if error occurs
                        raise HTTPException(status_code=500, detail=f"Error while setting permissions for {api_name}: {str(e)}")   

            db.commit()

    except Exception as e:
        # Handle any other errors that occur during permission creation
        db.rollback()  # Rollback the entire transaction if any error occurs
        raise HTTPException(status_code=500, detail=f"Error while creating permissions for user: {str(e)}")     
    
def update_permissions_for_user(user: User, db: Session):

    default_permissions = get_default_permissions(role=user.role)

    for api_name, call_limit in default_permissions.items():
        try:
            if api_name == "ppc_cluster":
                # Check if the permission already exists for this user
                permission = db.query(PPCCluster).filter(PPCCluster.user_id == user.id).first()
                if permission:
                    # Update existing permission
                    # permission.call_limit = call_limit
                    continue
                else:
                    # Create new permission if it doesn’t exist
                    permission = PPCCluster(
                        user_id=user.id,
                        call_limit=call_limit,
                        call_count=0,
                        total_tokens=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)
            elif api_name == "content_generation":
                permission = db.query(Contentgeneration).filter(Contentgeneration.user_id == user.id).first()
                if permission:
                    # Update existing permission
                    # permission.call_limit = call_limit
                    continue
                else:
                    # Create new permission if it doesn’t exist
                    permission = Contentgeneration(
                        user_id=user.id,
                        call_limit=call_limit,
                        call_count=0,
                        last_reset=datetime.utcnow()
                    )
                    db.add(permission)
            # Add similar blocks for other APIs as needed
        except Exception as e:
            # Rollback on error and raise an exception with details
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error while setting permission for {api_name}: {str(e)}")
    
    # Commit all changes if no errors occur
    db.commit()    