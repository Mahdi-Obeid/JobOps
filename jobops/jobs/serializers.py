from rest_framework import serializers
from .models import User, Equipment, JobTask, Job, JobTaskEquipment


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, help_text="Password for the new user")
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        help_text="User role in the system"
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ["id", "name", "eq_type", "serial_number", "is_active"]


class JobTaskEquipmentSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    equipment_id = serializers.IntegerField(write_only=True, help_text="ID of the equipment to assign")

    class Meta:
        model = JobTaskEquipment
        fields = ["id", "equipment", "equipment_id", "quantity", "notes"]


class JobTaskSerializer(serializers.ModelSerializer):
    # nested field for all equipment required for this task
    required_equipment = JobTaskEquipmentSerializer(source='jobtaskequipment_set', many=True, read_only=True)
    # For creating/updating equipment requirements
    equipment_requirements = JobTaskEquipmentSerializer(
        many=True, 
        write_only=True, 
        required=False,
        help_text="List of equipment required for this task"
    )
    status = serializers.ChoiceField(
        choices=JobTask.STATUS_CHOICES,
        help_text="Current status of the task"
    )

    class Meta:
        model = JobTask
        fields = [
            "id", "title", "description", "order", "status", "completed_at", 
            "job", "required_equipment", "equipment_requirements"
        ]

    def create(self, validated_data):
        equipment_requirements = validated_data.pop('equipment_requirements', [])
        task = JobTask.objects.create(**validated_data)
        
        # Create equipment requirements
        for equipment_req in equipment_requirements:
            JobTaskEquipment.objects.create(
                job_task=task,
                equipment_id=equipment_req['equipment_id'],
                quantity=equipment_req.get('quantity', 1),
                notes=equipment_req.get('notes', '')
            )
        
        return task

    def update(self, instance, validated_data):
        equipment_requirements = validated_data.pop('equipment_requirements', None)
        
        # Update the task
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Auto-set completed_at when status changes to COMPLETED
        if instance.status == "COMPLETED" and not instance.completed_at:
            from django.utils import timezone
            instance.completed_at = timezone.now()
        
        instance.save()
        
        # Update equipment requirements if provided
        if equipment_requirements is not None:
            # Clear existing requirements
            instance.jobtaskequipment_set.all().delete()
            
            # Create new requirements
            for equipment_req in equipment_requirements:
                JobTaskEquipment.objects.create(
                    job_task=instance,
                    equipment_id=equipment_req['equipment_id'],
                    quantity=equipment_req.get('quantity', 1),
                    notes=equipment_req.get('notes', '')
                )
        
        return instance


class JobSerializer(serializers.ModelSerializer):
    tasks = JobTaskSerializer(source="jobtask_set", many=True, read_only=True)
    status = serializers.ChoiceField(
        choices=Job.STATUS_CHOICES,
        help_text="Current status of the job"
    )
    priority = serializers.ChoiceField(
        choices=Job.PRIORITY_CHOICES,
        help_text="Priority level of the job"
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="TECHNICIAN"),
        help_text="Technician assigned to this job"
    )

    class Meta:
        model = Job
        fields = [
            "id", "title", "description", "client_name", "created_by", "assigned_to",
            "status", "priority", "scheduled_date", "tasks"
        ]
        read_only_fields = ["created_by"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user
        return super().create(validated_data)