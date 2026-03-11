from datetime import datetime, timezone
from typing import Any

import boto3

from app.models import JobStatus, VariantStatus


class DynamoDBJobsRepository:
    """DynamoDB single-table jobs repo using IAM task role credentials (no explicit keys)."""

    def __init__(self, region_name: str, table_name: str) -> None:
        self.table_name = table_name
        self._client = boto3.client("dynamodb", region_name=region_name)

    def create_job(
        self, job_id: str, input_key: str, variants: list[dict[str, Any]]
    ) -> None:
        timestamp = _utc_now_iso()
        dynamo_variants = [
            {
                "M": {
                    "name": {"S": v["name"]},
                    "width": {"N": str(v["width"])},
                    "format": {"S": v["format"]},
                    "status": {"S": VariantStatus.PENDING.value},
                    "outputKey": {"NULL": True},
                    "error": {"NULL": True},
                }
            }
            for v in variants
        ]
        try:
            self._client.put_item(
                TableName=self.table_name,
                Item={
                    "jobId": {"S": job_id},
                    "inputKey": {"S": input_key},
                    "status": {"S": JobStatus.CREATED.value},
                    "error": {"NULL": True},
                    "variants": {"L": dynamo_variants},
                    "createdAt": {"S": timestamp},
                    "updatedAt": {"S": timestamp},
                },
                ConditionExpression="attribute_not_exists(jobId)",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise ValueError(f"Job {job_id} already exists")

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        response = self._client.get_item(
            TableName=self.table_name,
            Key={"jobId": {"S": job_id}},
        )
        item = response.get("Item")
        if item is None:
            return None

        return {
            "job_id": item["jobId"]["S"],
            "input_key": item["inputKey"]["S"],
            "status": item["status"]["S"],
            "error": _dynamo_str_or_none(item.get("error")),
            "created_at": item["createdAt"]["S"],
            "updated_at": item["updatedAt"]["S"],
            "variants": [
                {
                    "name": v["M"]["name"]["S"],
                    "width": int(v["M"]["width"]["N"]),
                    "format": v["M"]["format"]["S"],
                    "status": v["M"]["status"]["S"],
                    "output_key": _dynamo_str_or_none(v["M"].get("outputKey")),
                    "error": _dynamo_str_or_none(v["M"].get("error")),
                }
                for v in item["variants"]["L"]
            ],
        }

    def update_status(
        self, job_id: str, status: JobStatus, error: str | None = None
    ) -> bool:
        timestamp = _utc_now_iso()
        error_value: dict[str, Any] = (
            {"S": error} if error is not None else {"NULL": True}
        )
        try:
            self._client.update_item(
                TableName=self.table_name,
                Key={"jobId": {"S": job_id}},
                UpdateExpression="SET #s = :s, #e = :e, updatedAt = :u",
                ExpressionAttributeNames={"#s": "status", "#e": "error"},
                ExpressionAttributeValues={
                    ":s": {"S": status.value},
                    ":e": error_value,
                    ":u": {"S": timestamp},
                },
                ConditionExpression="attribute_exists(jobId)",
            )
            return True
        except self._client.exceptions.ConditionalCheckFailedException:
            return False

    def update_variant(
        self,
        job_id: str,
        variant_name: str,
        status: VariantStatus,
        output_key: str | None = None,
        error: str | None = None,
    ) -> bool:
        response = self._client.get_item(
            TableName=self.table_name,
            Key={"jobId": {"S": job_id}},
            ProjectionExpression="variants",
        )
        item = response.get("Item")
        if item is None:
            return False

        variant_index = None
        for i, v in enumerate(item["variants"]["L"]):
            if v["M"]["name"]["S"] == variant_name:
                variant_index = i
                break
        if variant_index is None:
            return False

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
                ":s": {"S": status.value},
                ":o": output_key_value,
                ":e": error_value,
                ":u": {"S": timestamp},
            },
        )
        return True

    def ping(self) -> bool:
        try:
            self._client.describe_table(TableName=self.table_name)
            return True
        except Exception:
            return False


def _dynamo_str_or_none(attr: dict[str, Any] | None) -> str | None:
    if attr is None or "NULL" in attr:
        return None
    return attr.get("S")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
