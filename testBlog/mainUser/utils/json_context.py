from django.http import JsonResponse


def json_response(
        message=None, status=200, success=True, custom_data=None, **kwargs
):
    """Return a generic JSON response."""
    response_data = {"message": message, "success": success}
    if custom_data:
        response_data.update(custom_data)
    return JsonResponse(response_data, status=status, **kwargs)
