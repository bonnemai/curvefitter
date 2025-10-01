NAME="curve-fitter"
docker buildx build --platform linux/arm64 -t "$NAME" .
# docker run --rm -e CURVE_FITTER_LOCAL_SERVER=true -p 8080:8080 "$NAME"

# cat <<'EOF'

# To exercise the image with the AWS Lambda Runtime Interface Emulator (requires the
# aws-lambda-rie binary on your host), first download it, e.g.:

mkdir -p ~/.aws-lambda-rie
curl -Lo ~/.aws-lambda-rie/aws-lambda-rie \
    https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie
chmod +x ~/.aws-lambda-rie/aws-lambda-rie

# Then run:

docker run --rm \
    -p 9000:8080 \
    --env AWS_LAMBDA_RUNTIME_API=localhost:8080 \
    --entrypoint /aws-lambda-rie/aws-lambda-rie \
    -v ~/.aws-lambda-rie:/aws-lambda-rie \
    curve-fitter \
    ./entrypoint.sh app.main.handler

# curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
#     -d '{"httpMethod":"GET","path":"/health"}'


curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -H "Content-Type: application/json" \
  -d '{
        "version": "2.0",
        "routeKey": "GET /",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
          "host": "localhost",
          "user-agent": "curl"
        },
        "requestContext": {
          "accountId": "123456789012",
          "apiId": "local",
          "domainName": "localhost",
          "domainPrefix": "local",
          "http": {
            "method": "GET",
            "path": "/",
            "protocol": "HTTP/1.1",
            "sourceIp": "127.0.0.1",
            "userAgent": "curl"
          },
          "requestId": "test",
          "routeKey": "GET /",
          "stage": "$default",
          "time": "12/Mar/2025:12:00:00 +0000",
          "timeEpoch": 1741435200000
        },
        "isBase64Encoded": false
      }'


# curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
#   -H "Content-Type: application/json" \
#   -d '{
#         "version": "2.0",
#         "routeKey": "GET /health",
#         "rawPath": "/health",
#         "rawQueryString": "",
#         "headers": {
#           "host": "localhost",
#           "user-agent": "curl"
#         },
#         "requestContext": {
#           "accountId": "123456789012",
#           "apiId": "local",
#           "domainName": "localhost",
#           "domainPrefix": "local",
#           "http": {
#             "method": "GET",
#             "path": "/health",
#             "protocol": "HTTP/1.1",
#             "sourceIp": "127.0.0.1",
#             "userAgent": "curl"
#           },
#           "requestId": "test",
#           "routeKey": "GET /health",
#           "stage": "$default",
#           "time": "12/Mar/2025:12:00:00 +0000",
#           "timeEpoch": 1741435200000
#         },
#         "isBase64Encoded": false
#       }'


# EOF
