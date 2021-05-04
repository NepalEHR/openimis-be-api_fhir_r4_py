from api_fhir_r4.converters.coverageConverter import CoverageConverter
from api_fhir_r4.serializers import BaseFHIRSerializer
from api_fhir_r4.models import Coverage, CoverageClass
from rest_framework import serializers

class CoverageSerializer(BaseFHIRSerializer):

    fhirConverter = CoverageConverter

    