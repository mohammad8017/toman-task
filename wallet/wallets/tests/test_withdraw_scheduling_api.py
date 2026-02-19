from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient


class WithdrawSchedulingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _iso(self, dt):
        s = dt.isoformat()
        return s.replace("+00:00", "Z")

    def test_schedule_withdraw_future_does_not_change_balance(self):
        w = self.client.post("/wallets/", data={}, format="json").json()

        dep = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": 1000}, format="json")
        self.assertIn(dep.status_code, (200, 201), dep.content)

        execute_at = self._iso(timezone.now() + timedelta(seconds=30))

        sched = self.client.post(
            f"/wallets/{w['uuid']}/withdraw",
            data={"amount": 400, "execute_at": execute_at},
            format="json",
        )
        self.assertIn(sched.status_code, (200, 201), sched.content)

        wallet_now = self.client.get(f"/wallets/{w['uuid']}/").json()
        self.assertEqual(int(wallet_now["balance"]), 1000)

        payload = sched.json()
        self.assertTrue(
            any(k in payload for k in ("reference", "transaction_id", "id")),
            f"Expected a transaction identifier in response, got: {payload}",
        )

    def test_schedule_withdraw_rejects_past_execute_at(self):
        w = self.client.post("/wallets/", data={}, format="json").json()

        past = self._iso(timezone.now() - timedelta(seconds=5))
        sched = self.client.post(
            f"/wallets/{w['uuid']}/withdraw",
            data={"amount": 100, "execute_at": past},
            format="json",
        )
        self.assertEqual(sched.status_code, 400, sched.content)
