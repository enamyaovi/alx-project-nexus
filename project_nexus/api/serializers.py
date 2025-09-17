from rest_framework import serializers
from api.models import Genre, UserProfile, FavoriteMovie
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'password'
        ]

    def validate_email(self, value):
        pass 

    def validate_password(self, value):
        pass 

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    


