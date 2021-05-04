from api_fhir_r4.models import Element, Property


class BackboneElement(Element):

    modifierExtension = Property('modifierExtension', 'Extension', count_max='*')
