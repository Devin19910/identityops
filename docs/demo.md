# Running the demo

## Option A — Docker (no Python setup needed)

```bash
docker-compose up
curl http://localhost:8000/audit/orphaned-access
curl http://localhost:8000/consent/pending
```

## Option B — CLI, locally

```bash
pip install -e .
identityops audit orphaned-access
```

Expect output like:

```
             Orphaned Mailbox Access
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Mailbox            ┃ Trustee                    ┃ Rights           ┃ Reason                      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ support@demo.local │ sam.okafor@demo.local      │ SendAs           │ trustee account is disabled │
│ billing@demo.local │ sam.okafor@demo.local      │ FullAccess       │ trustee account is disabled │
└────────────────────┴────────────────────────────┴──────────────────┴─────────────────────────────┘
```

Then remediate it — first as a dry run, then for real:

```bash
identityops audit orphaned-access --remediate            # dry run, logs intent only
identityops audit orphaned-access --remediate --confirm  # actually removes the access
```

Check the audit trail:

```bash
cat identityops_audit.jsonl
```

Every line is a JSON record of exactly what was (or would have been) changed,
by whom, and whether it was a dry run.
