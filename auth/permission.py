from datetime import datetime

def get_default_permissions(role: str = "user"):
    if role == "prime":
        return {
                "seo_csv": 20,
                "ppc_csv": 20,
                "seo_keywords": 50,
                "ppc_keywords": 50,
                "seo_cluster": 20,
                "ppc_cluster": 20,
                "social_media": 20,
        }
    elif role == "admin":
        return {
            "seo_csv": 100,
            "ppc_csv": 100,
            "seo_keywords": 100,
            "ppc_keywords": 100,
            "seo_cluster": 100,
            "ppc_cluster": 100,
            "social_media": 100,
        }
    else:  # normal user
        return {
            "seo_csv": 5,
            "ppc_csv": 5,
            "seo_keywords": 10,
            "ppc_keywords": 10,
            "seo_cluster": 10,
            "ppc_cluster": 10,
            "social_media": 10,
        }