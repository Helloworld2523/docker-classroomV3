from rest_framework import serializers
from .models import ClassScheduleCenter

class ClassScheduleCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassScheduleCenter
        fields = '__all__'
