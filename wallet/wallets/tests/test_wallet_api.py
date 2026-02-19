from django.test import TestCase
from rest_framework.test import APIClient


class WalletApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_wallet(self):
        resp = self.client.post("/wallets/", data={}, format="json")
        self.assertIn(resp.status_code, (200, 201), resp.content)

        data = resp.json()
        self.assertIn("uuid", data)
        self.assertIn("balance", data)
        self.assertEqual(int(data["balance"]), 0)

    def test_get_wallet(self):
        create = self.client.post("/wallets/", data={}, format="json")
        self.assertIn(create.status_code, (200, 201), create.content)
        w = create.json()

        resp = self.client.get(f"/wallets/{w['uuid']}/")
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        self.assertEqual(data["uuid"], w["uuid"])

    def test_deposit_increases_balance(self):
        create = self.client.post("/wallets/", data={}, format="json")
        w = create.json()

        dep = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": 1000}, format="json")
        self.assertIn(dep.status_code, (200, 201), dep.content)
        self.assertEqual(int(dep.json()["balance"]), 1000)

        dep2 = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": 250}, format="json")
        self.assertIn(dep2.status_code, (200, 201), dep2.content)
        self.assertEqual(int(dep2.json()["balance"]), 1250)

    def test_deposit_invalid_amount(self):
        w = self.client.post("/wallets/", data={}, format="json").json()

        r1 = self.client.post(f"/wallets/{w['uuid']}/deposit", data={}, format="json")
        self.assertEqual(r1.status_code, 400, r1.content)

        r2 = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": -5}, format="json")
        self.assertEqual(r2.status_code, 400, r2.content)

        r3 = self.client.post(f"/wallets/{w['uuid']}/deposit", data={"amount": 0}, format="json")
        self.assertEqual(r3.status_code, 400, r3.content)
