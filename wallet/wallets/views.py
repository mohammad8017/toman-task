from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from wallets.models import Transaction, TransactionKind, TransactionStatus, Wallet
from wallets.serializers import DepositSerializer, ScheduleWithdrawSerializer, TransactionSerializer, WalletSerializer


class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"

class CreateDepositView(APIView):
    def post(self, request, *args, **kwargs):
        wallet_uuid = kwargs["uuid"]
        s = DepositSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        amount = s.validated_data["amount"]

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(uuid=wallet_uuid)
            Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
            wallet.refresh_from_db(fields=["balance"])

            Transaction.objects.create(
                wallet=wallet,
                kind=TransactionKind.DEPOSIT,
                status=TransactionStatus.SUCCEEDED,
                amount=amount,
                execute_at=None,
            )

        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)


class ScheduleWithdrawView(APIView):
    def post(self, request, *args, **kwargs):
        wallet_uuid = kwargs["uuid"]
        wallet = get_object_or_404(Wallet, uuid=wallet_uuid)

        s = ScheduleWithdrawSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        amount = s.validated_data["amount"]
        execute_at = s.validated_data["execute_at"]

        txn = Transaction.objects.create(
            wallet=wallet,
            kind=TransactionKind.WITHDRAW,
            status=TransactionStatus.SCHEDULED,
            amount=amount,
            execute_at=execute_at,
        )

        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class TransactionListView(APIView):
    def get(self, request, *args, **kwargs):
        wallet_uuid = kwargs["uuid"]
        wallet = get_object_or_404(Wallet, uuid=wallet_uuid)

        txns = Transaction.objects.filter(wallet=wallet).order_by("-created_at")
        serializer = TransactionSerializer(txns, many=True)
        return Response(serializer.data)