Provides a reusable base wizard for printing reports from any Odoo model.

Key features:

- **Dynamic report list** - wizard auto-discovers all `ir.actions.report` records
  flagged `show_in_wizard = True` for the active model.
- **Domain filtering** - each report can define a `domain_form` so it only appears when
  the selected records match the domain (e.g. only confirmed orders).
- **Auto-select** - when exactly one report qualifies, it is pre-selected and the user
  can print immediately without choosing.
- **Extensible** - subclass `base.print.wizard` to add extra fields (print mode, date
  range, etc.) and override `action_print()` to pass context to the report.

Use Pattern 1 (direct binding) when you only need to choose among multiple reports. Use
Pattern 2 (subclass) when the wizard itself needs extra options that influence how the
report renders. See `USAGE.md` for step-by-step instructions.
