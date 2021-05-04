from api_fhir_r4.models import Element, Property


class SampledData(Element):

    origin = Property('origin', 'Quantity', required=True)
    period = Property('period', float, required=True)
    factor = Property('factor', float)
    lowerLimit = Property('lowerLimit', float)
    upperLimit = Property('upperLimit', float)
    dimensions = Property('dimensions', int, required=True)
    data = Property('data', str)  # "E" | "U" | "L"
