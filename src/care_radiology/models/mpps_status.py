from django.db import models
from care.emr.models import EMRBaseModel
from care.emr.models.service_request import ServiceRequest


class RadiologyMppsStatus(EMRBaseModel):
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="radiology_mpps_statuses",
    )
    accession_number = models.CharField(max_length=16, unique=True)
    status = models.CharField(max_length=32)
    procedure_step_id = models.CharField(max_length=64, null=True, blank=True)
    mpps_sop_instance_uid = models.CharField(max_length=64, null=True, blank=True)
