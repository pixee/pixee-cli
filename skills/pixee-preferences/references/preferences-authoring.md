# Authoring Pixee organization preferences

Reference examples for the three flavors of preference: remediation guidance, triage
context, and rule enable/disable. Lift these directly when composing a preferences
document, then adapt them to the org's stack, libraries, and tone.

## Remediation guidance

Tell Pixee how the team prefers to fix specific vulnerability classes. Code examples are
the clearest signal: a "Preferred" block and a "Not preferred" block leave no ambiguity.

### SQL injection in Java

```markdown
## SQL Injection

When fixing SQL injection vulnerabilities, always use Spring's `NamedParameterJdbcTemplate`
with named parameters (`:paramName` syntax) rather than positional placeholders (`?`).
Named parameters improve code readability and make it easier to maintain queries with
multiple parameters. This project includes `spring-jdbc` as a dependency.

**Preferred approach:**
```java
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;

NamedParameterJdbcTemplate namedJdbc = new NamedParameterJdbcTemplate(dataSource);
String query = "SELECT * FROM users WHERE email = :email";
MapSqlParameterSource params = new MapSqlParameterSource("email", email);
List<User> users = namedJdbc.query(query, params, rowMapper);
```

**Not preferred:**
```java
String query = "SELECT * FROM users WHERE email = ?";
PreparedStatement stmt = conn.prepareStatement(query);
stmt.setString(1, email);
```
```

### Cross-site scripting in JavaScript

```markdown
## Cross-Site Scripting (XSS)

For XSS vulnerabilities in user-generated content, always use the `DOMPurify` library for
HTML sanitization. DOMPurify provides robust, battle-tested sanitization that prevents
XSS while preserving the safe HTML formatting our content editors require.

**Preferred approach:**
```javascript
const DOMPurify = require('dompurify');
const { JSDOM } = require('jsdom');

const window = new JSDOM('').window;
const purify = DOMPurify(window);

