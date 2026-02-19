import requests


class ThirdPartyError(Exception):
    pass


def request_third_party_transfer(*, reference: str, amount: int, timeout_s: float = 3.0) -> dict:
    try:
        resp = requests.post("http://localhost:8010/", timeout=timeout_s, json={
            "reference": reference,
            "amount": amount,
        })
        payload = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ThirdPartyError(str(e)) from e

    return payload


def is_third_party_success(payload: dict) -> bool:
    return payload.get("status") == 200 and payload.get("data") == "success"
