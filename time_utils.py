from datetime import datetime, timedelta, timezone

def convert_utc_to_local(utc_time):
    """Chuyển đổi thời gian UTC thành thời gian địa phương (UTC+7)"""
    if not utc_time:
        return None
    
    # Đảm bảo utc_time có thông tin múi giờ
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    
    # Chuyển sang múi giờ Việt Nam (UTC+7)
    vietnam_tz = timezone(timedelta(hours=7))
    local_time = utc_time.astimezone(vietnam_tz)
    
    return local_time

def convert_local_to_utc(local_time):
    """Chuyển đổi thời gian địa phương thành UTC"""
    if not local_time:
        return None
        
    # Nếu thời gian chưa có thông tin múi giờ, gán múi giờ Việt Nam
    if local_time.tzinfo is None:
        vietnam_tz = timezone(timedelta(hours=7))
        local_time = local_time.replace(tzinfo=vietnam_tz)
    
    # Chuyển sang UTC
    utc_time = local_time.astimezone(timezone.utc)
    
    # Bỏ thông tin múi giờ để lưu vào MongoDB
    return utc_time.replace(tzinfo=None) 