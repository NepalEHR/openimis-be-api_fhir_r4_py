from api_fhir_r4.models import Element, Property


class Annotation(Element):

    authorReference = Property('authorReference', 'Reference')
    authorString = Property('authorString', str)
    text = Property('text', str, required=True)
    time = Property('time', 'FHIRDate')
