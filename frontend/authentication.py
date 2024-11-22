# Add this helper function at the top level
def get_user_specific_key(base_key: str, user_id: str) -> str:
    return f"user_{user_id}_{base_key}"