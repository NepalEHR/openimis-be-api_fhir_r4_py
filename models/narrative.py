from api_fhir_r4.models import Element, Property


class Narrative(Element):

    div = Property('div', str, required=True)
    status = Property('status', str, required=True)  # generated | extensions | additional | empty
