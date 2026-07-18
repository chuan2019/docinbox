# Sample API Calls - buckets

## Via the FastAPI Webservice

```bash
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X GET http://localhost:8000/healthz | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    40  100    40    0     0   7004      0 --:--:-- --:--:-- --:--:--  8000
{
  "status": "ok",
  "account": "000000000000"
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X GET http://localhost:8000/buckets | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    14  100    14    0     0   3603      0 --:--:-- --:--:-- --:--:--  4666
{
  "buckets": []
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X POST http://localhost:8000/buckets/inbox-uploads | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    27  100    27    0     0   2996      0 --:--:-- --:--:-- --:--:--  3375
{
  "created": "inbox-uploads"
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X GET http://localhost:8000/buckets | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    29  100    29    0     0   6689      0 --:--:-- --:--:-- --:--:--  7250
{
  "buckets": [
    "inbox-uploads"
  ]
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X POST http://localhost:8000/buckets/inbox-uploads-temp | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    32  100    32    0     0   3197      0 --:--:-- --:--:-- --:--:--  3555
{
  "created": "inbox-uploads-temp"
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X GET http://localhost:8000/buckets | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    50  100    50    0     0   9487      0 --:--:-- --:--:-- --:--:-- 10000
{
  "buckets": [
    "inbox-uploads",
    "inbox-uploads-temp"
  ]
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X DELETE http://localhost:8000/buckets/inbox-uploads-temp | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    32  100    32    0     0   6274      0 --:--:-- --:--:-- --:--:--  8000
{
  "deleted": "inbox-uploads-temp"
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ curl -X GET http://localhost:8000/buckets | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    29  100    29    0     0   6868      0 --:--:-- --:--:-- --:--:--  7250
{
  "buckets": [
    "inbox-uploads"
  ]
}
chuan@chuan2025:~/Projects/Document-AI/docinbox$

```

## Via `aws` command line tool

```bash
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 AWS_ENDPOINT_URL=http://localhost:4566
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 ls
2026-07-18 14:47:24 inbox-uploads
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 mb s3://inbox-uploads-tmp
make_bucket: inbox-uploads-tmp
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 ls
2026-07-18 14:47:24 inbox-uploads
2026-07-18 14:57:01 inbox-uploads-tmp
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 rm s3://inbox-uploads-tmp --recursive
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 ls
2026-07-18 14:47:24 inbox-uploads
2026-07-18 14:57:01 inbox-uploads-tmp
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 rb s3://inbox-uploads-tmp
remove_bucket: inbox-uploads-tmp
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$ aws s3 ls
2026-07-18 14:47:24 inbox-uploads
chuan@chuan2025:~/Projects/Document-AI/docinbox$
chuan@chuan2025:~/Projects/Document-AI/docinbox$
```
