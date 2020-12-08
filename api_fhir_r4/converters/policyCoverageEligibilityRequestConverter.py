from policy.services import ByInsureeRequest

from api_fhir_r4.configurations import R4CoverageEligibilityConfiguration as Config
from api_fhir_r4.converters import BaseFHIRConverter, PatientConverter
from api_fhir_r4.models import CoverageEligibilityResponse as FHIREligibilityResponse, \
    CoverageEligibilityResponseInsuranceItem, CoverageEligibilityResponseInsurance, \
    CoverageEligibilityResponseInsuranceItemBenefit, Money,CoverageEligibilityResponseInsurance,Extension

import urllib.request, json 

class PolicyCoverageEligibilityRequestConverter(BaseFHIRConverter):
    current_id=""
    @classmethod
    def to_fhir_obj(cls, eligibility_response):
        fhir_response = FHIREligibilityResponse()
        for item in eligibility_response.items:
            if item.status in Config.get_fhir_active_policy_status():
                cls.build_fhir_insurance(fhir_response, item)
        return fhir_response

    @classmethod
    def to_imis_obj(cls, fhir_eligibility_request, audit_user_id):
        uuid = cls.build_imis_uuid(fhir_eligibility_request)
        cls.current_id=uuid
        return ByInsureeRequest(uuid)

    @classmethod
    def build_fhir_insurance(cls, fhir_response, response):
        result = CoverageEligibilityResponseInsurance()
        result.extension = []
        extension = Extension()
        extension.url = "https://openimis.atlassian.net/wiki/spaces/OP/pages/960069653/FHIR+extension+isHead"
        extension.valueBoolean = cls.checkPolicyStatus(cls)
        result.extension.append(extension)
        #cls.build_fhir_insurance_contract(result, response)
        cls.build_fhir_money_item(result, Config.get_fhir_balance_code(),
                                     response.ceiling,
                                     response.ded)
        fhir_response.insurance.append(result)

    '''
    @classmethod
    def build_fhir_insurance_contract(cls, insurance, contract):
        insurance.contract = ContractConverter.build_fhir_resource_reference(
            contract)
    '''
    def checkPolicyStatus(cls):
        sosys_status =False
        sosys_url = "https://sudishrestha.com.np/sosys_status_check.json"
        with urllib.request.urlopen(sosys_url) as url:
            data = json.loads(url.read().decode())
            print(data["ResponseData"][0]["Status"])
            if "Active" == data["ResponseData"][0]["Status"]:
                sosys_status =True
        print(cls.current_id)
        return sosys_status

    @classmethod
    def build_fhir_money_item(cls, insurance, code, allowed_value, used_value):
        item = cls.build_fhir_generic_item(code)
        cls.build_fhir_money_item_benefit(
            item, allowed_value, used_value)
        insurance.item.append(item)

    @classmethod
    def build_fhir_generic_item(cls, code):
        item = CoverageEligibilityResponseInsuranceItem()
        item.category = cls.build_simple_codeable_concept(
            Config.get_fhir_balance_default_category())
        return item

    @classmethod
    def build_fhir_money_item_benefit(cls, item, allowed_value, used_value):
        benefit = cls.build_fhir_generic_item_benefit()
        allowed_money_value = Money()
        allowed_money_value.value = allowed_value or 0
        benefit.allowedMoney = allowed_money_value
        used_money_value = Money()
        used_money_value.value = used_value or 0
        benefit.usedMoney = used_money_value
        item.benefit.append(benefit)

    @classmethod
    def build_fhir_generic_item_benefit(cls):
        benefit = CoverageEligibilityResponseInsuranceItemBenefit()
        benefit.type = cls.build_simple_codeable_concept(
            Config.get_fhir_financial_code())
        return benefit

    @classmethod
    def build_imis_uuid(cls, fhir_eligibility_request):
        uuid = None
        patient_reference = fhir_eligibility_request.patient
        if patient_reference:
            uuid = PatientConverter.get_resource_id_from_reference(
                patient_reference)
        return uuid
