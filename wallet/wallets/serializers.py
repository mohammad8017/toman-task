from rest_framework import serializers
from django.utils import timezone
from wallets.models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("uuid", "balance")
        read_only_fields = ("uuid", "balance")

class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)


class ScheduleWithdrawSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    execute_at = serializers.DateTimeField()

    def validate_execute_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("execute_at must be in the future (UTC).")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ("reference", "kind", "status", "amount", "execute_at", "created_at")
        read_only_fields = fields