function renderUserContent(htmlContent) {
    return purify.sanitize(htmlContent, {
        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a'],
        ALLOWED_ATTR: ['href', 'class']
    });
}
```

**Not preferred:**
```javascript
function renderUserContent(htmlContent) {
    return htmlContent
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
```
```

### Path traversal in C#

```markdown
## Path Traversal

For path traversal vulnerabilities, always use our internal `PathValidatorUtility` class
from the `DocumentManagement.Security` namespace rather than manual path validation or
basic `Path.Combine` checks. `PathValidatorUtility` has been audited by our security team
and enforces consistent path security policies across all file operations.

**Preferred approach:**
```csharp
using DocumentManagement.Security;

[HttpGet("download")]
public IActionResult DownloadDocument([FromQuery] string filename)
{
    string safePath = PathValidatorUtility.ValidatePathForRead(filename);
    byte[] fileBytes = System.IO.File.ReadAllBytes(safePath);
    return File(fileBytes, "application/octet-stream", Path.GetFileName(safePath));
}
```

**Not preferred:**
```csharp
using System.IO;

[HttpGet("download")]
public IActionResult DownloadDocument([FromQuery] string filename)
{
    string basePath = @"C:\Documents";
    string fullPath = Path.Combine(basePath, filename);

    if (!fullPath.StartsWith(basePath))
    {
        return BadRequest("Invalid path");
    }

    byte[] fileBytes = System.IO.File.ReadAllBytes(fullPath);
    return File(fileBytes, "application/octet-stream", filename);
}
```
```

## Triage context

Give Pixee context about the deployment environment, compensating controls, or
intentional patterns so it can decide whether a finding is a real risk in this codebase.

### Service architecture

```markdown
## Service Architecture and Trust Boundaries

This service is a multi-tenant SaaS deployed behind AWS ALB with WAF enabled (XSS and
SQL-injection rulesets active). Credentials are managed in AWS Secrets Manager; the
application reads them from environment variables on startup. Rate limiting is enforced at
both the ALB and application layers.

Reduce severity by 1 level for findings on endpoints under `/api/internal/*` (IP-restricted
to office and VPN ranges) and for methods annotated `@PreAuthorize("hasRole('ADMIN')")`.
Findings in `@RestController` methods exposed at `/api/public/*` are higher priority than
internal services: assume internet-facing attack surface.

Treat data from external EHR systems as untrusted regardless of DTO type. Any class that
extends `EHRMessageDTO` carries data from external integrations and should be treated as a
taint source.
```

### SSRF allowlist

```markdown
## Server-Side Request Forgery (SSRF)

For SSRF vulnerabilities in healthcare data fetching, validate URLs against our approved
endpoint allowlists defined in `app.config`. Our medical data platform only integrates
with pre-approved healthcare data exchange partners.

**Approved Endpoints:**
- Medical APIs: `APPROVED_MEDICAL_APIS` (HL7 FHIR, Healthcare.gov, etc.)
- Internal systems: `INTERNAL_EHR_ENDPOINTS` (internal EHR instances)
- Combined list: `ALL_APPROVED_ENDPOINTS`

**Validation Rule:** URLs must start with one of the approved endpoint prefixes. Any
other URL must be rejected with a clear error message directing users to the platform
administration team.

**Preferred approach:**
```python
from urllib.parse import urlparse
from app.config import ALL_APPROVED_ENDPOINTS

def fetch_patient_data(self, fhir_url: str) -> dict:
    if not any(fhir_url.startswith(endpoint) for endpoint in ALL_APPROVED_ENDPOINTS):
        raise ValueError(
            f"API endpoint not in approved list: {fhir_url}. "
            f"Contact platform admin to add new medical data sources."
        )

    parsed = urlparse(fhir_url)
    if parsed.scheme != 'https':
        raise ValueError("Only HTTPS endpoints allowed for medical data")

    response = requests.get(fhir_url, timeout=30)
    response.raise_for_status()
    return response.json()
```
```

### Intentional cryptographic patterns

```markdown
## Cryptography

Treat any use of MD5 or SHA1 for password hashing or signature verification as
**CRITICAL** (HIPAA requirement). Treat weak random number generation in session ID
creation, token generation, or CSRF token generation as **CRITICAL**.

The following uses of weak primitives are **intentional** and should be marked
**FALSE_POSITIVE**:
- Weak random in our rate-limiting jitter logic in `src/middleware/rate_limit.py`: this
  is not a security context, the jitter only spreads request retries.
- MD5 in `src/cache/keys.py`: used as a fast non-cryptographic content-addressable cache
  key, never to authenticate or sign data.
- SHA1 in `src/legacy/etag.py`: used as an ETag fingerprint for HTTP caching, not for
  authentication.

For password hashing, prefer Argon2id with our standard parameters (memory=64MB,
iterations=3, parallelism=4). For cryptographically secure random, use
`secrets.token_bytes()` in Python and `java.security.SecureRandom` in Java.
```

## Enabling and disabling rules

Reference scanner rules by tool name and rule ID. Supported scanners today: Sonar,
CodeQL, Semgrep, Checkmarx, Snyk, GitLab SAST, Veracode, AppScan, Polaris, Trivy, Datadog
SAST, and Fortify.

```markdown
## Scanner Rule Preferences

### Treat as remediable
The Semgrep rule `python.lang.security.audit.eval-detected.eval-detected` should be
considered **REMEDIABLE**. We have a safe eval wrapper pattern that can be applied
automatically; do not mark findings of this rule as WONT_FIX by default.

### Disable
Ignore findings for these rules across all repos:
- Sonar `javasecurity:S2076` in `src/scripts/admin/`: internal CLI tooling, not exposed.
- CodeQL `js/disabled-certificate-validation` in `test/`: TLS validation is disabled
  against the test fixture server only.
- Snyk `javascript/PrototypePollution` flagged on `devDependencies`: these never ship to
  production bundles.

### Elevate
Promote these rule classes by one severity level when found in `/src/payments/` (PCI-DSS
scope): all CodeQL `cwe-`-prefixed rules and any Sonar rule whose key starts with
`security-hotspot:`.
```

## Composing a document

- Start small. A handful of high-impact rules and one or two triage paragraphs cover most
  real-world cases.
- Explain *why* a preference exists. The "why" lets Pixee apply the rule correctly to new
  findings instead of pattern-matching on the prose.
- Show code where possible. Plain prose works, but a "Preferred" code block paired with a
  "Not preferred" counter-example is unambiguous.
- Keep total length under 10,000 characters. The CLI rejects oversize content client-side
  before the round-trip.
- Treat the document as living. Update it when the stack changes, when a recurring
  false-positive pattern emerges, or when a new internal utility supersedes an old one.
