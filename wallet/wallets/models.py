import uuid

from django.db import models


class Wallet(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    balance = models.BigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(balance__gte=0), name='balance_non_negative')
        ]


class TransactionKind(models.TextChoices):
        DEPOSIT = "DEPOSIT"
        WITHDRAW = "WITHDRAW"

class TransactionStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Transaction(models.Model):
    

    reference = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    kind = models.CharField(max_length=16, choices=TransactionKind.choices)
    status = models.CharField(max_length=16, choices=TransactionStatus.choices)

    amount = models.PositiveBigIntegerField()

    execute_at = models.DateTimeField(null=True, blank=True, db_index=True)

    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    provider_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "execute_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(kind=TransactionKind.DEPOSIT, execute_at__isnull=True) |
                    models.Q(kind=TransactionKind.WITHDRAW, execute_at__isnull=False)
                ),
                name="withdraw_execute_at_required",
            )
        ]


