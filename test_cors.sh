# Preflight:
curl -i -X OPTIONS "https://your.api.example.com/any/path" \
  -H "Origin: https://your-frontend.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type, authorization"