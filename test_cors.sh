# Preflight:
URL=https://2pzmybbrkdhzf75k6wz24dflua0hbiko.lambda-url.eu-west-2.on.aws
ORIGIN=http://localhost:8001
curl -i -X OPTIONS "${URL}/curves/stream" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: GET" 
  # -H "Access-Control-Request-Headers: content-type, authorization"