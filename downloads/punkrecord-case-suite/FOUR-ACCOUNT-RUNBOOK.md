# Fixed Test Accounts

Target: `http://14.103.229.153:15173/` only. Local PunkRecord is source reference, not the test target.

| Actor | Login | Manager | Level |
|---|---|---|---:|
| manager | test_user1 | none | 0 |
| supervisor | test_user2 | test_user1 | 1 |
| employee | test_user3 | test_user2 | 2 |
| other | test_user4 | test_user2 | 2 |

All four identities already exist. `test-account-pool.json` pins their IDs. Missing users, changed identities or reporting lines stop execution; scripts must never create replacements or reset passwords.

The API Workflow Test job grants todo/project/meeting read/write and iam.read. It does not grant administrator status, salary access or iam.write. L0 Beli authorization is based on `manager_user_id is None`, separately from job permissions.

Credentials are stored in the Windows CurrentUser DPAPI file, which is excluded from Git. On another host provide `PUNKRECORD_TEST_PASSWORD`. Management login uses `AUTOTEST_PASSWORD`; business administrator login uses `PUNKRECORD_PASSWORD`. Never export passwords or JWTs into reports.

## Execution

Run from this folder using a Python environment containing requests and tzdata. The local autotest API must be running on port 8000. Native flow records use the existing shared project 17796 and always target remote port 15173. The deployed remote management version does not support the new native scenario/run routes; headed Web jobs use its supported Agent endpoints.

1. `python -m unittest test_account_pool`
2. `python verify_account_reuse.py`
3. Set `NATIVE82_OUTPUT` to a new run filename, then `python native_replay_82.py`. Use the same filename with `--resume` to retry failed/incomplete scenes without duplicating successful scenes.
4. After the 82-flow run finishes, `python four_account_permissions.py`.
5. After financial mutation tests finish, `python shop_rich_native.py`.
6. `python probe_reward_page_permissions.py` for four read-only headed Web checks via local-win-01.
7. `python publish_four_account_report.py` to save the reconciled report and publish it to project knowledge.

The 2026-10-19 report expects the 82-flow result filename `native-82-four-accounts-results.json`. Permission and shop scripts refuse to overwrite existing result files; preserve completed results before explicitly preparing another run. Do not run separate financial suites concurrently on the same account.

Fixtures are new test tasks/projects/products, not new users. Reward/ledger/order history is retained for inspection. Products are unpublished at cleanup; the four fixed accounts remain active. Native templates are disabled after execution because rerunning stateful tests requires fresh fixtures.

## Retired Users

Only the three CASE_20261019_144610 users and their explicitly authorized historical test dependencies were deleted. Backup: `/home/xiaox/data/punkrecord-test-cleanup/20261019T085835Z-7b189e548213.json`. Autotest execution history was retained. The old cleanup manifest is historical; do not rerun it to select current users.

`initialize_account_pool.py` is intentionally blocked for version-2 user-provided accounts. Do not use it to replace their credentials.
