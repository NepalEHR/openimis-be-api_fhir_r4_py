from api_fhir_r4.models import FHIRBaseObject, Property


class Element(FHIRBaseObject):

    id = Property('id', str)
    extension = Property('extension', 'Extension', count_max='*')
