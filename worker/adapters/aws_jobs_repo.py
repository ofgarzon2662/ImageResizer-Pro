from datetime import datetime, timezone
from typing import Any

import boto3


class DynamoDBJobsRepository:
    """DynamoDB jobs repo using IAM task role credentials (no explicit keys)."""

    def __init__(self, region_name: str, table_name: str) -> None:
        self.table_name = table_name
        self._client = boto3.client("dynamodb", region_name=region_name)

    def update_job_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None:
        timestamp = _utc_now_iso()
        error_value: dict[str, Any] = (
            {"S": error} if error is not None else {"NULL": True}
        )
        self._client.update_item(
            TableName=self.table_name,
            Key={"jobId": {"S": job_id}},
            UpdateExpression="SET #s = :s, #e = :e, updatedAt = :u",
            ExpressionAttributeNames={"#s": "status", "#e": "error"},
            ExpressionAttributeValues={
                ":s": {"S": status},
                ":e": error_value,
                ":u": {"S": timestamp},
            },
        )

    def update_variant_status(
        self,
        job_id: str,
        variant_name: str,
        status: str,
        output_key: str | None = None,
        error: str | None = None,
    ) -> None:
        response = self._client.get_item(
            TableName=self.table_name,
            Key={"jobId": {"S": job_id}},
            ProjectionExpression="variants",
        )
        item = response.get("Item")
        if item is None:
            return

        variant_index = None
        for i, v in enumerate(item["variants"]["L"]):
            if v["M"]["name"]["S"] == variant_name:
                variant_index = i
                break
        if variant_index is None:
            return

        timestamp = _utc_now_iso()
        output_key_value: dict[str, Any] = (
            {"S": output_key} if output_key is not None else {"NULL": True}
        )
        error_value: dict[str, Any] = (
            {"S": error} if error is not None else {"NULL": True}
        )

        prefix = f"variants[{variant_index}]"
        self._client.update_item(
            TableName=self.table_name,
            Key={"jobId": {"S": job_id}},
            UpdateExpression=(
                f"SET {prefix}.#s = :s, {prefix}.outputKey = :o, "
                f"{prefix}.#e = :e, updatedAt = :u"
            ),
            ExpressionAttributeNames={"#s": "status", "#e": "error"},
            ExpressionAttributeValues={
                ":s": {"S": status},
                ":o": output_key_value,
                ":e": error_value,
                ":u": {"S": timestamp},
            },
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
