# Interface between client and the PictureServer

| Version | Date       | Author | Description   |
|---------|------------|--------|---------------|
| v0.0    | 2024-03-17 | Noam Cohen | Initial draft |
| v1.0    | 2025-04-27 | Noam Cohen | Make it pure API|

<hr>

**NOTE:** This Markdown file is best viewed with VisualStudio code (press CTRL shift v)

This document defines the wire protocol between an http client and the server in the project.

The words 'MUST', 'SHALL', 'SHOULD' are as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)

The set of commands supported by the server may increase over time, with a change in the api version.

The server has an API VERSION. The current version is 1. This value MUST be returned in the `/status` endpoint.

In API VERSION 1, the server SHALL use http scheme. Clients MUST NOT follow redirects.

Connection handling: Clients MAY open or close connections at any time; the server does not guarantee persistent or keep-alive behavior.

If the client is browser: No CORS support required.

see [REST API](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)<br>
see [Idempotent commands](https://restfulapi.net/idempotent-rest-apis/)

# The Goal
An http server classifies an image uploaded from a client.

The image can be in one of supported formats.

The client can be *any* http client - for example mobile phone, Safari browser, command line `curl` command, python api call etc. 


## Command format

When sending the image file, use FormData.


### Server response
The server SHALL respond with json body.

 - server SHALL have Content-Type=application/json
 - Response of the server SHALL have a json body. If the response is error, the body SHALL be:
  ```
{"error": {"http_status": number, "message": "some message"}
}
```

The "http_status" field in the error object must exactly match the HTTP response code
The HTTP status itself should also be the same number. (Meaning if for example the "http_status" returned is 400 then the server should send this json with the status code 400 and not 200)


### Response codes
The response codes SHALL be standard HTTP status codes. <br>
Each command specifies the possible status codes.

# Command list 

## Upload image file to inference engine

This endpoint is for uploading an image and waiting until a response is ready.


Endpoint: **POST /upload_image**

Content-Disposition: form-data; name="image"; filename="somepic.png"

Send a form field called `image` of type "form-data" that contains the file you want to upload (for example, `somepic.png`).

Content-Type: image/png    or image/jpeg

Supported image types SHALL be at least PNG and JPEG. 

### Example call
#### GOOD
```
curl -X POST http://localhost/upload_image \
     -H "Content-Type: multipart/form-data" \
     -F "image=@./somepic.png;type=image/png"

```
#### BAD
```
curl -i http://localhost/upload_image -F "image=@./bad.bin"
# HTTP/1.1 400 Bad Request
# Content-Type: application/json
# {"error":{"http_status":400,"message":"Unsupported image format"}}
```

Treat any non-decodable payload as malformed. In this case the server SHALL return 400 and increment the number of failed jobs.

If the file is classified (regardless if the classification is correct), return 200

The server SHALL respond synchronously.

If processing is too slow (e.g. connection to a remote API server failed), the server MUST return 500 with appropriate message.

Timeout handling is not needed.


### Possible Response
200: command processed successfully <br>
400: the input file is malformed (e.g. bad file type)<br>
405: unsupported http method (user called GET)<br>
500: internal server error   <br>

if 200: the json body shall be in the format `{ "matches": [ {"name": string, "score": number}]}`

The "score" represents the confidence in this match. Number SHALL be  0.0 \< score\<= 1.0

*example* 
```
{"matches": [{"name": "tomato", "score": 0.9}, {"name":"carrot", "score": 0.02}]}
```


## Get server status
Endpoint: GET /status <br>


Response: 200

The response body SHALL be in the format:
```
{"status":
  {
    "uptime": number /* seconds */,
    "processed:{
          "success": number,
          "fail": number
    },
    "health": "ok" |"error",
    "api_version": number
  }
}
```


**uptime** is the numbers of seconds since the server started (wallclock time). <br>
The uptime value is in fractional seconds, e.g. 55.6

**success** is the number of jobs completed successfully<br>
**fail** is the number of jobs completed with some error <br>

The "health" SHALL be "ok" if classification can be done, and "error" otherwise.

In this context, a `job` is uploading an image in order to get the classification.
<hr>

### Example
`curl http://localhost/status`

with response
```
"status":
  {
    "uptime": 230.7,
    "processed":{
          "success": 5,
          "fail": 1
    },
    "health": "ok",
    "api_version": 1
  }
```