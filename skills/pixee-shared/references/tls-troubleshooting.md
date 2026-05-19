# TLS trust failures

Read this when the user reports that `pixee` cannot reach an internal or
enterprise Pixee server and the failure looks like a certificate problem (the
generic "Connection to ... failed" message is the symptom — confirm with
`curl` before applying anything below).

`pixee` verifies the server's TLS certificate against its bundled Mozilla CA
list, not the operating system's trust store. Installing a private CA in the
OS keychain alone does not change what `pixee` trusts. This bites when the
user is connecting to a self-hosted Pixee Enterprise Server whose certificate
is signed by an internal CA: the request fails before any HTTP traffic.

## Confirm it's a trust issue

The CLI's "Connection to ... failed" line covers DNS failures, connection
refused, and TLS failures alike, so the first job is to confirm what's
actually broken. Don't guess — run a one-shot probe with `curl` from the
same shell and read its error verbatim:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://pixee.<internal-domain>/
```

If `curl` reports `SSL certificate problem: self-signed certificate`,
`unable to get local issuer certificate`, or similar, it's a CA-chain problem
and the steps below apply. If `curl` says `Could not resolve host`,
`Connection refused`, or times out, this guide isn't the fix — that's DNS,
firewall, or a wrong `--server` URL.

## Preferred fix — add the internal CA to `pixee`'s trust set

`pixee` honors `NODE_EXTRA_CA_CERTS`. Point it at a PEM file containing the
internal CA chain and verification still happens — only that specific CA is
added. The user's bearer token stays protected from passive eavesdroppers
and active on-path attackers, which is exactly what you want.

Walk the user through this:

1. **Locate the internal CA PEM.** Ask the user — they usually have it from
   their IT team, an internal docs page, or by running
   `openssl s_client -connect pixee.<internal-domain>:443 -showcerts </dev/null`
   and copying the chain. If they don't have it and can't get it quickly,
   drop to the last-resort fix.
2. **Verify it covers the server.** With the PEM on disk, confirm `curl`
   itself trusts it before touching `pixee`:
   ```bash
   curl --cacert /path/to/internal-ca.pem https://pixee.<internal-domain>/
   ```
   A successful response means the chain is right. A continued
   `unable to get local issuer certificate` means the file is missing
   intermediates — ask for the full chain.
3. **Run `pixee` against it.** Set the env var in the same shell:
   ```bash
   export NODE_EXTRA_CA_CERTS=/path/to/internal-ca.pem
   pixee --server https://pixee.<internal-domain> auth status
   ```
   For a persistent setup, export it from the user's shell profile or set it
   in the deployment's environment (CI variable, Kubernetes secret, etc.).
   Per-invocation works too:
   ```bash
   NODE_EXTRA_CA_CERTS=/path/to/internal-ca.pem pixee --server https://... scan list
   ```

## Last resort — `--insecure`

If the user genuinely cannot obtain the CA chain (short-lived sandbox,
one-off connectivity check, ephemeral CI container with no way to mount a
PEM), `--insecure` / `PIXEE_INSECURE_TLS=true` disables verification entirely:

```bash
pixee --insecure --server https://pixee.<internal-domain> scan list
PIXEE_INSECURE_TLS=true pixee --server https://pixee.<internal-domain> scan list
```

Be explicit with the user about the tradeoff before suggesting it: with
verification off, anyone who can intercept the connection — including any
host between them and the server — can read their bearer token and act as
them against the API. Recommend it only when the cost of waiting for the
proper CA is genuinely higher than that risk, and treat any persistent CI
usage of `--insecure` as a bug to come back and fix once the CA is available.
