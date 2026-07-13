Provides a reusable base wizard for printing reports from any Odoo model.

Key features:

- **Dynamic report list** - wizard auto-discovers all `ir.actions.report` records
  flagged `show_in_wizard = True` for the active model.
- **Domain filtering** - each report can define a `domain_form` so it only appears when
  every selected record matches the domain (e.g. only confirmed orders).
- **Access-aware and validated** - reports respect their configured groups, and the
  selected report is validated again on the server before printing.
- **Auto-select** - when exactly one report qualifies, it is pre-selected and the user
  can print immediately without choosing.
- **Extensible** - subclass `base.print.wizard` to add extra fields (print mode, date
  range, etc.) and override `_get_report_context()` to pass context to the report.
- **Optional copy options** - inherit `base.print.copy.mixin` when a specialized wizard
  needs copy quantity and Original/Copy type fields.

Use Pattern 1 (direct binding) when you only need to choose among multiple reports. Use
Pattern 2 (subclass) when the wizard itself needs extra options that influence how the
report renders. The copy mixin is optional and does not add fields to the base wizard.
See `USAGE.md` for step-by-step instructions.
