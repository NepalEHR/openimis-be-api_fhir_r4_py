from policy.services import ByInsureeRequest

from api_fhir_r4.configurations import R4CoverageEligibilityConfiguration as Config
from api_fhir_r4.converters import BaseFHIRConverter, PatientConverter
from api_fhir_r4.models import CoverageEligibilityResponse as FHIREligibilityResponse, \
    CoverageEligibilityResponseInsuranceItem, CoverageEligibilityResponseInsurance, \
    CoverageEligibilityResponseInsuranceItemBenefit, Money,CoverageEligibilityResponseInsurance,Extension


import urllib.request, json 
import os
import json

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
        extension.url = "sosys_policy"
        extension.valueBoolean = cls.checkPolicyStatus(cls,extension)
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
    def getSosysToken(cls):
        auth_url = os.environ.get('sosys_url')+ str("/api/auth/login")
        data ={
                "UserId":os.environ.get('sosy_userid'),
                "Password":os.environ.get('sosys_password'),
                "wsType":os.environ.get('sosys_wstype')
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = json.dumps(data).encode("utf-8")
        output=""
        try:
            req = urllib.request.Request(auth_url, data, headers)
            with urllib.request.urlopen(req) as f:
                res = f.read()
            output =str(res.decode())
        except Exception as e:
            print(e)
        token_arr=json.loads(str(output))
        return token_arr["token"]

    def checkPolicyStatus(cls,Mextension):
        sosys_token = cls.getSosysToken(cls)
        sosys_url = str(os.environ.get('sosys_url'))+ str("/api/health/GetContributorStatusFhir/")+str(cls.current_id)
        output=""
        try:
            req = urllib.request.Request(sosys_url)
            req.add_header("Authorization","Bearer " +str(sosys_token))
            with urllib.request.urlopen(req) as f:
                res = f.read()
            output =str(res.decode())
        except Exception as e:
            return False
        resJson = json.loads(str(output))
        for resp in resJson["ResponseData"]:
            extension = Extension()
            extension.url = resp['class'][0]['value']
            policyValid =resp["status"]
            if policyValid.lower() == 'active':
                extension.valueBoolean = True
            else:
                extension.valueBoolean = False
            Mextension.append(extension)
        # return Mextension

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
