from api_fhir_r4.models import Element, Property


class CodeableConcept(Element):

    coding = Property('coding', 'Coding', count_max='*')
    text = Property('text', str)
