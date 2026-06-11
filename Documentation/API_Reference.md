---
title: Alluci Sovereign Agent v0.9.5-rc1
language_tabs:
  - python: Python
  - javascript: JavaScript
language_clients:
  - python: ""
  - javascript: ""
toc_footers: []
includes: []
search: false
highlight_theme: darkula
headingLevel: 2

---

<!-- Generator: Widdershins v4.0.1 -->

<h1 id="alluci-sovereign-agent">Alluci Sovereign Agent v0.9.5-rc1</h1>

> Scroll down for code samples, example requests and responses. Select a language for code samples from the tabs above or the mobile navigation menu.

Sovereign Executive Assistant with Polytopic Manifolds

<h1 id="alluci-sovereign-agent-default">Default</h1>

## Get Monitoring Page

<a id="opIdget_monitoring_page_monitoring__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'text/html'
}

r = requests.get('/monitoring/', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'text/html'
};

fetch('/monitoring/',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /monitoring/`

Serve the premium monitoring UI page.

> Example responses

> 200 Response

```
"string"
```

<h3 id="get-monitoring-page-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|string|

<aside class="success">
This operation does not require authentication
</aside>

## Get Metrics Json

<a id="opIdget_metrics_json_metrics_json_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/metrics/json', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/metrics/json',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /metrics/json`

Expose Prometheus metrics as JSON for HTMX polling.
The output is a dict where each metric name maps to its current value(s).

> Example responses

> 200 Response

```json
null
```

<h3 id="get-metrics-json-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-metrics-json-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Execute Objective

<a id="opIdexecute_objective_api_v1_objective_execute_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'X-Execution-Manifest': 'string'
}

r = requests.post('/api/v1/objective/execute', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "objective": "string",
  "autonomy_level": "SEMI_AUTONOMOUS"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'X-Execution-Manifest':'string'
};

