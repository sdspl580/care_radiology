from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework.exceptions import AuthenticationFailed, ParseError
from pydantic import ValidationError as PydanticValidationError


from care.emr.models.patient import Patient
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.service_request.spec import (
    SERVICE_REQUEST_CANCELLED_CHOICES,
    ServiceRequestStatusChoices,
)
from care_radiology.models.dicom_study import DicomStudy
from care_radiology.models.mpps_status import RadiologyMppsStatus
from care_radiology.models.webhook_logs import RadiologyWebhookLogs
from care_radiology.models.radiology_service_request import RadiologyServiceRequest
from care_radiology.resources.webhook.spec import MPPS_STATUS_COMPLETED, MppsWebhookSpec
from care_radiology.utils.accession import get_service_request_by_accession
from care_radiology.authentication import StaticAPIKeyAuthentication


class WebhookViewSet(ViewSet):
    @action(
        detail=False,
        methods=["post"],
        url_path="study",
        permission_classes=[AllowAny],
    )
    def save_webhook(self, request):
        # Manually authenticate
        authenticator = StaticAPIKeyAuthentication()
        user_auth_tuple = authenticator.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid API key")

        try:
            data = request.data
        except ParseError:
            return Response(
                {"detail": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        RadiologyWebhookLogs.objects.create(raw_data=data, type="SR-STUDY-INSERT")
        if not isinstance(data, dict):
            return Response(
                {"detail": "JSON object expected"},
                status=status.HTTP_400_BAD_REQUEST,
            )


        if data.get("service_request_id") and data.get("study_id"):
            try:
                sr = ServiceRequest.objects.get(external_id=data["service_request_id"])
            except ServiceRequest.DoesNotExist:
                return Response(
                    {"detail": "No matching service request"},
                    status=status.HTTP_409_CONFLICT,
                )
            (study, ds_created) = DicomStudy.objects.get_or_create(
                dicom_study_uid=data.get("study_id"), patient=sr.patient, defaults={}
            )
            if sr and study:
                (rsr, rsr_created) = RadiologyServiceRequest.objects.update_or_create(
                    service_request=sr, dicom_study=study, defaults={"raw_data": data}
                )

            return Response(
                {
                    "detail": "Webhook received and saved successfully",
                    "record": {
                        "external_id": rsr.external_id,
                        "data": rsr.raw_data,
                    },
                },
                status=status.HTTP_200_OK,
            )
        elif data.get("patient_id") and data.get("study_id"):
            patient = Patient.objects.filter(
                instance_identifiers__contains=[{"value": data.get("patient_id")}]
            ).first()
            if not patient:
                return Response(
                    {"detail": "No matching patient"},
                    status=status.HTTP_409_CONFLICT,
                )
            (study, ds_created) = DicomStudy.objects.get_or_create(
                dicom_study_uid=data.get("study_id"), patient = patient, defaults={}
            )
            if (patient and study):
                return Response(
                    {
                        "detail": "Webhook received and saved successfully",
                        "record": {
                            "external_id": study.external_id,
                            "data": data,
                        },
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(
            {
                "detail": "Webhook received and saved successfully",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="mpps",
        permission_classes=[AllowAny],
    )
    def mpps_status(self, request):
        # Manually authenticate
        authenticator = StaticAPIKeyAuthentication()
        user_auth_tuple = authenticator.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid API key")

        try:
            data = request.data
        except ParseError:
            return Response(
                {"detail": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        RadiologyWebhookLogs.objects.create(raw_data=data, type="MPPS-STATUS")
        if not isinstance(data, dict):
            return Response(
                {"detail": "JSON object expected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = MppsWebhookSpec.model_validate(data)
        except PydanticValidationError as e:
            return Response(
                {
                    "detail": "Invalid payload",
                    "errors": e.errors(include_url=False, include_context=False),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sr = get_service_request_by_accession(payload.accession_number)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"detail": "No matching service request"},
                status=status.HTTP_409_CONFLICT,
            )

        (mpps, mpps_created) = RadiologyMppsStatus.objects.update_or_create(
            accession_number=payload.accession_number,
            defaults={
                "service_request": sr,
                "status": payload.status,
                "procedure_step_id": payload.procedure_step_id,
                "mpps_sop_instance_uid": payload.mpps_sop_instance_uid,
            },
        )

        # Mirrors the guards in core's ServiceRequestViewSet.complete
        if (
            payload.status == MPPS_STATUS_COMPLETED
            and sr.status != ServiceRequestStatusChoices.completed.value
            and sr.status not in SERVICE_REQUEST_CANCELLED_CHOICES
        ):
            sr.status = ServiceRequestStatusChoices.completed.value
            sr.save(update_fields=["status", "modified_date"])

        return Response(
            {
                "detail": "MPPS status updated",
                "record": {
                    "external_id": mpps.external_id,
                    "accession_number": mpps.accession_number,
                    "status": mpps.status,
                    "service_request_status": sr.status,
                },
            },
            status=status.HTTP_200_OK,
        )
