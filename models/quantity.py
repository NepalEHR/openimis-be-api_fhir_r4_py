from api_fhir_r4.models import Element, Property


class Quantity(Element):

    value = Property('value', float)
    comparator = Property('comparator', str)  # < | <= | >= | >
    unit = Property('unit', str)
    system = Property('system', str)
    code = Property('code', str)
