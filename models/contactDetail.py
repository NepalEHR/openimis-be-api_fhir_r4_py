from api_fhir_r4.models import Element, Property


class ContactDetail(Element):

    name = Property('name', str)
    telecom = Property('telecom', 'ContactPoint', count_max='*')
