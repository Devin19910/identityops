# Architecture

## Layering

```
connectors/   -> the only layer that talks to real APIs (Graph, EXO, or the demo fake)
lifecycle/    -> joiner-mover-leaver workflows, built on an explicit state machine
governance/   -> the oversight layer: orphaned access scanning, consent risk review
safety/       -> confirmation gate + audit log, shared by every mutating call above
```

The dependency direction only ever points downward: `governance` and `lifecycle`
depend on `connectors.base.TenantConnector`, never on a concrete implementation.
Swapping `DemoConnector` for `GraphConnector` + `ExoConnector` requires no changes
to any governance or lifecycle code — that's the actual point of the abstraction,
not just tidiness.

## Why mailbox permissions need a separate connector from Graph

Microsoft Graph has no endpoint for FullAccess/Send-As mailbox delegation —
that data lives entirely in Exchange Online, reachable only via the EXO REST
`InvokeCommand` endpoint (which wraps the same PowerShell cmdlets an admin
would run by hand: `Get-MailboxPermission`, `Get-RecipientPermission`, etc.).

Any tool built only against Graph will structurally miss this class of leftover
access after an offboarding — which is exactly why `OrphanedAccessScanner` takes
a connector that implements both surfaces.

## Wiring `GraphConnector`/`ExoConnector` into the CLI

1. Register an Azure AD app with `User.Read.All` and `Directory.ReadWrite.All`
   (Graph, application permissions, admin-consented) and `Exchange.ManageAsApp`
   (Exchange Online, application permission, also admin-consented + role-assigned
   via Exchange Online RBAC to the app's service principal).
2. Set `IDENTITYOPS_TENANT_ID`, `IDENTITYOPS_CLIENT_ID`, `IDENTITYOPS_CLIENT_SECRET`.
3. In `cli/main.py`, swap `_get_connector()`'s body to return
   `GraphConnector()` for user/consent operations and `ExoConnector()` for
   mailbox operations (or a small composite connector that dispatches to both —
   left as an exercise, since the two-connector split is the actual design lesson
   this repo tries to demonstrate).

## Granting tenant-wide admin consent (the two-call flow)

`GraphConnector.grant_tenant_consent` is intentionally left unimplemented in this
repo because it involves a real, easy-to-get-wrong two-step flow:

1. `POST /servicePrincipals` with just `{"appId": "<app-id>"}` — if the app has
   never been consented to before, no service principal exists yet, and you
   can't grant consent to something that doesn't have one.
2. `POST /oauth2PermissionGrants` with `clientId` (the service principal's own
   `id`, not its `appId`), `consentType: "AllPrincipals"`, `resourceId` (Microsoft
   Graph's service principal id), and `scope` as a single space-separated string.

Skipping step 1 when the SP doesn't exist yet is the most common way this
silently fails.
