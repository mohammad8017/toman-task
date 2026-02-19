from django.contrib import admin

from wallets.models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("uuid", "balance", "created_at", "updated_at")
    search_fields = ("uuid",)
    list_filter = ("created_at", "updated_at")
    ordering = ("-created_at",)
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference",
        "wallet",
        "kind",
        "status",
        "amount",
        "execute_at",
        "attempts",
        "created_at",
        "updated_at",
    )
    search_fields = ("reference", "wallet__uuid")
    list_filter = ("kind", "status", "created_at", "execute_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields += ["wallet", "kind", "amount", "execute_at", "reference"]
        return fields
