"""
Side-quest: tail the docinbox table's DynamoDB Stream.
Run with: python -m bootstrap.tail_stream (Ctrl+C to stop)
"""
import time
from app.aws.clients import get_client
from bootstrap.seed import PARAMETERS

def main() -> None:
    table = PARAMETERS["dynamodb/table-name"]
    arn = get_client("dynamodb").describe_table(
        TableName=table
    )["Table"]["LatestStreamArn"]
    streams = get_client("dynamodbstreams")
    shard = streams.describe_stream(
        StreamArn=arn
    )["StreamDescription"]["Shards"][0]
    iterator = streams.get_shard_iterator(
        StreamArn=arn, ShardId=shard["ShardId"],
        ShardIteratorType="LATEST"
    )["ShardIterator"]
    print(f"tailing {arn}\n")
    while True:
        resp = streams.get_records(ShardIterator=iterator, Limit=25)
        for rec in resp["Records"]:
            keys = rec["dynamodb"]["Keys"] # raw wire format: {"S": …}
            print((
                f'{rec["eventName"]:<7} '
                f'{keys["PK"]["S"]:<45} '
                f'{keys["SK"]["S"]}'
            ))
        iterator = resp["NextShardIterator"]
        time.sleep(1)

if __name__ == "__main__":
    main()