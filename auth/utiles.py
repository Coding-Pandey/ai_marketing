from auth.models import SEOCSV, PPCCSV, SEOKeywords, PPCKeywords, SEOCluster, PPCCluster, SocialMedia, SEOFile
from auth.permission import get_default_permissions
from datetime import datetime, timedelta
from fastapi import  HTTPException

def create_permissions_for_user(new_user, db):
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
                        total_files_count=call_limit,
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
            except Exception as e:
                        # Handle errors for each specific API insertion
                        db.rollback()  # Rollback the transaction if error occurs
                        raise HTTPException(status_code=500, detail=f"Error while setting permissions for {api_name}: {str(e)}")   

            db.commit()

    except Exception as e:
        # Handle any other errors that occur during permission creation
        db.rollback()  # Rollback the entire transaction if any error occurs
        raise HTTPException(status_code=500, detail=f"Error while creating permissions for user: {str(e)}")     
    
    