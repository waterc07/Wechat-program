from flask import jsonify


def success_response(data=None, message="OK", code="OK", status=200):
    return (
        jsonify(
            {
                "success": True,
                "code": code,
                "message": message,
                "data": data or {},
            }
        ),
        status,
    )


def error_response(message, code="ERROR", status=400, data=None):
    return (
        jsonify(
            {
                "success": False,
                "code": code,
                "message": message,
                "data": data or {},
            }
        ),
        status,
    )

