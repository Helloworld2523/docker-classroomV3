from django import template
from django.utils.safestring import mark_safe
# from .models import Count
register = template.Library()

@register.filter
def ChangDay(value):
    if value=='1':
        return 'Monday'
    if value=='2':
        return 'Tuesday'    
    if value=='3':
        return 'Wednesday'    
    if value=='4':
        return 'Thursday'    
    if value=='5':
        return 'Friday'  
    if value=='6':
        return 'Saturday'   
    if value=='7':
        return 'Sunday'   
    
# @register.filter
# def showCountRoom(q):
#     countOnline=0
#     try:
#         data_c = Count.objects.get(room_name=q.lower())
#         countOnline = data_c.sessions_total
#     except Count.DoesNotExist:
#         # Handle the case where no matching record is found
#         countOnline=0
        
#     return countOnline          

        