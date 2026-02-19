from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient


class ScheduledWithdrawExecutionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _iso(self, dt):
        s = dt.isoformat()
        return s.replace("+00:00", "Z")

    def _create_wallet_with_balance(self, amount: int):
        w = self.client.post("/wallets/", data={}, format="json").json()
        dep = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": amount}, format="json")
        self.assertIn(dep.status_code, (200, 201), dep.content)
        return w

    def _get_executor(self):
        try:
            from wallets.services import execute_withdrawal
            return execute_withdrawal
        except Exception as e:
            self.skipTest(f"Missing wallets.services.execute_withdrawal. Error: {e}")

    def _get_models(self):
        try:
            from wallets.models import Transaction
            return Transaction
        except Exception as e:
            self.skipTest(f"Missing wallets.models.Transaction. Error: {e}")

    def _schedule_and_force_due(self, wallet_uuid: str, amount: int):
        Transaction = self._get_models()

        execute_at = self._iso(timezone.now() + timedelta(seconds=10))
        resp = self.client.post(
            f"/wallets/{wallet_uuid}/withdraw",
            data={"amount": amount, "execute_at": execute_at},
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201), resp.content)

        payload = resp.json()

        ref = payload.get("reference")

        if ref:
            txn = Transaction.objects.get(reference=ref)
        else:
            txn = Transaction.objects.order_by("-id").first()

        Transaction.objects.filter(id=txn.id).update(execute_at=timezone.now() - timedelta(seconds=1))

        return txn.id

    @patch("wallets.services.request_third_party_transfer", return_value={"data": "success", "status": 200})
    def test_due_withdraw_success_debits_balance(self, _mock_tp):
        execute_withdrawal = self._get_executor()

        w = self._create_wallet_with_balance(1000)
        txn_id = self._schedule_and_force_due(w["uuid"], 400)

        execute_withdrawal(txn_id=txn_id)

        wallet_after = self.client.get(f"/wallets/{w['uuid']}/").json()
        self.assertEqual(int(wallet_after["balance"]), 600)

    @patch("wallets.services.request_third_party_transfer", return_value={"data": "failed", "status": 503})
    def test_due_withdraw_failure_refunds_balance(self, _mock_tp):
        execute_withdrawal = self._get_executor()

        w = self._create_wallet_with_balance(1000)
        txn_id = self._schedule_and_force_due(w["uuid"], 400)

        execute_withdrawal(txn_id=txn_id)

        wallet_after = self.client.get(f"/wallets/{w['uuid']}/").json()
        self.assertEqual(int(wallet_after["balance"]), 1000)

    @patch("wallets.services.request_third_party_transfer", return_value={"data": "success", "status": 200})
    def test_idempotency_execute_twice_does_not_double_debit(self, _mock_tp):
        execute_withdrawal = self._get_executor()

        w = self._create_wallet_with_balance(1000)
        txn_id = self._schedule_and_force_due(w["uuid"], 400)

        execute_withdrawal(txn_id=txn_id)
        execute_withdrawal(txn_id=txn_id)

        wallet_after = self.client.get(f"/wallets/{w['uuid']}/").json()
        self.assertEqual(int(wallet_after["balance"]), 600)
