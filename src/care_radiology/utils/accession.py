from care.emr.models.service_request import ServiceRequest

ACCESSION_NUMBER_LENGTH = 16


def get_service_request_by_accession(accession_number: str) -> ServiceRequest:
    """
    The accession number is the last 16 hex characters of the service request's
    external_id (its last two UUID groups, without the hyphen).

    Raises ServiceRequest.DoesNotExist if no service request matches.
    """
    accession_number = accession_number.strip().lower()
    sr_lookup_str = accession_number[:4] + "-" + accession_number[4:]
    return ServiceRequest.objects.get(external_id__endswith=sr_lookup_str)
