"""Initial production schema."""

from alembic import op
import sqlalchemy as sa

revision = "202606281300"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "plaid_items",
        sa.Column("item_id", sa.String(), primary_key=True),
        sa.Column("client_user_id", sa.String(), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("token_key_version", sa.String(), nullable=False),
        sa.Column("institution_id", sa.String(), nullable=True),
        sa.Column("institution_name", sa.String(), nullable=True),
        sa.Column("transactions_cursor", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_plaid_items_client_user_id", "plaid_items", ["client_user_id"])
    op.create_table(
        "plaid_transactions",
        sa.Column("transaction_id", sa.String(), primary_key=True),
        sa.Column("client_user_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_plaid_transactions_client_user_id",
        "plaid_transactions",
        ["client_user_id"],
    )
    op.create_table(
        "dashboard_snapshots",
        sa.Column("client_user_id", sa.String(), nullable=False),
        sa.Column("month", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("client_user_id", "month"),
    )
    op.create_table(
        "webhook_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("webhook_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("dashboard_snapshots")
    op.drop_table("plaid_transactions")
    op.drop_index("idx_plaid_items_client_user_id", table_name="plaid_items")
    op.drop_table("plaid_items")
    op.drop_table("users")
