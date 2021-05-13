

from api_fhir_r4.configurations import R4CoverageEligibilityConfiguration as Config
from api_fhir_r4.converters import BaseFHIRConverter, PatientConverter
from api_fhir_r4.models import CoverageEligibilityResponse as FHIREligibilityResponse, \
    CoverageEligibilityResponseInsuranceItem, CoverageEligibilityResponseInsurance, \
    CoverageEligibilityResponseInsuranceItemBenefit, Money,CoverageEligibilityResponseInsurance,Extension
from policy.services import EligibilityRequest, EligibilityService, EligibilityResponse
from policy.services import ByInsureeRequest, ByInsureeService, ByInsureeResponse
from insuree.models import Insuree, Photo, Gender, Family, FamilyType,InsureePolicy

import urllib.request, json 
import os
import json
from sosys.models import Employer,InsureeEmployer
from location.models import Location
from datetime import datetime
from django.db import connection
from mimetypes import guess_extension, guess_type
from policy.models import Policy,Product

class PolicyCoverageEligibilityRequestConverter(BaseFHIRConverter):
    current_id=""
    @classmethod
    def to_fhir_obj(cls, eligibility_response):
        fhir_response = FHIREligibilityResponse()
        foundInsuree = False
        for item in eligibility_response.items:
            if item.status in Config.get_fhir_active_policy_status():
                foundInsuree = True
                cls.build_fhir_insurance(fhir_response, item)
        if foundInsuree == False:
            if cls.getInsureeDetails(cls,cls.current_id):
                returnData = cls.getDataAgain(cls.current_id)
                for item in returnData.items:
                    # print(item)
                    if item.status in Config.get_fhir_active_policy_status():
                        foundInsuree = True
                        cls.build_fhir_insurance(fhir_response, item)
            else:
                print("Error")

        return fhir_response
    def getDataAgain(chfid):
        with connection.cursor() as cur:
            sql = """\
                EXEC [dbo].[uspPolicyInquiry] @CHFID = %s;
            """
            cur.execute(sql, [chfid])
            # stored proc outputs several results (varying from ),
            # we are only interested in the last one
            next = True
            res = []
            while next:
                try:
                    res = cur.fetchall()
                except:
                    pass
                finally:
                    next = cur.nextset()
            items = tuple(
                map(lambda x: ByInsureeService._to_item(x), res)
            )
            by_insuree_request = None
            return ByInsureeResponse(
                by_insuree_request=by_insuree_request,
                items=items
            )
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
    def parse_sosys_date(date_str,format="%m/%d/%Y"):
        try:
            a =  date_str.split(" ")
            formatted_date = datetime.strptime(a[0], format).strftime('%Y-%m-%d')
            return formatted_date
        except:
            a =datetime.today().strftime('%Y-%m-%d') 
            # formatted_date = datetime.strptime(a[0], format).strftime('%Y-%m-%d')
            return a
    def getInsureeDetails(cls,chfId):
        sosys_token = cls.getSosysToken(cls)
        sosys_url = str(os.environ.get('sosys_url'))+ str("/api/health/GetContributorFhir/")+str(chfId)
        output=""
        try:
            req = urllib.request.Request(sosys_url)
            req.add_header("Authorization","Bearer " +str(sosys_token))
            with urllib.request.urlopen(req) as f:
                res = f.read()
            output =str(res.decode())
        except Exception as e:
            return False
        respData = json.loads(str(output))
        if respData["IsSucess"]:
            # print(respData["ResponseData"])
            x = (respData["ResponseData"])
            genderMFO= Gender.objects.get(code='M') if x["gender"]=='male' else (Gender.objects.get(code='F') if x["gender"]=='female' else Gender.objects.get(code='O'))
            insureereturn = Insuree.objects.create(
                chf_id=x["id"],
                last_name= x["name"][0]["family"],
                other_names=x["name"][0]["given"][0]+" "+x["name"][0]["given"][1],
                gender= genderMFO,
                head=True,
                card_issued=False,
                email=x['telecom'][0]['value'],
                dob=cls.parse_sosys_date(x["birthDate"]),
                offline=False,
                current_address=x['address'][0]['text'],
                current_village=0,
                validity_from=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),audit_user_id=0)
            family_type = FamilyType.objects.get(code='H')
            familyreturn = Family.objects.create(
                location = Location.objects.get(id=3348),
                head_insuree = insureereturn,
                family_type = family_type,
                validity_from = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                audit_user_id = 2,
                poverty= False,

            )
            insureereturn.family = familyreturn
            insureereturn.save()
            policy_medical = cls.create_policy(cls,insureereturn, 'SSF0001', familyreturn,x['extension'])
            cls.create_insuree_policy(insureereturn,policy_medical)
            policy_accident = cls.create_policy(cls,insureereturn, 'SSF0002', familyreturn,x['extension'])
            cls.create_insuree_policy(insureereturn,policy_accident)
            if "contact" in x:
                for dep in x["contact"]:
                    genderMFO = Gender.objects.get(code='M') if dep["gender"] == 'male' else (
                        Gender.objects.get(code='F') if dep["gender"] == 'female' else Gender.objects.get(
                            code='O'))
                    familyInsureereturn = Insuree.objects.create(
                        chf_id="S"+x["id"],
                        last_name= dep["name"]["family"],
                        other_names=dep["name"]["given"][0],
                        family = familyreturn,
                        gender= genderMFO,
                        head=False,
                        card_issued=True,
                        dob="1111-01-01",
                        offline=False,
                        current_address=x['address'][0]['text'],
                        current_village=0,
                        validity_from=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        audit_user_id=1
                    )
                    cls.create_insuree_policy(familyInsureereturn, policy_medical)
                    cls.create_insuree_policy(familyInsureereturn, policy_accident)

            if 'link' in x:
                for emp in x["link"]:

                    iid = emp["other"]["identifier"]["value"]
                    empreturn = ''
                    try:
                        empreturn = Employer.objects.get(E_SSID=iid)
                    except Employer.DoesNotExist:
                        # print("empreturn",empreturn)
                        namee = emp["other"]["extension"][0]["valueString"]
                        emalli = emp["other"]["extension"][1]["valueString"]
                        empreturn = Employer.objects.create(E_SSID = iid,EmployerNameEng = namee,EmployerNameNep = namee, AlertSource = "email", AlertSourceVal = emalli, Status = "A")
                    # print("Inside")
                    InsureeEmployer.objects.create(employer= empreturn , insuree = insureereturn)
            
            if 'photo' in x:
                uri = x["photo"][0]["url"]
                ext = guess_extension(guess_type(uri)[0])
                photofileName = x["id"]+"_E00001_"+datetime.now().strftime('%Y%m%d')+"_0.0_0.0"+ext
                insureeid = x["id"]
                Photofolder = 'Images\\Updated\\'
                photodate = datetime.now().strftime('%Y-%m-%d')
                validityFrom = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                officerid = 3
                audituserid = -1
                # Create File in folder
                BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.join(BASE_DIR,Photofolder,photofileName)
                header, encoded = uri.split(",", 1)
                base64_img_bytes = encoded.encode('utf-8')
                with open(path, 'wb') as file_to_save:
                    decoded_image_data = base64.decodebytes(base64_img_bytes)
                    file_to_save.write(decoded_image_data)
                pho = Photo.objects.create(
                    insuree_id=insureereturn.id,
                    chf_id=x["id"],
                    folder=Photofolder,
                    validity_from=validityFrom,
                    filename=photofileName,
                    date=photodate,
                    officer_id=officerid,
                    audit_user_id=audituserid
                )
                insureereturn.photo = pho
                insureereturn.photo_date = pho.date
                insureereturn.save()
            return True
        else:
            raise CustomInsureeSearchException(respData["Message"])
            return False


    def create_policy(cls,insuree,product_id,family,extension):
        policyRet = Policy.objects.create(
            family=family,
            # enroll_date=datetime.now().strftime('%Y-%m-%d'),
            enroll_date=cls.parse_sosys_date(extension[1]["valueString"],'%Y.%m.%d'),
            # start_date=datetime.now().strftime('%Y-%m-%d'),
            start_date=cls.parse_sosys_date(extension[1]["valueString"],'%Y.%m.%d'),
            product=Product.objects.get(code=product_id,validity_to=None),
            audit_user_id=1,
            # effective_date=datetime.now().strftime('%Y-%m-%d'),
            effective_date=cls.parse_sosys_date(extension[1]["valueString"],'%Y.%m.%d'),
            expiry_date=cls.parse_sosys_date(extension[2]["valueString"]),
            status=2,
            value=700000.00,
            stage='N'
        )
        return policyRet
    def create_insuree_policy(insuree,policy):
        insureePolicyRet = InsureePolicy.objects.create(
            insuree=insuree,
            policy=policy,
            audit_user_id=1,
            enrollment_date=policy.enroll_date,
            start_date=policy.enroll_date,
            effective_date=policy.enroll_date,
            # expiry_date=datetime.now().strftime('%Y-%m-%d'),
            expiry_date=policy.expiry_date,
            validity_from=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            # validity_to=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        # print(respData)
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
            print("ERROR HERE")
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
                return True
            else:
                return False
            # Mextension.append(extension)
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
class CustomInsureeSearchException(Exception):
    pass