from django.contrib import admin
from .models import Classrooms,ClassScheduleCenter,Locations,LogSubjectInRoom
import datetime

from django.utils.html import escape
from django.utils.html import mark_safe 
from . import config
from django.template.loader import render_to_string
# Register your models here.
class ClassScheduleCenterInline(admin.TabularInline):
    model = ClassScheduleCenter
    list_display = ('course_no')
    exclude = ['added_by','created_at','updated_at']
    extra = 0

class ClassroomsAdmin(admin.ModelAdmin):

    list_display = ("room_name", "room_stream",'display_video',)
    list_filter = ('room_location_id',)
    search_fields=('room_name',)
    list_per_page=10
    list_editable=["room_stream",]
    exclude = ['added_by','created_at','updated_at']

    inlines = [ClassScheduleCenterInline]

    def display_video(self, obj):
        if obj.room_location_id==1:
            return render_to_string('live/vod.html', {'object': obj,'server':config.serverMedia68,'room_server':obj.room_name.lower()})
        elif  obj.room_location_id==2:
            return render_to_string('live/vod.html', {'object': obj,'server':config.serverMedia65,'room_server':obj.room_name.lower()})
        elif obj.room_location_id==3 or obj.room_location_id==5 or obj.room_location_id==7 :
            return render_to_string('live/vod.html', {'object': obj,'server':config.serverMedia66,'room_server':obj.room_name.lower()})
        elif obj.room_location_id==4:
            return render_to_string('live/vod.html', {'object': obj,'server':config.serverMedia68,'room_server':obj.room_name.lower()})
        elif obj.room_location_id==8:
            return render_to_string('live/vod.html', {'object': obj,'server':config.serverMedia67,'room_server':obj.room_name.lower()})       

    def _get_thumbnail(self, obj):
        return mark_safe(
            '<iframe width="560" height="315" src="https://www.youtube.com/embed/95wuXZi6HII" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
        )
        
    _get_thumbnail.allow_tags = True

    def _getStream(self,obj):
        #mystr = '<h3>%s</h3><br/>%s%s/playlist.m3u8' % (obj.room_name,config.serverMedia66,obj.room_name)
        if obj.room_location_id==1:
            mystr =(
                '<center><script type="text/javascript" src="//player.wowza.com/player/latest/wowzaplayer.min.js"></script>'
                '<div id="playerElement%s"  style="height:250px;width:250px"></div>'
                '<script type="text/javascript">'
                    'WowzaPlayer.create("playerElement%s",'
                    '{'
                    '"license":"PLAY1-9QhBw-ydwZk-h3bpC-mcnn3-mdpVR",'
                    '"title":"%s",'
                    '"description":"",'
                    '"sourceURL":"%s%s/playlist.m3u8",'
                    '"autoPlay":true,'
                    '"volume":"75",'
                    '"mute":true,'
                    '"loop":false,'
                    '"audioOnly":false,'
                    '"uiShowQuickRewind":true,'
                    '"uiQuickRewindSeconds":"30"'
                    '}'
                ');'
                '</script></center>'
            ) % (
                obj.room_name,
                obj.room_name,
                obj.room_name,
                config.serverMedia68,
                obj.room_name.lower()
            )
        elif obj.room_location_id==2:
            mystr =(
                '<center><script type="text/javascript" src="//player.wowza.com/player/latest/wowzaplayer.min.js"></script>'
                '<div id="playerElement%s"  style="height:250px;width:250px"></div>'
                '<script type="text/javascript">'
                    'WowzaPlayer.create("playerElement%s",'
                    '{'
                    '"license":"PLAY1-9QhBw-ydwZk-h3bpC-mcnn3-mdpVR",'
                    '"title":"%s",'
                    '"description":"",'
                    '"sourceURL":"%s%s/playlist.m3u8",'
                    '"autoPlay":true,'
                    '"volume":"75",'
                    '"mute":true,'
                    '"loop":false,'
                    '"audioOnly":false,'
                    '"uiShowQuickRewind":true,'
                    '"uiQuickRewindSeconds":"30"'
                    '}'
                ');'
                '</script></center>'
            ) % (
                obj.room_name,
                obj.room_name,
                obj.room_name,
                config.serverMedia65,
                obj.room_name.lower()
            )    
        elif obj.room_location_id==3 or obj.room_location_id==5 or obj.room_location_id==7 :
            mystr =(
                '<center><script type="text/javascript" src="//player.wowza.com/player/latest/wowzaplayer.min.js"></script>'
                '<div id="playerElement%s"  style="height:250px;width:250px"></div>'
                '<script type="text/javascript">'
                    'WowzaPlayer.create("playerElement%s",'
                    '{'
                    '"license":"PLAY1-9QhBw-ydwZk-h3bpC-mcnn3-mdpVR",'
                    '"title":"%s",'
                    '"description":"",'
                    '"sourceURL":"%s%s/playlist.m3u8",'
                    '"autoPlay":true,'
                    '"volume":"75",'
                    '"mute":true,'
                    '"loop":false,'
                    '"audioOnly":false,'
                    '"uiShowQuickRewind":true,'
                    '"uiQuickRewindSeconds":"30"'
                    '}'
                ');'
                '</script></center>'
            ) % (
                obj.room_name,
                obj.room_name,
                obj.room_name,
                config.serverMedia66,
                obj.room_name.lower()
            )            
        elif obj.room_location_id==4:
            #vjs-fluid จะจัดการเอง ถ้าเอาอองจะใช้ width และ height ได้
            #vjs-big-play-centered  ให้ปุ่ม play อยู่ตรงกลาง
            mystr =('<link href="https://unpkg.com/video.js/dist/video-js.css" rel="stylesheet">'
                    '<script src="https://unpkg.com/video.js/dist/video.js"></script>'
                    '<script src="https://unpkg.com/videojs-contrib-hls/dist/videojs-contrib-hls.js"></script>'
                    '<center><video id="%s" class="video-js vjs-fluid vjs-default-skin vjs-big-play-centered" controls preload="auto" autoplay="true" poster="https://www.dailygizmo.tv/wp-content/uploads/2017/05/y0-500x512.jpg" data-setup="{}" >'
                        '<source src="%s%s.m3u8" type="application/x-mpegURL">'
                    '</video></center>'
                    '<script>'
                        'var player = videojs("%s");'
                        #'player.play({autoplay: "false"});'
                        'player.volume(0);'
                    '</script>'
            ) % (
                obj.room_name,
                config.serverMdeia88,
                obj.room_name.lower(),  
                obj.room_name,               
            )
            #mystr='<h3>%s</h3><br/>%s%s/playlist.m3u8' % (obj.room_name,config.serverMedia66,obj.room_name)
            #print(mystr)
        elif obj.room_location_id==8:
            mystr =(
                '<center><script type="text/javascript" src="//player.wowza.com/player/latest/wowzaplayer.min.js"></script>'
                '<div id="playerElement%s"  style="height:250px;width:250px"></div>'
                '<script type="text/javascript">'
                    'WowzaPlayer.create("playerElement%s",'
                    '{'
                    '"license":"PLAY1-9QhBw-ydwZk-h3bpC-mcnn3-mdpVR",'
                    '"title":"%s",'
                    '"description":"",'
                    '"sourceURL":"%s%s/playlist.m3u8",'
                    '"autoPlay":true,'
                    '"volume":"75",'
                    '"mute":true,'
                    '"loop":false,'
                    '"audioOnly":false,'
                    '"uiShowQuickRewind":true,'
                    '"uiQuickRewindSeconds":"30"'
                    '}'
                ');'
                '</script></center>'
            ) % (
                obj.room_name,
                obj.room_name,
                obj.room_name,
                config.serverMedia67,
                obj.room_name.lower()
            )            
        elif obj.room_location_id==6 :
            mystr =('<link href="https://unpkg.com/video.js/dist/video-js.css" rel="stylesheet">'
                    '<script src="https://unpkg.com/video.js/dist/video.js"></script>'
                    '<script src="https://unpkg.com/videojs-contrib-hls/dist/videojs-contrib-hls.js"></script>'
                    '<center><video id="%s" class="video-js vjs-fluid vjs-default-skin vjs-big-play-centered" controls preload="auto" autoplay="true" poster="https://www.dailygizmo.tv/wp-content/uploads/2017/05/y0-500x512.jpg" data-setup="{}" >'
                        '<source src="%s%s.m3u8" type="application/x-mpegURL">'
                    '</video></center>'
                    '<script>'
                        'var player = videojs("%s");'
                        #'player.play({autoplay: "false"});'
                        'player.volume(0);'
                    '</script>'
            ) % (
                obj.room_name,
                #config.serverMdeia88,
                'https://vtop-playground.ml/hls_dash/',
                'master',  
                obj.room_name,               
            )
            print(mystr)
        return mark_safe(
           mystr
        )
    _getStream.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_at = datetime.datetime.now()
            obj.updated_at = datetime.datetime.now()
            # print("yes")
        else:
            obj.updated_at = datetime.datetime.now()

        # Only set added_by during the first save.
        obj.added_by = request.user.username
        return super().save_model(request, obj, form, change)

