from celery import shared_task

from wallets.services import execute_withdrawal, fetch_due_withdrawal_ids, release_stale_processing


@shared_task(bind=True, max_retries=5, default_retry_delay=5)
def execute_withdrawal_task(self, txn_id: int):
    execute_withdrawal(txn_id=txn_id)


@shared_task
def enqueue_due_withdrawals(batch: int = 200):
    release_stale_processing(older_than_minutes=10)
    ids = fetch_due_withdrawal_ids(batch=batch)
    for txn_id in ids:
        execute_withdrawal_task.delay(txn_id)


@shared_task
def release_stale():
    release_stale_processing(older_than_minutes=10)
