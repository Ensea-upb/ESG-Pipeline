# Output Contract Notes v1.5

`contracts/output_contract_v1.json` remains unchanged in v1.5.

## Evidence Types Currently Emitted

Observed in current v1 outputs:

- `section_heading`
- `paragraph`
- `table`
- `figure`

## Contract-Allowed Values Not Currently Emitted

The contract also allows:

- `list_item`
- `footnote`
- `caption`
- `unknown`

These values are `contract_allowed_not_currently_emitted` and reserved for future compatibility. Downstream modules must accept the full enum but must not assume that every allowed value appears in every run.

Keeping these values avoids a breaking contract change.
