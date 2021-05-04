import copy

from location.models import Location

from api_fhir_r4.converters import LocationConverter
from api_fhir_r4.serializers import BaseFHIRSerializer


class LocationSerializer(BaseFHIRSerializer):
    fhirConverter = LocationConverter()

    def create(self, validated_data):
        copied_data = copy.deepcopy(validated_data)
        del copied_data['_state']
        return Location.objects.create(**copied_data)

    def update(self, instance, validated_data):
        # TODO legalForm isn't covered because that value is missing in the model
        # TODO LocationId isn't covered because that value is missing in the model
        # TODO offline isn't covered in the current version of API
        # TODO care_type isn't covered in the current version of API
        instance.code = validated_data.get('code', instance.code)
        instance.name = validated_data.get('name', instance.name)
        instance.type = validated_data.get('type', instance.type)
        instance.partOf = validated_data.get('partOf', instance.partOf)
        instance.audit_user_id = self.get_audit_user_id()
        instance.save()
        return instance
