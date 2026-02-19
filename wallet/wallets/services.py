from datetime import timedelta
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from wallets.models import Transaction, Wallet, TransactionKind, TransactionStatus
from wallets.utils import (
    ThirdPartyError,
    request_third_party_transfer,
    is_third_party_success,
)

INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
THIRD_PARTY_FAILED = "THIRD_PARTY_FAILED"
NETWORK_ERROR = "NETWORK_ERROR"
STALE_PROCESSING = "STALE_PROCESSING"


def fetch_due_withdrawal_ids(batch: int = 200) -> list[int]:
    now = timezone.now()
    return list(
        Transaction.objects.filter(
            kind=TransactionKind.WITHDRAW,
            status=TransactionStatus.SCHEDULED,
            execute_at__lte=now,
        )
        .order_by("execute_at", "id")
        .values_list("id", flat=True)[:batch]
    )


def claim_and_reserve(txn_id: int) -> tuple[bool, str, int]:
    with transaction.atomic():
        txn = (
            Transaction.objects.select_for_update()
            .select_related("wallet")
            .get(id=txn_id)
        )

        if txn.kind != TransactionKind.WITHDRAW or txn.status != TransactionStatus.SCHEDULED:
            return False, str(txn.reference), int(txn.amount)
        if txn.execute_at and txn.execute_at > timezone.now():
            return False, str(txn.reference), int(txn.amount)
        
        wallet = Wallet.objects.select_for_update().get(id=txn.wallet_id)

        if wallet.balance < txn.amount:
            txn.status = TransactionStatus.FAILED
            txn.last_error = INSUFFICIENT_FUNDS
            txn.save(update_fields=["status", "last_error", "updated_at"])
            return False, str(txn.reference), int(txn.amount)

        Wallet.objects.filter(id=wallet.id).update(balance=F("balance") - txn.amount)

        Transaction.objects.filter(id=txn.id).update(
            status=TransactionStatus.PROCESSING,
            attempts=F("attempts") + 1,
            last_error="",
        )

        return True, str(txn.reference), int(txn.amount)


def finalize_success(txn_id: int, provider_payload: dict) -> None:
    with transaction.atomic():
        txn = Transaction.objects.select_for_update().get(id=txn_id)
        if txn.status != TransactionStatus.PROCESSING:
            return
        txn.status = TransactionStatus.SUCCEEDED
        txn.provider_payload = provider_payload
        txn.save(update_fields=["status", "provider_payload", "updated_at"])


def finalize_failure_and_refund(txn_id: int, reason: str, provider_payload: dict | None = None) -> None:
    with transaction.atomic():
        txn = Transaction.objects.select_for_update().get(id=txn_id)
        if txn.status != TransactionStatus.PROCESSING:
            return

        wallet = Wallet.objects.select_for_update().get(id=txn.wallet_id)

        Wallet.objects.filter(id=wallet.id).update(balance=F("balance") + txn.amount)

        txn.status = TransactionStatus.FAILED
        txn.last_error = reason
        txn.provider_payload = provider_payload
        txn.save(update_fields=["status", "last_error", "provider_payload", "updated_at"])


def execute_withdrawal(txn_id: int) -> None:
    reserved, reference, amount = claim_and_reserve(txn_id)
    if not reserved:
        return

    try:
        payload = request_third_party_transfer(reference=reference, amount=amount, timeout_s=3.0)
        if is_third_party_success(payload):
            finalize_success(txn_id, payload)
        else:
            finalize_failure_and_refund(txn_id, THIRD_PARTY_FAILED, payload)
    except ThirdPartyError as e:
        finalize_failure_and_refund(txn_id, f"{NETWORK_ERROR}: {e}", None)


def release_stale_processing(older_than_minutes: int = 10, batch: int = 200) -> int:
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)

    ids = list(
        Transaction.objects.filter(
            kind=TransactionKind.WITHDRAW,
            status=TransactionStatus.PROCESSING,
            updated_at__lt=cutoff,
        ).values_list("id", flat=True)[:batch]
    )

    for txn_id in ids:
        finalize_failure_and_refund(txn_id, STALE_PROCESSING)

    return len(ids)
