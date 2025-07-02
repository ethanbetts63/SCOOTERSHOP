                                  

def admin_parse_booking_request_flags(request_post_data):
    #--
    selected_profile_id = request_post_data.get('selected_profile_id')
    selected_motorcycle_id = request_post_data.get('selected_motorcycle_id')
    create_new_profile = request_post_data.get('create_new_profile') == 'true'                          
    create_new_motorcycle = request_post_data.get('create_new_motorcycle') == 'true'                          

    return {
        'selected_profile_id': int(selected_profile_id) if selected_profile_id else None,
        'selected_motorcycle_id': int(selected_motorcycle_id) if selected_motorcycle_id else None,
        'create_new_profile': create_new_profile,
        'create_new_motorcycle': create_new_motorcycle,
    }