admin.site.register(Classrooms,ClassroomsAdmin)
##################



class ClassScheduleCenterAdmin(admin.ModelAdmin):
    list_display = ("course_no","course_day","time_start","time_end","room_name")
    list_per_page=25
    list_editable=["course_day","time_start","time_end","room_name"]
    exclude = ['added_by','created_at','updated_at']

    #relation คือ ฟิวในตารางนั้น__ฟิวในตารางหลัก
    search_fields=['course_no','room_name__room_name']
    
   

    def get_room_name(self, obj):
        return obj.classrooms.room_name
    get_room_name.short_description = 'Author'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_at = datetime.datetime.now()
            obj.updated_at = datetime.datetime.now()
            # print("yes")
        else:
            obj.updated_at = datetime.datetime.now()

        # Only set added_by during the first save.
        obj.added_by = request.user.username
        return super().save_model(request, obj, form, change)

admin.site.register(ClassScheduleCenter,ClassScheduleCenterAdmin)



class LocationsAdmin(admin.ModelAdmin):
    ordering = ('id',)

admin.site.register(Locations,LocationsAdmin)

class LogSubjectInRoomAdmin(admin.ModelAdmin):
    list_display = ("course_no","room_location","user_ip","created_at",)
    list_per_page=50

admin.site.register(LogSubjectInRoom,LogSubjectInRoomAdmin)
