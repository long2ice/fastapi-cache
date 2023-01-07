import datetime
from typing import Optional, Tuple

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session

from fastapi_cache.backends import Backend


class DynamoBackend(Backend):
    """
    Amazon DynamoDB backend provider

    This backend requires an existing table within your AWS environment to be passed during
    backend init. If ttl is going to be used, this needs to be manually enabled on the table
    using the `ttl` key. Dynamo will take care of deleting outdated objects, but this is not
    instant so don't be alarmed when they linger around for a bit.

    As with all AWS clients, credentials will be taken from the environment. Check the AWS SDK
    for more information.

    Usage:
        >> dynamodb = DynamoBackend(table_name="your-cache", region="eu-west-1")
        >> await dynamodb.init()
        >> FastAPICache.init(dynamodb)
    """

    def __init__(self, table_name: str, region: Optional[str] = None) -> None:
        self.session = get_session()
        self.client: Optional[AioBaseClient] = None  # Needs async init
        self.table_name = table_name
        self.region = region

    async def init(self) -> None:
        self.client = await self.session.create_client(
            "dynamodb", region_name=self.region
        ).__aenter__()

    async def close(self) -> None:
        self.client = await self.client.__aexit__(None, None, None)

    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        response = await self.client.get_item(TableName=self.table_name, Key={"key": {"S": key}})

        if "Item" in response:
            value = response["Item"].get("value", {}).get("S")
            ttl = response["Item"].get("ttl", {}).get("N")

            if not ttl:
                return -1, value

            # It's only eventually consistent so we need to check ourselves
            expire = int(ttl) - int(datetime.datetime.now().timestamp())
            if expire > 0:
                return expire, value

        return 0, None

    async def get(self, key: str) -> str:
        response = await self.client.get_item(TableName=self.table_name, Key={"key": {"S": key}})
        if "Item" in response:
            return response["Item"].get("value", {}).get("S")

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        ttl = (
            {
                "ttl": {
                    "N": str(
                        int(
                            (
                                datetime.datetime.now() + datetime.timedelta(seconds=expire)
                            ).timestamp()
                        )
                    )
                }
            }
            if expire
            else {}
        )

        await self.client.put_item(
            TableName=self.table_name,
            Item={
                **{
                    "key": {"S": key},
                    "value": {"S": value},
                },
                **ttl,
            },
        )

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        raise NotImplementedError