fetch('/api/v1/objective/execute',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/objective/execute`

> Body parameter

```json
{
  "objective": "string",
  "autonomy_level": "SEMI_AUTONOMOUS"
}
```

<h3 id="execute-objective-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|query|string|false|none|
|X-Execution-Manifest|header|any|false|none|
|body|body|[ObjectiveRequest](#schemaobjectiverequest)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="execute-objective-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="execute-objective-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-authentication">Authentication</h1>

## Get Csrf Token

<a id="opIdget_csrf_token_api_v1_auth_csrf_token_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/auth/csrf-token', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/csrf-token',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/auth/csrf-token`

Generates a CSRF token pair.
Returns the token for use in X-CSRF-Token header.
Also sets the signed token in a cookie for double-submit validation.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-csrf-token-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-csrf-token-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Login

<a id="opIdlogin_api_v1_auth_login_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/login', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "key": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/auth/login',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/login`

Sovereign Master Key Authentication.

> Body parameter

```json
{
  "key": "string"
}
```

<h3 id="login-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[LoginRequest](#schemaloginrequest)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="login-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="login-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Logout

<a id="opIdlogout_api_v1_auth_logout_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/logout', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/logout',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/logout`

> Example responses

> 200 Response

```json
null
```

<h3 id="logout-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="logout-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Verusid Login Request

<a id="opIdget_verusid_login_request_api_v1_auth_verusid_login_request_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/auth/verusid/login-request', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/verusid/login-request',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/auth/verusid/login-request`

Generates a full LoginConsentRequest with QR deeplink.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-verusid-login-request-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-verusid-login-request-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Verusid Login Status

<a id="opIdget_verusid_login_status_api_v1_auth_verusid_status__challenge_id__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/auth/verusid/status/{challenge_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/verusid/status/{challenge_id}',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/auth/verusid/status/{challenge_id}`

Checks if a login has been completed for the given challenge_id.

<h3 id="get-verusid-login-status-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|challenge_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-verusid-login-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-verusid-login-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Verusid Webhook

<a id="opIdverusid_webhook_api_v1_auth_verusid_webhook_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/verusid/webhook', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/auth/verusid/webhook',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/verusid/webhook`

Webhook for Verus Mobile to POST the signed LoginConsentResponse.

> Body parameter

```json
{}
```

<h3 id="verusid-webhook-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="verusid-webhook-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="verusid-webhook-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Webauthn Challenge

<a id="opIdget_webauthn_challenge_api_v1_auth_webauthn_challenge_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/auth/webauthn/challenge', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/webauthn/challenge',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/auth/webauthn/challenge`

Generates a cryptographic challenge for WebAuthn/FIDO2.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-webauthn-challenge-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-webauthn-challenge-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Verify Webauthn Response

<a id="opIdverify_webauthn_response_api_v1_auth_webauthn_verify_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/webauthn/verify', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/auth/webauthn/verify',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/webauthn/verify`

Verifies the WebAuthn attestation/assertion using py_webauthn.

> Body parameter

```json
{}
```

<h3 id="verify-webauthn-response-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="verify-webauthn-response-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="verify-webauthn-response-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Webauthn Assertion Challenge

<a id="opIdget_webauthn_assertion_challenge_api_v1_auth_webauthn_assertion_challenge_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/webauthn/assertion/challenge', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/auth/webauthn/assertion/challenge',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/webauthn/assertion/challenge`

Step 1 of WebAuthn login: generate a challenge for an existing registered credential.
The browser sends back credentialId (optional) to restrict which credential to use.

> Body parameter

```json
{}
```

<h3 id="get-webauthn-assertion-challenge-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-webauthn-assertion-challenge-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-webauthn-assertion-challenge-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Verify Webauthn Assertion

<a id="opIdverify_webauthn_assertion_api_v1_auth_webauthn_assertion_verify_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/auth/webauthn/assertion/verify', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/auth/webauthn/assertion/verify',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/auth/webauthn/assertion/verify`

Step 2 of WebAuthn login: verify the signed assertion and issue a JWT.
This is the login path — uses verify_authentication_response.

> Body parameter

```json
{}
```

<h3 id="verify-webauthn-assertion-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="verify-webauthn-assertion-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="verify-webauthn-assertion-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Oauth Authorize

<a id="opIdoauth_authorize_api_v1_auth_oauth_authorize_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/auth/oauth/authorize', params={
  'provider_id': 'string'
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/auth/oauth/authorize?provider_id=string',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/auth/oauth/authorize`

Starts an OAuth 2.0 flow for a specific provider.

<h3 id="oauth-authorize-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|provider_id|query|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="oauth-authorize-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="oauth-authorize-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-task-management">Task Management</h1>

## Get Tasks

<a id="opIdget_tasks_api_v1_tasks_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/tasks', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/tasks',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/tasks`

<h3 id="get-tasks-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|status|query|string|false|none|
|priority|query|any|false|none|
|timeline|query|any|false|none|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-tasks-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-tasks-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Add Task

<a id="opIdadd_task_api_v1_tasks_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/tasks', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "description": "string",
  "completed": false,
  "priority": "URGENT",
  "due_date": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/tasks',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/tasks`

> Body parameter

```json
{
  "description": "string",
  "completed": false,
  "priority": "URGENT",
  "due_date": "string"
}
```

<h3 id="add-task-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|query|string|false|none|
|body|body|[TaskUpdate](#schemataskupdate)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="add-task-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="add-task-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Task

<a id="opIdupdate_task_api_v1_tasks__index__put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/tasks/{index}', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "description": "string",
  "completed": false,
  "priority": "URGENT",
  "due_date": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/tasks/{index}',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/tasks/{index}`

> Body parameter

```json
{
  "description": "string",
  "completed": false,
  "priority": "URGENT",
  "due_date": "string"
}
```

<h3 id="update-task-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|index|path|integer|true|none|
|agent_id|query|string|false|none|
|body|body|[TaskUpdate](#schemataskupdate)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-task-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-task-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Task

<a id="opIddelete_task_api_v1_tasks__index__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/tasks/{index}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/tasks/{index}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/tasks/{index}`

<h3 id="delete-task-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|index|path|integer|true|none|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-task-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-task-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-dag-and-pipeline-runs">DAG & Pipeline Runs</h1>

## List Dag Runs

<a id="opIdlist_dag_runs_api_v1_dag_runs_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/dag/runs', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/dag/runs',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/dag/runs`

<h3 id="list-dag-runs-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|status|query|any|false|none|
|limit|query|integer|false|none|
|offset|query|integer|false|none|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="list-dag-runs-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="list-dag-runs-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-sovereign-memory">Sovereign Memory</h1>

## List Memory

<a id="opIdlist_memory_api_v1_memory_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/memory', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/memory`

<h3 id="list-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|limit|query|integer|false|none|
|offset|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="list-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="list-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Search Memory

<a id="opIdsearch_memory_api_v1_memory_search_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/memory/search', params={
  'q': 'string'
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory/search?q=string',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/memory/search`

<h3 id="search-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|q|query|string|true|none|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="search-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="search-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Store Memory

<a id="opIdstore_memory_api_v1_memory_store_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/memory/store', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/memory/store',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/memory/store`

> Body parameter

```json
{}
```

<h3 id="store-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="store-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="store-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Memory Stats

<a id="opIdget_memory_stats_api_v1_memory_stats_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/memory/stats', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory/stats',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/memory/stats`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-memory-stats-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-memory-stats-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Memory Entry

<a id="opIddelete_memory_entry_api_v1_memory__entry_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/memory/{entry_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory/{entry_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/memory/{entry_id}`

<h3 id="delete-memory-entry-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|entry_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-memory-entry-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-memory-entry-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Trigger Consolidation

<a id="opIdtrigger_consolidation_api_v1_memory_consolidate_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/memory/consolidate', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory/consolidate',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/memory/consolidate`

Manually trigger the H-LSM consolidation cycle (Decay, Promotion, Pruning).

> Example responses

> 200 Response

```json
null
```

<h3 id="trigger-consolidation-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="trigger-consolidation-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Pin Memory

<a id="opIdpin_memory_api_v1_memory__entry_id__pin_patch"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.patch('/api/v1/memory/{entry_id}/pin', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/memory/{entry_id}/pin',
{
  method: 'PATCH',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PATCH /api/v1/memory/{entry_id}/pin`

> Body parameter

```json
{}
```

<h3 id="pin-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|entry_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="pin-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="pin-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Tag Memory

<a id="opIdtag_memory_api_v1_memory__entry_id__tags_patch"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.patch('/api/v1/memory/{entry_id}/tags', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/memory/{entry_id}/tags',
{
  method: 'PATCH',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PATCH /api/v1/memory/{entry_id}/tags`

> Body parameter

```json
{}
```

<h3 id="tag-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|entry_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="tag-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="tag-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Promote Memory

<a id="opIdpromote_memory_api_v1_memory__entry_id__promote_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/memory/{entry_id}/promote', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/memory/{entry_id}/promote',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/memory/{entry_id}/promote`

<h3 id="promote-memory-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|entry_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="promote-memory-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="promote-memory-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-sovereign-goals">Sovereign Goals</h1>

## List Goals

<a id="opIdlist_goals_api_v1_goals__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/goals/', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/goals/',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/goals/`

List all goals, optionally filtered by status.

<h3 id="list-goals-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|status|query|any|false|none|

> Example responses

> 200 Response

```json
[
  {
    "id": 0,
    "title": "string",
    "description": "string",
    "status": "string",
    "created_at": "2019-08-24T14:15:22Z"
  }
]
```

<h3 id="list-goals-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="list-goals-responseschema">Response Schema</h3>

Status Code **200**

*Response List Goals Api V1 Goals  Get*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|Response List Goals Api V1 Goals  Get|[[GoalRecord](#schemagoalrecord)]|false|none|none|
|» GoalRecord|[GoalRecord](#schemagoalrecord)|false|none|none|
|»» id|integer|false|none|none|
|»» title|string|true|none|none|
|»» description|any|false|none|none|

*anyOf*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»»» *anonymous*|string|false|none|none|

*or*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»»» *anonymous*|null|false|none|none|

*continued*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»» status|string|true|none|none|
|»» created_at|string(date-time)|false|none|none|

<aside class="success">
This operation does not require authentication
</aside>

## Create Goal

<a id="opIdcreate_goal_api_v1_goals__post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/goals/', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "title": "string",
  "description": "string",
  "priority": "MEDIUM"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/goals/',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/goals/`

> Body parameter

```json
{
  "title": "string",
  "description": "string",
  "priority": "MEDIUM"
}
```

<h3 id="create-goal-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[Body_create_goal_api_v1_goals__post](#schemabody_create_goal_api_v1_goals__post)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="create-goal-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="create-goal-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Goal

<a id="opIdget_goal_api_v1_goals__goal_id__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/goals/{goal_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/goals/{goal_id}',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/goals/{goal_id}`

Get details of a specific goal.

<h3 id="get-goal-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|goal_id|path|integer|true|none|

> Example responses

> 200 Response

```json
{
  "id": 0,
  "title": "string",
  "description": "string",
  "status": "string",
  "created_at": "2019-08-24T14:15:22Z"
}
```

<h3 id="get-goal-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[GoalRecord](#schemagoalrecord)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<aside class="success">
This operation does not require authentication
</aside>

## Update Goal

<a id="opIdupdate_goal_api_v1_goals__goal_id__patch"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.patch('/api/v1/goals/{goal_id}', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "status": "string",
  "progress": 0
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/goals/{goal_id}',
{
  method: 'PATCH',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PATCH /api/v1/goals/{goal_id}`

> Body parameter

```json
{
  "status": "string",
  "progress": 0
}
```

<h3 id="update-goal-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|goal_id|path|integer|true|none|
|body|body|[Body_update_goal_api_v1_goals__goal_id__patch](#schemabody_update_goal_api_v1_goals__goal_id__patch)|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-goal-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-goal-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Goal

<a id="opIddelete_goal_api_v1_goals__goal_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/goals/{goal_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/goals/{goal_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/goals/{goal_id}`

<h3 id="delete-goal-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|goal_id|path|integer|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-goal-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-goal-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-sop-engine">SOP Engine</h1>

## List Sops

<a id="opIdlist_sops_api_v1_sops__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/sops/', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/sops/',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/sops/`

List all active Standard Operating Procedures.

> Example responses

> 200 Response

```json
[
  {
    "id": 0,
    "name": "string",
    "description": "string",
    "steps": {},
    "is_active": true,
    "created_at": "2019-08-24T14:15:22Z"
  }
]
```

<h3 id="list-sops-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="list-sops-responseschema">Response Schema</h3>

Status Code **200**

*Response List Sops Api V1 Sops  Get*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|Response List Sops Api V1 Sops  Get|[[SOPRecord](#schemasoprecord)]|false|none|none|
|» SOPRecord|[SOPRecord](#schemasoprecord)|false|none|none|
|»» id|integer|false|none|none|
|»» name|string|true|none|none|
|»» description|any|false|none|none|

*anyOf*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»»» *anonymous*|string|false|none|none|

*or*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»»» *anonymous*|null|false|none|none|

*continued*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|»» steps|object|false|none|none|
|»» is_active|boolean|false|none|none|
|»» created_at|string(date-time)|false|none|none|

<aside class="success">
This operation does not require authentication
</aside>

## Register Sop

<a id="opIdregister_sop_api_v1_sops__post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/sops/', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "name": "string",
  "description": "string",
  "steps": [
    {}
  ]
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/sops/',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/sops/`

> Body parameter

```json
{
  "name": "string",
  "description": "string",
  "steps": [
    {}
  ]
}
```

<h3 id="register-sop-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[Body_register_sop_api_v1_sops__post](#schemabody_register_sop_api_v1_sops__post)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="register-sop-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="register-sop-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Sop

<a id="opIdget_sop_api_v1_sops__sop_id__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/sops/{sop_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/sops/{sop_id}',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/sops/{sop_id}`

Get details of a specific SOP.

<h3 id="get-sop-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|sop_id|path|integer|true|none|

> Example responses

> 200 Response

```json
{
  "id": 0,
  "name": "string",
  "description": "string",
  "steps": {},
  "is_active": true,
  "created_at": "2019-08-24T14:15:22Z"
}
```

<h3 id="get-sop-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[SOPRecord](#schemasoprecord)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<aside class="success">
This operation does not require authentication
</aside>

## Execute Sop

<a id="opIdexecute_sop_api_v1_sops__sop_id__execute_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/sops/{sop_id}/execute', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/sops/{sop_id}/execute',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/sops/{sop_id}/execute`

> Body parameter

```json
{}
```

<h3 id="execute-sop-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|sop_id|path|integer|true|none|
|body|body|any|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="execute-sop-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="execute-sop-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-vault-operations">Vault Operations</h1>

## Rotate Vault Keys

<a id="opIdrotate_vault_keys_api_v1_vault_rotate_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/vault/rotate', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/vault/rotate',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/vault/rotate`

> Body parameter

```json
{}
```

<h3 id="rotate-vault-keys-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="rotate-vault-keys-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="rotate-vault-keys-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Export RSA identity key (encrypted)

<a id="opIdexport_identity_pem_api_v1_vault_export_identity_pem_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/vault/export-identity-pem', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "export_passphrase": "stringstringstri"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/vault/export-identity-pem',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/vault/export-identity-pem`

Returns the vault RSA private key encrypted with your export passphrase.

> Body parameter

```json
{
  "export_passphrase": "stringstringstri"
}
```

<h3 id="export-rsa-identity-key-(encrypted)-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[ExportPemRequest](#schemaexportpemrequest)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="export-rsa-identity-key-(encrypted)-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="export-rsa-identity-key-(encrypted)-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Flush Vault

<a id="opIdflush_vault_api_v1_vault_flush_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/vault/flush', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/vault/flush',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/vault/flush`

> Example responses

> 200 Response

```json
null
```

<h3 id="flush-vault-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="flush-vault-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Check Health

<a id="opIdcheck_health_api_v1_check_health_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/check-health', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/check-health',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/check-health`

Triggers a health check across all model manifolds.

> Example responses

> 200 Response

```json
null
```

<h3 id="check-health-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="check-health-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Vault Keys

<a id="opIdget_vault_keys_api_v1_vault_keys_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/vault/keys', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/vault/keys',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/vault/keys`

Retrieves masked API keys for UI display. Prevents raw secret exposure.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-vault-keys-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-vault-keys-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Save Vault Keys

<a id="opIdsave_vault_keys_api_v1_vault_keys_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/vault/keys', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/vault/keys',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/vault/keys`

Persists API keys, merging with existing values to preserve masked secrets.

> Body parameter

```json
{}
```

<h3 id="save-vault-keys-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="save-vault-keys-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="save-vault-keys-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Backup Status

<a id="opIdget_backup_status_api_v1_vault_backup_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/vault/backup/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/vault/backup/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/vault/backup/status`

Aggregates per‑vault backup status strings for UI polling.
Returns a mapping of vault identifiers to their latest status.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-backup-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-backup-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-bridge-channels">Bridge Channels</h1>

## List Channels

<a id="opIdlist_channels_api_v1_channels_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels`

> Example responses

> 200 Response

```json
null
```

<h3 id="list-channels-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="list-channels-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Channel Availability

<a id="opIdget_channel_availability_api_v1_channels_availability_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/availability', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/availability',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/availability`

Returns platform availability status for all registered bridge adapters.
Used by BridgeCenter to show which bridges can be configured on this host.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-channel-availability-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-channel-availability-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Channel Config

<a id="opIdget_channel_config_api_v1_channels__channel_id__config_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/{channel_id}/config', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/config',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/{channel_id}/config`

<h3 id="get-channel-config-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-channel-config-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-channel-config-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Channel Config

<a id="opIdupdate_channel_config_api_v1_channels__channel_id__config_put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/channels/{channel_id}/config', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/config',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/channels/{channel_id}/config`

> Body parameter

```json
{}
```

<h3 id="update-channel-config-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-channel-config-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-channel-config-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Connect Channel

<a id="opIdconnect_channel_api_v1_channels__channel_id__connect_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/{channel_id}/connect', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/connect',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/{channel_id}/connect`

<h3 id="connect-channel-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="connect-channel-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="connect-channel-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Toggle Channel

<a id="opIdtoggle_channel_api_v1_channels__channel_id__toggle_put"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.put('/api/v1/channels/{channel_id}/toggle', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/toggle',
{
  method: 'PUT',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/channels/{channel_id}/toggle`

<h3 id="toggle-channel-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="toggle-channel-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="toggle-channel-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Send

<a id="opIdchannel_send_api_v1_channels__channel_id__send_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/{channel_id}/send', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/send',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/{channel_id}/send`

> Body parameter

```json
{}
```

<h3 id="channel-send-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-send-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-send-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Upload

<a id="opIdchannel_upload_api_v1_channels__channel_id__upload_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/{channel_id}/upload', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/upload',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/{channel_id}/upload`

> Body parameter

```json
{}
```

<h3 id="channel-upload-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-upload-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-upload-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Health

<a id="opIdchannel_health_api_v1_channels__channel_id__health_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/{channel_id}/health', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/health',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/{channel_id}/health`

Returns the real-time connection health of a specific bridge.
Used by BridgeCenter frontend to show live status indicators.

<h3 id="channel-health-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-health-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-health-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Unread

<a id="opIdchannel_unread_api_v1_channels__channel_id__unread_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/{channel_id}/unread', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/unread',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/{channel_id}/unread`

Fetch unread messages from a bridge's inbox.
Used by the agent's inbound message polling logic.

<h3 id="channel-unread-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-unread-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-unread-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Social Task

<a id="opIdchannel_social_task_api_v1_channels__channel_id__social_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/{channel_id}/social', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/social',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/{channel_id}/social`

> Body parameter

```json
{}
```

<h3 id="channel-social-task-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-social-task-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-social-task-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Channel Enterprise Task

<a id="opIdchannel_enterprise_task_api_v1_channels__channel_id__enterprise_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/{channel_id}/enterprise', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/{channel_id}/enterprise',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/{channel_id}/enterprise`

> Body parameter

```json
{}
```

<h3 id="channel-enterprise-task-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|channel_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="channel-enterprise-task-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="channel-enterprise-task-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## All Channels Health

<a id="opIdall_channels_health_api_v1_channels_health_all_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/health/all', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/health/all',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/health/all`

Returns connection health for every registered bridge simultaneously.

> Example responses

> 200 Response

```json
null
```

<h3 id="all-channels-health-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="all-channels-health-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Iwatch Status

<a id="opIdiwatch_status_api_v1_channels_iwatch_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/iwatch/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/iwatch/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/iwatch/status`

> Example responses

> 200 Response

```json
null
```

<h3 id="iwatch-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="iwatch-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Iwatch Pairing Qr

<a id="opIdiwatch_pairing_qr_api_v1_channels_iwatch_pairing_qr_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/iwatch/pairing-qr', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/iwatch/pairing-qr',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/iwatch/pairing-qr`

Generate TOTP seed and QR payload for Watch pairing.

> Example responses

> 200 Response

```json
null
```

<h3 id="iwatch-pairing-qr-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="iwatch-pairing-qr-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Iwatch Pair

<a id="opIdiwatch_pair_api_v1_channels_iwatch_pair_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/iwatch/pair', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "property1": "string",
  "property2": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/iwatch/pair',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/iwatch/pair`

> Body parameter

```json
{
  "property1": "string",
  "property2": "string"
}
```

<h3 id="iwatch-pair-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|
|» **additionalProperties**|body|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="iwatch-pair-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="iwatch-pair-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Ingest Iwatch Biometrics

<a id="opIdingest_iwatch_biometrics_api_v1_channels_iwatch_biometrics_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/iwatch/biometrics', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/iwatch/biometrics',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/iwatch/biometrics`

> Example responses

> 200 Response

```json
null
```

<h3 id="ingest-iwatch-biometrics-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="ingest-iwatch-biometrics-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Iwatch Telemetry

<a id="opIdget_iwatch_telemetry_api_v1_channels_iwatch_telemetry_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/iwatch/telemetry', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/iwatch/telemetry',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/iwatch/telemetry`

Retrieve recent telemetry samples from the iWatch bridge buffer.

<h3 id="get-iwatch-telemetry-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-iwatch-telemetry-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-iwatch-telemetry-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Wechat Qr Init

<a id="opIdwechat_qr_init_api_v1_channels_wechat_qr_init_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/wechat/qr-init', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/wechat/qr-init',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/wechat/qr-init`

Generate WeCom OAuth QR URL for workspace login.

> Example responses

> 200 Response

```json
null
```

<h3 id="wechat-qr-init-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="wechat-qr-init-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Oauth Callback

<a id="opIdoauth_callback_api_v1_oauth__bridge_id__callback_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/{bridge_id}/callback', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/{bridge_id}/callback',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/{bridge_id}/callback`

Generic OAuth callback endpoint for all OAuth-based bridges.

<h3 id="oauth-callback-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|bridge_id|path|string|true|none|
|code|query|string|false|none|
|state|query|string|false|none|
|error|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="oauth-callback-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="oauth-callback-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Wechat Webhook Verify

<a id="opIdwechat_webhook_verify_api_v1_webhook_wechat_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/webhook/wechat', params={
  'msg_signature': 'string',  'timestamp': 'string',  'nonce': 'string'
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/wechat?msg_signature=string&timestamp=string&nonce=string',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/webhook/wechat`

<h3 id="wechat-webhook-verify-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|msg_signature|query|string|true|none|
|timestamp|query|string|true|none|
|nonce|query|string|true|none|
|echostr|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="wechat-webhook-verify-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="wechat-webhook-verify-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Wechat Webhook Post

<a id="opIdwechat_webhook_post_api_v1_webhook_wechat_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/wechat', params={
  'msg_signature': 'string',  'timestamp': 'string',  'nonce': 'string'
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/wechat?msg_signature=string&timestamp=string&nonce=string',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/wechat`

<h3 id="wechat-webhook-post-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|msg_signature|query|string|true|none|
|timestamp|query|string|true|none|
|nonce|query|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="wechat-webhook-post-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="wechat-webhook-post-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Slack Oauth Start

<a id="opIdslack_oauth_start_api_v1_oauth_slack_start_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/slack/start', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/slack/start',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/slack/start`

> Example responses

> 200 Response

```json
null
```

<h3 id="slack-oauth-start-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="slack-oauth-start-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Slack Webhook

<a id="opIdslack_webhook_api_v1_webhook_slack_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/slack', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/slack',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/slack`

> Example responses

> 200 Response

```json
null
```

<h3 id="slack-webhook-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="slack-webhook-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Whatsapp Webhook Verify

<a id="opIdwhatsapp_webhook_verify_api_v1_webhook_whatsapp_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/webhook/whatsapp', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/whatsapp',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/webhook/whatsapp`

<h3 id="whatsapp-webhook-verify-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hub.mode|query|string|false|none|
|hub.verify_token|query|string|false|none|
|hub.challenge|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="whatsapp-webhook-verify-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="whatsapp-webhook-verify-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Whatsapp Webhook Post

<a id="opIdwhatsapp_webhook_post_api_v1_webhook_whatsapp_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/whatsapp', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/whatsapp',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/whatsapp`

> Example responses

> 200 Response

```json
null
```

<h3 id="whatsapp-webhook-post-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="whatsapp-webhook-post-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Instagram Oauth Start

<a id="opIdinstagram_oauth_start_api_v1_oauth_instagram_start_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/instagram/start', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/instagram/start',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/instagram/start`

> Example responses

> 200 Response

```json
null
```

<h3 id="instagram-oauth-start-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="instagram-oauth-start-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Instagram Webhook Verify

<a id="opIdinstagram_webhook_verify_api_v1_webhook_instagram_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/webhook/instagram', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/instagram',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/webhook/instagram`

<h3 id="instagram-webhook-verify-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hub.mode|query|string|false|none|
|hub.verify_token|query|string|false|none|
|hub.challenge|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="instagram-webhook-verify-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="instagram-webhook-verify-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Instagram Webhook Post

<a id="opIdinstagram_webhook_post_api_v1_webhook_instagram_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/instagram', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/instagram',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/instagram`

> Example responses

> 200 Response

```json
null
```

<h3 id="instagram-webhook-post-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="instagram-webhook-post-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Facebook Oauth Start

<a id="opIdfacebook_oauth_start_api_v1_oauth_facebook_start_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/facebook/start', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/facebook/start',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/facebook/start`

> Example responses

> 200 Response

```json
null
```

<h3 id="facebook-oauth-start-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="facebook-oauth-start-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Facebook Webhook Verify

<a id="opIdfacebook_webhook_verify_api_v1_webhook_facebook_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/webhook/facebook', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/facebook',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/webhook/facebook`

<h3 id="facebook-webhook-verify-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hub.mode|query|string|false|none|
|hub.verify_token|query|string|false|none|
|hub.challenge|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="facebook-webhook-verify-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="facebook-webhook-verify-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Facebook Webhook Post

<a id="opIdfacebook_webhook_post_api_v1_webhook_facebook_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/facebook', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/facebook',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/facebook`

> Example responses

> 200 Response

```json
null
```

<h3 id="facebook-webhook-post-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="facebook-webhook-post-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## X Oauth Start

<a id="opIdx_oauth_start_api_v1_oauth_x_start_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/x/start', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/x/start',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/x/start`

> Example responses

> 200 Response

```json
null
```

<h3 id="x-oauth-start-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="x-oauth-start-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Msteams Oauth Start

<a id="opIdmsteams_oauth_start_api_v1_oauth_msteams_start_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/oauth/msteams/start', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/oauth/msteams/start',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/oauth/msteams/start`

> Example responses

> 200 Response

```json
null
```

<h3 id="msteams-oauth-start-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="msteams-oauth-start-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Msteams Bot Activity

<a id="opIdmsteams_bot_activity_api_v1_webhook_msteams_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/msteams', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/msteams',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/msteams`

> Example responses

> 200 Response

```json
null
```

<h3 id="msteams-bot-activity-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="msteams-bot-activity-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Telegram Webhook

<a id="opIdtelegram_webhook_api_v1_webhook_telegram__token__post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/telegram/{token}', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/webhook/telegram/{token}',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/telegram/{token}`

Receives inbound updates from Telegram Bot API.

> Body parameter

```json
{}
```

<h3 id="telegram-webhook-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|token|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="telegram-webhook-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="telegram-webhook-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Google Chat Event

<a id="opIdgoogle_chat_event_api_v1_webhook_google_chat_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/webhook/google_chat', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/webhook/google_chat',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/webhook/google_chat`

> Example responses

> 200 Response

```json
null
```

<h3 id="google-chat-event-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="google-chat-event-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Iphone Pair

<a id="opIdiphone_pair_api_v1_channels_iphone_pair_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/iphone/pair', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "property1": "string",
  "property2": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/iphone/pair',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/iphone/pair`

> Body parameter

```json
{
  "property1": "string",
  "property2": "string"
}
```

<h3 id="iphone-pair-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|
|» **additionalProperties**|body|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="iphone-pair-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="iphone-pair-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Icloud Imessage Permission

<a id="opIdicloud_imessage_permission_api_v1_channels_imessage_permission_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/channels/imessage/permission', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/channels/imessage/permission',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/channels/imessage/permission`

Checks if the agent has Full Disk Access to read chat.db (macOS).

> Example responses

> 200 Response

```json
null
```

<h3 id="icloud-imessage-permission-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="icloud-imessage-permission-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Webchat Launch

<a id="opIdwebchat_launch_api_v1_channels_webchat_launch_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/webchat/launch', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "property1": "string",
  "property2": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/webchat/launch',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/webchat/launch`

> Body parameter

```json
{
  "property1": "string",
  "property2": "string"
}
```

<h3 id="webchat-launch-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|
|» **additionalProperties**|body|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="webchat-launch-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="webchat-launch-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Icloud 2Fa

<a id="opIdicloud_2fa_api_v1_channels_icloud_2fa_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/icloud/2fa', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "property1": "string",
  "property2": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/icloud/2fa',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/icloud/2fa`

> Body parameter

```json
{
  "property1": "string",
  "property2": "string"
}
```

<h3 id="icloud-2fa-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|
|» **additionalProperties**|body|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="icloud-2fa-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="icloud-2fa-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Webchat Session Capture

<a id="opIdwebchat_session_capture_api_v1_channels_webchat_session__id__capture_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/channels/webchat/session/{id}/capture', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/channels/webchat/session/{id}/capture',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/channels/webchat/session/{id}/capture`

> Body parameter

```json
{}
```

<h3 id="webchat-session-capture-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="webchat-session-capture-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="webchat-session-capture-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Agent Subscriptions

<a id="opIdget_agent_subscriptions_api_v1_agents__agent_id__subscriptions_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/agents/{agent_id}/subscriptions', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}/subscriptions',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/agents/{agent_id}/subscriptions`

Fetch all channel subscription states for a specific agent.

<h3 id="get-agent-subscriptions-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-agent-subscriptions-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-agent-subscriptions-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Agent Subscription

<a id="opIdupdate_agent_subscription_api_v1_agents__agent_id__subscriptions_put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/agents/{agent_id}/subscriptions', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}/subscriptions',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/agents/{agent_id}/subscriptions`

> Body parameter

```json
{}
```

<h3 id="update-agent-subscription-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-agent-subscription-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-agent-subscription-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Agent Subscription

<a id="opIddelete_agent_subscription_api_v1_agents__agent_id__subscriptions__channel_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/agents/{agent_id}/subscriptions/{channel_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}/subscriptions/{channel_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/agents/{agent_id}/subscriptions/{channel_id}`

<h3 id="delete-agent-subscription-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|
|channel_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-agent-subscription-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-agent-subscription-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-voice-and-audio">Voice & Audio</h1>

## Transcribe Voice

<a id="opIdtranscribe_voice_api_v1_voice_transcribe_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'multipart/form-data',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/voice/transcribe', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "file": "string"
}';
const headers = {
  'Content-Type':'multipart/form-data',
  'Accept':'application/json'
};

fetch('/api/v1/voice/transcribe',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/voice/transcribe`

> Body parameter

```yaml
file: string

```

<h3 id="transcribe-voice-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[Body_transcribe_voice_api_v1_voice_transcribe_post](#schemabody_transcribe_voice_api_v1_voice_transcribe_post)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="transcribe-voice-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="transcribe-voice-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Synthesise Voice

<a id="opIdsynthesise_voice_api_v1_voice_synthesise_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/voice/synthesise', params={
  'text': 'string'
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/voice/synthesise?text=string',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/voice/synthesise`

Synthesise text to speech using local Piper bridge (P1-007).

<h3 id="synthesise-voice-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|text|query|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="synthesise-voice-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="synthesise-voice-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-cron-scheduler">Cron Scheduler</h1>

## List Cron Jobs

<a id="opIdlist_cron_jobs_api_v1_cron_jobs_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/cron/jobs', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/cron/jobs',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/cron/jobs`

List all cron jobs.

<h3 id="list-cron-jobs-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="list-cron-jobs-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="list-cron-jobs-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Create Cron Job

<a id="opIdcreate_cron_job_api_v1_cron_jobs_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/cron/jobs', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/cron/jobs',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/cron/jobs`

> Body parameter

```json
{}
```

<h3 id="create-cron-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|query|string|false|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="create-cron-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="create-cron-job-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Cron Job

<a id="opIdget_cron_job_api_v1_cron_jobs__job_id__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/cron/jobs/{job_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/cron/jobs/{job_id}',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/cron/jobs/{job_id}`

Get a specific cron job.

<h3 id="get-cron-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|job_id|path|integer|true|none|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-cron-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-cron-job-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Cron Job

<a id="opIddelete_cron_job_api_v1_cron_jobs__job_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/cron/jobs/{job_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/cron/jobs/{job_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/cron/jobs/{job_id}`

<h3 id="delete-cron-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|job_id|path|integer|true|none|
|agent_id|query|string|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-cron-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-cron-job-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-wallet-and-defi">Wallet & DeFi</h1>

## Get Wallet Status

<a id="opIdget_wallet_status_api_v1_wallet_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/wallet/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/wallet/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/wallet/status`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-wallet-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-wallet-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Wallet Balance

<a id="opIdget_wallet_balance_api_v1_wallet_balance_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/wallet/balance', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/wallet/balance',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/wallet/balance`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-wallet-balance-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-wallet-balance-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Wallet Send

<a id="opIdwallet_send_api_v1_wallet_send_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/wallet/send', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/wallet/send',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/wallet/send`

> Body parameter

```json
{}
```

<h3 id="wallet-send-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="wallet-send-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="wallet-send-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Mining Status

<a id="opIdget_mining_status_api_v1_wallet_mining_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/wallet/mining', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/wallet/mining',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/wallet/mining`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-mining-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-mining-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Node Status

<a id="opIdget_node_status_api_v1_wallet_node_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/wallet/node/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/wallet/node/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/wallet/node/status`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-node-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-node-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Wallet Node Action

<a id="opIdwallet_node_action_api_v1_wallet_node_action_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/wallet/node/action', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/wallet/node/action',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/wallet/node/action`

> Body parameter

```json
{}
```

<h3 id="wallet-node-action-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="wallet-node-action-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="wallet-node-action-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-telemetry">Telemetry</h1>

## Post Telemetry

<a id="opIdpost_telemetry_api_v1_telemetry_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/telemetry', params={
  'extra_data': null
}, headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/telemetry',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/telemetry`

Ingests biometric telemetry from companion devices (Apple Watch, etc.)
CSRF-protected via the singleton pattern.

<h3 id="post-telemetry-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hr|query|any|false|none|
|hrv|query|any|false|none|
|gsr|query|any|false|none|
|respiratory_rate|query|any|false|none|
|stress_score|query|any|false|none|
|valence|query|any|false|none|
|arousal|query|any|false|none|
|focus|query|any|false|none|
|device_id|query|any|false|none|
|extra_data|query|any|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="post-telemetry-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="post-telemetry-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-system-status">System Status</h1>

## Health

<a id="opIdhealth_api_v1_health_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/health', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/health',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/health`

Public Kubernetes-style liveness probe.

> Example responses

> 200 Response

```json
null
```

<h3 id="health-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="health-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Detailed Health

<a id="opIdget_detailed_health_api_v1_system_health_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/system/health', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/health',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/system/health`

Runs diagnostic checks across primary modules for the Health dashboard.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-detailed-health-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-detailed-health-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Readiness Check

<a id="opIdreadiness_check_api_v1_ready_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/ready', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/ready',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/ready`

Public readiness check for Kubernetes health.

> Example responses

> 200 Response

```json
null
```

<h3 id="readiness-check-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="readiness-check-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Api Readiness Check

<a id="opIdapi_readiness_check_api_v1_system_ready_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/system/ready', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/ready',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/system/ready`

Protected readiness check.

> Example responses

> 200 Response

```json
null
```

<h3 id="api-readiness-check-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="api-readiness-check-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get System Status

<a id="opIdget_system_status_api_v1_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/status`

High-level system status and resource metrics.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-system-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-system-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Prometheus Metrics

<a id="opIdget_prometheus_metrics_api_v1_metrics_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'text/plain'
}

r = requests.get('/api/v1/metrics', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'text/plain'
};

fetch('/api/v1/metrics',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/metrics`

Prometheus-compatible metrics endpoint.

> Example responses

> 200 Response

```
"string"
```

<h3 id="get-prometheus-metrics-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|string|

<aside class="success">
This operation does not require authentication
</aside>

## Get Audit Ledger

<a id="opIdget_audit_ledger_api_v1_audit_ledger_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/audit/ledger', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/audit/ledger',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/audit/ledger`

<h3 id="get-audit-ledger-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|limit|query|integer|false|none|
|offset|query|integer|false|none|
|status|query|any|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-audit-ledger-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-audit-ledger-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Add Audit Entry

<a id="opIdadd_audit_entry_api_v1_audit_entry_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/audit/entry', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "id": "string",
  "event": "string",
  "details": "",
  "status": "INFO",
  "timestamp": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/audit/entry',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/audit/entry`

> Body parameter

```json
{
  "id": "string",
  "event": "string",
  "details": "",
  "status": "INFO",
  "timestamp": "string"
}
```

<h3 id="add-audit-entry-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[AuditEntry](#schemaauditentry)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="add-audit-entry-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="add-audit-entry-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Pcl Status

<a id="opIdget_pcl_status_api_v1_system_pcl_status_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/system/pcl/status', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/pcl/status',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/system/pcl/status`

Retrieve detailed PCL engine status, recent opportunities, and cycles.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-pcl-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-pcl-status-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Trigger Pcl Cycle

<a id="opIdtrigger_pcl_cycle_api_v1_system_pcl_cycle_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/system/pcl/cycle', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/pcl/cycle',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/system/pcl/cycle`

Manually trigger a PCL cognitive cycle immediately.

> Example responses

> 200 Response

```json
null
```

<h3 id="trigger-pcl-cycle-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="trigger-pcl-cycle-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Pcl Opportunities

<a id="opIdget_pcl_opportunities_api_v1_system_pcl_opportunities_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/system/pcl/opportunities', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/pcl/opportunities',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/system/pcl/opportunities`

Retrieve historical PCL opportunities from the database.

<h3 id="get-pcl-opportunities-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|limit|query|integer|false|none|
|actioned|query|any|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-pcl-opportunities-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-pcl-opportunities-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Recovery Phrase

<a id="opIdget_recovery_phrase_api_v1_system_recovery_phrase_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/system/recovery-phrase', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/system/recovery-phrase',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/system/recovery-phrase`

Returns the BIP-39 recovery phrase for the current master key.
Requires active session and CSRF validation for high-security read.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-recovery-phrase-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-recovery-phrase-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-sessions-and-agents">Sessions & Agents</h1>

## Get Current Session

<a id="opIdget_current_session_api_v1_session_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/session', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/session',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/session`

Returns the current user context (soul manifest + bridge connections) for frontend hydration.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-current-session-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-current-session-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## List Sessions

<a id="opIdlist_sessions_api_v1_sessions_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/sessions', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/sessions',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/sessions`

List all active and historical sessions.

<h3 id="list-sessions-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|start|query|any|false|none|
|end|query|any|false|none|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="list-sessions-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="list-sessions-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Session Config

<a id="opIdget_session_config_api_v1_sessions__session_key__config_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/sessions/{session_key}/config', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/sessions/{session_key}/config',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/sessions/{session_key}/config`

Get per-session configuration overrides.

<h3 id="get-session-config-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|session_key|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-session-config-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-session-config-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Agents

<a id="opIdget_agents_api_v1_agents_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/agents', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/agents`

Returns all AgentRecord entries from the database.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-agents-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-agents-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Create Agent

<a id="opIdcreate_agent_api_v1_agents_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/agents', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/agents',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/agents`

> Body parameter

```json
{}
```

<h3 id="create-agent-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="create-agent-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="create-agent-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Agent

<a id="opIdget_agent_api_v1_agents__agent_id__get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/agents/{agent_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/agents/{agent_id}`

Return a single agent by ID.

<h3 id="get-agent-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-agent-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-agent-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Agent

<a id="opIdupdate_agent_api_v1_agents__agent_id__put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/agents/{agent_id}', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/agents/{agent_id}`

> Body parameter

```json
{}
```

<h3 id="update-agent-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-agent-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-agent-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Agent

<a id="opIddelete_agent_api_v1_agents__agent_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/agents/{agent_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/agents/{agent_id}`

<h3 id="delete-agent-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-agent-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-agent-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delegate To Agent

<a id="opIddelegate_to_agent_api_v1_agents_delegate_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/agents/delegate', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "agent_id": "string",
  "task": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/agents/delegate',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/agents/delegate`

> Body parameter

```json
{
  "agent_id": "string",
  "task": "string"
}
```

<h3 id="delegate-to-agent-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[Body_delegate_to_agent_api_v1_agents_delegate_post](#schemabody_delegate_to_agent_api_v1_agents_delegate_post)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delegate-to-agent-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delegate-to-agent-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Agent Heartbeat History

<a id="opIdget_agent_heartbeat_history_api_v1_agents__agent_id__heartbeat_history_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/agents/{agent_id}/heartbeat/history', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/agents/{agent_id}/heartbeat/history',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/agents/{agent_id}/heartbeat/history`

Recent heartbeat execution history for a specific agent.

<h3 id="get-agent-heartbeat-history-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|agent_id|path|string|true|none|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-agent-heartbeat-history-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-agent-heartbeat-history-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Root Heartbeat History

<a id="opIdget_root_heartbeat_history_api_v1_heartbeat_history_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/heartbeat/history', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/heartbeat/history',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/heartbeat/history`

Recent heartbeat execution history for the root agent.

<h3 id="get-root-heartbeat-history-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|limit|query|integer|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="get-root-heartbeat-history-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-root-heartbeat-history-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-system-configuration">System Configuration</h1>

## Get Config

<a id="opIdget_config_api_v1_config_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/config', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/config',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/config`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-config-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-config-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Config

<a id="opIdupdate_config_api_v1_config_put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/config', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/config',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/config`

> Body parameter

```json
{}
```

<h3 id="update-config-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-config-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-config-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Config Schema

<a id="opIdget_config_schema_api_v1_config_schema_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/config/schema', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/config/schema',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/config/schema`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-config-schema-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-config-schema-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-admin">admin</h1>

## Get Allowed Hosts

<a id="opIdget_allowed_hosts_api_v1_egress_hosts_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/egress/hosts', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/egress/hosts',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/egress/hosts`

> Example responses

> 200 Response

```json
{
  "hosts": [
    "string"
  ]
}
```

<h3 id="get-allowed-hosts-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[AllowedHosts](#schemaallowedhosts)|

<aside class="success">
This operation does not require authentication
</aside>

## Update Allowed Hosts

<a id="opIdupdate_allowed_hosts_api_v1_egress_hosts_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/egress/hosts', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "hosts": [
    "string"
  ]
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/egress/hosts',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/egress/hosts`

> Body parameter

```json
{
  "hosts": [
    "string"
  ]
}
```

<h3 id="update-allowed-hosts-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[AllowedHosts](#schemaallowedhosts)|true|none|

> Example responses

> 200 Response

```json
{
  "hosts": [
    "string"
  ]
}
```

<h3 id="update-allowed-hosts-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[AllowedHosts](#schemaallowedhosts)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<aside class="success">
This operation does not require authentication
</aside>

## Get Rotation Schedule

<a id="opIdget_rotation_schedule_api_v1_egress_rotation_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/egress/rotation', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/egress/rotation',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/egress/rotation`

> Example responses

> 200 Response

```json
{
  "interval_days": 30,
  "last_rotated": "string"
}
```

<h3 id="get-rotation-schedule-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[RotationSchedule](#schemarotationschedule)|

<aside class="success">
This operation does not require authentication
</aside>

## Update Rotation Schedule

<a id="opIdupdate_rotation_schedule_api_v1_egress_rotation_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/egress/rotation', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "interval_days": 30,
  "last_rotated": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/egress/rotation',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/egress/rotation`

> Body parameter

```json
{
  "interval_days": 30,
  "last_rotated": "string"
}
```

<h3 id="update-rotation-schedule-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[RotationSchedule](#schemarotationschedule)|true|none|

> Example responses

> 200 Response

```json
{
  "interval_days": 30,
  "last_rotated": "string"
}
```

<h3 id="update-rotation-schedule-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[RotationSchedule](#schemarotationschedule)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<aside class="success">
This operation does not require authentication
</aside>

## Trigger Rotation

<a id="opIdtrigger_rotation_api_v1_egress_rotate_post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/egress/rotate', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/egress/rotate',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/egress/rotate`

> Example responses

> 202 Response

```json
null
```

<h3 id="trigger-rotation-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|202|[Accepted](https://tools.ietf.org/html/rfc7231#section-6.3.3)|Successful Response|Inline|

<h3 id="trigger-rotation-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-soul-manifest">Soul Manifest</h1>

## Get Soul Manifest

<a id="opIdget_soul_manifest_api_v1_soul_manifest_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/soul/manifest', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/soul/manifest',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/soul/manifest`

Retrieves the current Soul Manifest from VDXF or Vault.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-soul-manifest-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-soul-manifest-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Update Soul Manifest

<a id="opIdupdate_soul_manifest_api_v1_soul_manifest_put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/soul/manifest', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "manifest": {},
  "preferences": {
    "preferences": {}
  }
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/soul/manifest',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/soul/manifest`

> Body parameter

```json
{
  "manifest": {},
  "preferences": {
    "preferences": {}
  }
}
```

<h3 id="update-soul-manifest-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[SoulManifest](#schemasoulmanifest)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="update-soul-manifest-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="update-soul-manifest-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Preview Soul Response

<a id="opIdpreview_soul_response_api_v1_soul_preview_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/soul/preview', headers = headers)

print(r.json())

```

```javascript
const inputBody = 'string';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/soul/preview',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/soul/preview`

> Body parameter

```json
"string"
```

<h3 id="preview-soul-response-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="preview-soul-response-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="preview-soul-response-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Get Soul Preferences

<a id="opIdget_soul_preferences_api_v1_soul_preferences_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/soul/preferences', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/soul/preferences',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/soul/preferences`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-soul-preferences-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-soul-preferences-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-execution-approval">Execution Approval</h1>

## Get Pending Approvals

<a id="opIdget_pending_approvals_api_v1_exec_pending_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/exec/pending', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/exec/pending',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/exec/pending`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-pending-approvals-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-pending-approvals-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Approve Request

<a id="opIdapprove_request_api_v1_exec_approve__request_id__post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/exec/approve/{request_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/exec/approve/{request_id}',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/exec/approve/{request_id}`

<h3 id="approve-request-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|request_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="approve-request-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="approve-request-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Deny Request

<a id="opIddeny_request_api_v1_exec_deny__request_id__post"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.post('/api/v1/exec/deny/{request_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/exec/deny/{request_id}',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/exec/deny/{request_id}`

<h3 id="deny-request-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|request_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="deny-request-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="deny-request-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## List Policies

<a id="opIdlist_policies_api_v1_exec_policies_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/exec/policies', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/exec/policies',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/exec/policies`

> Example responses

> 200 Response

```json
null
```

<h3 id="list-policies-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="list-policies-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Add Policy

<a id="opIdadd_policy_api_v1_exec_policies_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/exec/policies', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/exec/policies',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/exec/policies`

> Body parameter

```json
{}
```

<h3 id="add-policy-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="add-policy-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="add-policy-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Policy

<a id="opIddelete_policy_api_v1_exec_policies__policy_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/exec/policies/{policy_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/exec/policies/{policy_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/exec/policies/{policy_id}`

<h3 id="delete-policy-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|policy_id|path|integer|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-policy-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-policy-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-gemini-proxy">Gemini Proxy</h1>

## Gemini Proxy

<a id="opIdgemini_proxy_api_v1_gemini_proxy_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/gemini/proxy', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "prompt": "string",
  "complexity": "LOW",
  "privacy_level": "PUBLIC",
  "inference_mode": "LOCAL",
  "session_id": "string"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/gemini/proxy',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/gemini/proxy`

Proxies requests to the local Gemma 4 model or fallback providers.
Bypasses the need for a client-side Google API key by using the Sovereign LCE.

> Body parameter

```json
{
  "prompt": "string",
  "complexity": "LOW",
  "privacy_level": "PUBLIC",
  "inference_mode": "LOCAL",
  "session_id": "string"
}
```

<h3 id="gemini-proxy-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[Body_gemini_proxy_api_v1_gemini_proxy_post](#schemabody_gemini_proxy_api_v1_gemini_proxy_post)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="gemini-proxy-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="gemini-proxy-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-security-resolution">Security Resolution</h1>

## Resolve Security Block

<a id="opIdresolve_security_block_api_v1_security_resolve_post"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.post('/api/v1/security/resolve', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{
  "task_id": "string",
  "resolution_type": "string",
  "metadata": {}
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/security/resolve',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/v1/security/resolve`

Called by the frontend Interactive Security Modal to resolve a blocked task.

> Body parameter

```json
{
  "task_id": "string",
  "resolution_type": "string",
  "metadata": {}
}
```

<h3 id="resolve-security-block-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|[SecurityResolutionRequest](#schemasecurityresolutionrequest)|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="resolve-security-block-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="resolve-security-block-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="alluci-sovereign-agent-skills-vault">Skills Vault</h1>

## Get All Skills

<a id="opIdget_all_skills_api_v1_skills_get"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.get('/api/v1/skills', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/skills',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /api/v1/skills`

Retrieve all dynamically loaded skills from the vault.

> Example responses

> 200 Response

```json
null
```

<h3 id="get-all-skills-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-all-skills-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Save Skill

<a id="opIdsave_skill_api_v1_skills__skill_id__put"></a>

> Code samples

```python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

r = requests.put('/api/v1/skills/{skill_id}', headers = headers)

print(r.json())

```

```javascript
const inputBody = '{}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json'
};

fetch('/api/v1/skills/{skill_id}',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /api/v1/skills/{skill_id}`

Creates or Updates a skill in the local vault.

> Body parameter

```json
{}
```

<h3 id="save-skill-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|skill_id|path|string|true|none|
|body|body|object|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="save-skill-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="save-skill-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

## Delete Skill

<a id="opIddelete_skill_api_v1_skills__skill_id__delete"></a>

> Code samples

```python
import requests
headers = {
  'Accept': 'application/json'
}

r = requests.delete('/api/v1/skills/{skill_id}', headers = headers)

print(r.json())

```

```javascript

const headers = {
  'Accept':'application/json'
};

fetch('/api/v1/skills/{skill_id}',
{
  method: 'DELETE',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`DELETE /api/v1/skills/{skill_id}`

Deletes a skill from the local vault.

<h3 id="delete-skill-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|skill_id|path|string|true|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-skill-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="delete-skill-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

# Schemas

<h2 id="tocS_AllowedHosts">AllowedHosts</h2>
<!-- backwards compatibility -->
<a id="schemaallowedhosts"></a>
<a id="schema_AllowedHosts"></a>
<a id="tocSallowedhosts"></a>
<a id="tocsallowedhosts"></a>

```json
{
  "hosts": [
    "string"
  ]
}

```

AllowedHosts

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|hosts|[string]|true|none|List of allowed LLM hostnames|

<h2 id="tocS_AuditEntry">AuditEntry</h2>
<!-- backwards compatibility -->
<a id="schemaauditentry"></a>
<a id="schema_AuditEntry"></a>
<a id="tocSauditentry"></a>
<a id="tocsauditentry"></a>

```json
{
  "id": "string",
  "event": "string",
  "details": "",
  "status": "INFO",
  "timestamp": "string"
}

```

AuditEntry

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|id|string|false|none|none|
|event|string|true|none|none|
|details|string|false|none|none|
|status|string|false|none|none|
|timestamp|string|false|none|none|

<h2 id="tocS_Body_create_goal_api_v1_goals__post">Body_create_goal_api_v1_goals__post</h2>
<!-- backwards compatibility -->
<a id="schemabody_create_goal_api_v1_goals__post"></a>
<a id="schema_Body_create_goal_api_v1_goals__post"></a>
<a id="tocSbody_create_goal_api_v1_goals__post"></a>
<a id="tocsbody_create_goal_api_v1_goals__post"></a>

```json
{
  "title": "string",
  "description": "string",
  "priority": "MEDIUM"
}

```

Body_create_goal_api_v1_goals__post

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|title|string|true|none|none|
|description|string|true|none|none|
|priority|string|false|none|none|

<h2 id="tocS_Body_delegate_to_agent_api_v1_agents_delegate_post">Body_delegate_to_agent_api_v1_agents_delegate_post</h2>
<!-- backwards compatibility -->
<a id="schemabody_delegate_to_agent_api_v1_agents_delegate_post"></a>
<a id="schema_Body_delegate_to_agent_api_v1_agents_delegate_post"></a>
<a id="tocSbody_delegate_to_agent_api_v1_agents_delegate_post"></a>
<a id="tocsbody_delegate_to_agent_api_v1_agents_delegate_post"></a>

```json
{
  "agent_id": "string",
  "task": "string"
}

```

Body_delegate_to_agent_api_v1_agents_delegate_post

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|agent_id|string|true|none|none|
|task|string|true|none|none|

<h2 id="tocS_Body_gemini_proxy_api_v1_gemini_proxy_post">Body_gemini_proxy_api_v1_gemini_proxy_post</h2>
<!-- backwards compatibility -->
<a id="schemabody_gemini_proxy_api_v1_gemini_proxy_post"></a>
<a id="schema_Body_gemini_proxy_api_v1_gemini_proxy_post"></a>
<a id="tocSbody_gemini_proxy_api_v1_gemini_proxy_post"></a>
<a id="tocsbody_gemini_proxy_api_v1_gemini_proxy_post"></a>

```json
{
  "prompt": "string",
  "complexity": "LOW",
  "privacy_level": "PUBLIC",
  "inference_mode": "LOCAL",
  "session_id": "string"
}

```

Body_gemini_proxy_api_v1_gemini_proxy_post

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|prompt|string|true|none|none|
|complexity|string|false|none|none|
|privacy_level|string|false|none|none|
|inference_mode|string|false|none|none|
|session_id|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

#### Enumerated Values

|Property|Value|
|---|---|
|complexity|LOW|
|complexity|MEDIUM|
|complexity|HIGH|
|privacy_level|PUBLIC|
|privacy_level|SENSITIVE|
|privacy_level|AIRGAPPED|
|inference_mode|LOCAL|
|inference_mode|CLOUD|
|inference_mode|TACTICAL|
|inference_mode|HYBRID|

<h2 id="tocS_Body_register_sop_api_v1_sops__post">Body_register_sop_api_v1_sops__post</h2>
<!-- backwards compatibility -->
<a id="schemabody_register_sop_api_v1_sops__post"></a>
<a id="schema_Body_register_sop_api_v1_sops__post"></a>
<a id="tocSbody_register_sop_api_v1_sops__post"></a>
<a id="tocsbody_register_sop_api_v1_sops__post"></a>

```json
{
  "name": "string",
  "description": "string",
  "steps": [
    {}
  ]
}

```

Body_register_sop_api_v1_sops__post

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|name|string|true|none|none|
|description|string|true|none|none|
|steps|[object]|true|none|none|

<h2 id="tocS_Body_transcribe_voice_api_v1_voice_transcribe_post">Body_transcribe_voice_api_v1_voice_transcribe_post</h2>
<!-- backwards compatibility -->
<a id="schemabody_transcribe_voice_api_v1_voice_transcribe_post"></a>
<a id="schema_Body_transcribe_voice_api_v1_voice_transcribe_post"></a>
<a id="tocSbody_transcribe_voice_api_v1_voice_transcribe_post"></a>
<a id="tocsbody_transcribe_voice_api_v1_voice_transcribe_post"></a>

```json
{
  "file": "string"
}

```

Body_transcribe_voice_api_v1_voice_transcribe_post

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|file|string(binary)|true|none|none|

<h2 id="tocS_Body_update_goal_api_v1_goals__goal_id__patch">Body_update_goal_api_v1_goals__goal_id__patch</h2>
<!-- backwards compatibility -->
<a id="schemabody_update_goal_api_v1_goals__goal_id__patch"></a>
<a id="schema_Body_update_goal_api_v1_goals__goal_id__patch"></a>
<a id="tocSbody_update_goal_api_v1_goals__goal_id__patch"></a>
<a id="tocsbody_update_goal_api_v1_goals__goal_id__patch"></a>

```json
{
  "status": "string",
  "progress": 0
}

```

Body_update_goal_api_v1_goals__goal_id__patch

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|status|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

continued

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|progress|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|number|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

<h2 id="tocS_ExportPemRequest">ExportPemRequest</h2>
<!-- backwards compatibility -->
<a id="schemaexportpemrequest"></a>
<a id="schema_ExportPemRequest"></a>
<a id="tocSexportpemrequest"></a>
<a id="tocsexportpemrequest"></a>

```json
{
  "export_passphrase": "stringstringstri"
}

```

ExportPemRequest

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|export_passphrase|string|true|none|A unique passphrase to encrypt the exported key. Must not be your master key.|

<h2 id="tocS_GoalRecord">GoalRecord</h2>
<!-- backwards compatibility -->
<a id="schemagoalrecord"></a>
<a id="schema_GoalRecord"></a>
<a id="tocSgoalrecord"></a>
<a id="tocsgoalrecord"></a>

```json
{
  "id": 0,
  "title": "string",
  "description": "string",
  "status": "string",
  "created_at": "2019-08-24T14:15:22Z"
}

```

GoalRecord

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|id|integer|false|none|none|
|title|string|true|none|none|
|description|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

continued

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|status|string|true|none|none|
|created_at|string(date-time)|false|none|none|

<h2 id="tocS_HTTPValidationError">HTTPValidationError</h2>
<!-- backwards compatibility -->
<a id="schemahttpvalidationerror"></a>
<a id="schema_HTTPValidationError"></a>
<a id="tocShttpvalidationerror"></a>
<a id="tocshttpvalidationerror"></a>

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string",
      "input": null,
      "ctx": {}
    }
  ]
}

```

HTTPValidationError

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|detail|[[ValidationError](#schemavalidationerror)]|false|none|none|

<h2 id="tocS_LoginRequest">LoginRequest</h2>
<!-- backwards compatibility -->
<a id="schemaloginrequest"></a>
<a id="schema_LoginRequest"></a>
<a id="tocSloginrequest"></a>
<a id="tocsloginrequest"></a>

```json
{
  "key": "string"
}

```

LoginRequest

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|key|string|true|none|none|

<h2 id="tocS_ObjectiveRequest">ObjectiveRequest</h2>
<!-- backwards compatibility -->
<a id="schemaobjectiverequest"></a>
<a id="schema_ObjectiveRequest"></a>
<a id="tocSobjectiverequest"></a>
<a id="tocsobjectiverequest"></a>

```json
{
  "objective": "string",
  "autonomy_level": "SEMI_AUTONOMOUS"
}

```

ObjectiveRequest

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|objective|string|true|none|none|
|autonomy_level|string|false|none|none|

<h2 id="tocS_RotationSchedule">RotationSchedule</h2>
<!-- backwards compatibility -->
<a id="schemarotationschedule"></a>
<a id="schema_RotationSchedule"></a>
<a id="tocSrotationschedule"></a>
<a id="tocsrotationschedule"></a>

```json
{
  "interval_days": 30,
  "last_rotated": "string"
}

```

RotationSchedule

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|interval_days|integer|false|none|Rotation interval in days|
|last_rotated|any|false|none|ISO timestamp of last rotation|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

<h2 id="tocS_SOPRecord">SOPRecord</h2>
<!-- backwards compatibility -->
<a id="schemasoprecord"></a>
<a id="schema_SOPRecord"></a>
<a id="tocSsoprecord"></a>
<a id="tocssoprecord"></a>

```json
{
  "id": 0,
  "name": "string",
  "description": "string",
  "steps": {},
  "is_active": true,
  "created_at": "2019-08-24T14:15:22Z"
}

```

SOPRecord

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|id|integer|false|none|none|
|name|string|true|none|none|
|description|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

continued

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|steps|object|false|none|none|
|is_active|boolean|false|none|none|
|created_at|string(date-time)|false|none|none|

<h2 id="tocS_SecurityResolutionRequest">SecurityResolutionRequest</h2>
<!-- backwards compatibility -->
<a id="schemasecurityresolutionrequest"></a>
<a id="schema_SecurityResolutionRequest"></a>
<a id="tocSsecurityresolutionrequest"></a>
<a id="tocssecurityresolutionrequest"></a>

```json
{
  "task_id": "string",
  "resolution_type": "string",
  "metadata": {}
}

```

SecurityResolutionRequest

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|task_id|string|true|none|none|
|resolution_type|string|true|none|none|
|metadata|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|object|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

<h2 id="tocS_SoulManifest">SoulManifest</h2>
<!-- backwards compatibility -->
<a id="schemasoulmanifest"></a>
<a id="schema_SoulManifest"></a>
<a id="tocSsoulmanifest"></a>
<a id="tocssoulmanifest"></a>

```json
{
  "manifest": {},
  "preferences": {
    "preferences": {}
  }
}

```

SoulManifest

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|manifest|object|false|none|none|
|preferences|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|[SoulPreferences](#schemasoulpreferences)|false|none|Placeholder for user preferences related to the soul.<br>Extend with actual fields as needed.|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

<h2 id="tocS_SoulPreferences">SoulPreferences</h2>
<!-- backwards compatibility -->
<a id="schemasoulpreferences"></a>
<a id="schema_SoulPreferences"></a>
<a id="tocSsoulpreferences"></a>
<a id="tocssoulpreferences"></a>

```json
{
  "preferences": {}
}

```

SoulPreferences

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|preferences|object|false|none|none|

<h2 id="tocS_TaskPriority">TaskPriority</h2>
<!-- backwards compatibility -->
<a id="schemataskpriority"></a>
<a id="schema_TaskPriority"></a>
<a id="tocStaskpriority"></a>
<a id="tocstaskpriority"></a>

```json
"URGENT"

```

TaskPriority

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|TaskPriority|string|false|none|none|

#### Enumerated Values

|Property|Value|
|---|---|
|TaskPriority|URGENT|
|TaskPriority|HIGH|
|TaskPriority|MEDIUM|
|TaskPriority|LOW|

<h2 id="tocS_TaskUpdate">TaskUpdate</h2>
<!-- backwards compatibility -->
<a id="schemataskupdate"></a>
<a id="schema_TaskUpdate"></a>
<a id="tocStaskupdate"></a>
<a id="tocstaskupdate"></a>

```json
{
  "description": "string",
  "completed": false,
  "priority": "URGENT",
  "due_date": "string"
}

```

TaskUpdate

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|description|string|true|none|none|
|completed|boolean|false|none|none|
|priority|[TaskPriority](#schemataskpriority)|false|none|none|
|due_date|any|false|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|null|false|none|none|

<h2 id="tocS_ValidationError">ValidationError</h2>
<!-- backwards compatibility -->
<a id="schemavalidationerror"></a>
<a id="schema_ValidationError"></a>
<a id="tocSvalidationerror"></a>
<a id="tocsvalidationerror"></a>

```json
{
  "loc": [
    "string"
  ],
  "msg": "string",
  "type": "string",
  "input": null,
  "ctx": {}
}

```

ValidationError

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|loc|[anyOf]|true|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|integer|false|none|none|

continued

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|msg|string|true|none|none|
|type|string|true|none|none|
|input|any|false|none|none|
|ctx|object|false|none|none|

