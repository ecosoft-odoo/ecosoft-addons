## Pattern 1 - Use wizard directly (no Python subclass)

Best for: multiple reports on one model, wizard just picks which to print.

**Step 1:** Mark reports with `show_in_wizard = True` _(Technical menu → Reporting →
Reports, or via XML data)_

```xml
<record id="action_report_my_document" model="ir.actions.report">
    <field name="show_in_wizard" eval="True" />
    <!-- optional: only show when every selected record matches this domain -->
    <field name="domain_form">[('state', '=', 'confirm')]</field>
</record>
```

**Step 2:** Bind a window action to the source model

```xml
<record id="action_open_my_print_wizard" model="ir.actions.act_window">
    <field name="name">Print Report</field>
    <field name="res_model">base.print.wizard</field>
    <field name="view_mode">form</field>
    <field name="view_id" ref="base_print_wizard.view_print_wizard_base" />
    <field name="binding_model_id" ref="my_module.model_my_document" />
    <field name="binding_view_types">list,form</field>
    <field name="binding_type">report</field>
    <field name="target">new</field>
</record>
```

The wizard lists all reports flagged `show_in_wizard = True` for that model. If
`domain_form` is set, the report only appears when every active record matches the
domain. Reports restricted to groups are only shown to users in one of those groups.
When only one report qualifies, it is auto-selected and the user can click Print
immediately.

---

## Pattern 2 - Subclass for extra wizard fields

Best for: single fixed report with extra options (e.g. print mode, date range).

The fixed report must still have `show_in_wizard = True`, use the same model as the
active records, and satisfy its `domain_form` when one is configured.

**Step 1:** Create a child TransientModel

```python
from odoo import api, fields, models

class MyDocumentPrintWizard(models.TransientModel):
    _name = "my.document.print.wizard"
    _inherit = "base.print.wizard"
    _description = "My Document Print Wizard"

    print_mode = fields.Selection(
        selection=[("summary", "Summary"), ("detail", "Detail")],
        default="summary",
        required=True,
    )

    @api.model
    def _get_doctype_default(self):
        # Pin the default selection. The report must still be available for the records.
        return self.env.ref("my_module.action_report_my_document")

    def _get_report_context(self):
        res = super()._get_report_context()
        res["print_mode"] = self.print_mode
        return res
```

**Step 2:** Extend the base view to show the extra field

```xml
<record id="view_my_document_print_wizard_form" model="ir.ui.view">
    <field name="name">my.document.print.wizard.form</field>
    <field name="model">my.document.print.wizard</field>
    <field name="inherit_id" ref="base_print_wizard.view_print_wizard_base" />
    <field name="mode">primary</field>
    <field name="arch" type="xml">
        <!-- Replace doctype field with your custom field -->
        <field name="doctype" position="replace">
            <field name="doctype" invisible="1" />
            <field name="print_mode" widget="radio" />
        </field>
    </field>
</record>
```

**Step 3:** Bind the window action to the child wizard

```xml
<record id="action_my_document_print_wizard" model="ir.actions.act_window">
    <field name="name">Print Report</field>
    <field name="res_model">my.document.print.wizard</field>
    <field name="view_mode">form</field>
    <field name="view_id" ref="view_my_document_print_wizard_form" />
    <field name="binding_model_id" ref="my_module.model_my_document" />
    <field name="binding_view_types">list,form</field>
    <field name="binding_type">report</field>
    <field name="target">new</field>
</record>
```

---

## Module dependency

Add `base_print_wizard` to your module's `depends` list:

```python
"depends": ["base_print_wizard"],
```

---

## Optional copy options

Add the copy fields only to wizards that need them by inheriting the optional mixin:

```python
from odoo import models


class MyDocumentPrintWizard(models.TransientModel):
    _name = "my.document.print.wizard"
    _inherit = ["base.print.wizard", "base.print.copy.mixin"]

    def _get_report_context(self):
        res = super()._get_report_context()
        res.update(self._get_copy_report_context())
        return res
```

Add `copy_qty` and `copy_type` to the specialized wizard view. The mixin validates that
the copy quantity is greater than zero, but does not add fields to the base wizard view.

```xml
<record id="view_my_document_print_wizard_form" model="ir.ui.view">
    <field name="name">my.document.print.wizard.form</field>
    <field name="model">my.document.print.wizard</field>
    <field name="inherit_id" ref="base_print_wizard.view_print_wizard_base" />
    <field name="mode">primary</field>
    <field name="arch" type="xml">
        <xpath expr="//group[@name='criteria']/group[last()]" position="inside">
            <field name="copy_qty" />
            <field name="copy_type" />
        </xpath>
    </field>
</record>
```

## Validation behavior

- A report must have `show_in_wizard = True` and its `model` must match the active model.
- Every selected record must match `domain_form`; mixed selections do not expose a
  partially applicable report.
- Reports restricted with `groups_id` are only available to members of those groups.
- `domain_form` syntax is validated when the report action is saved.
- The selected report is validated again by `action_print()` to prevent bypassing the
  form-view domain through RPC or custom code.

---

## Override reference

| Method                        | When to override                                   |
| ----------------------------- | -------------------------------------------------- |
| `_get_doctype_default()`      | Fix a single default report instead of auto-select |
| `_get_available_report_ids()` | Custom report filtering logic                      |
| `_get_action_report()`        | Change which records are passed to the report      |
| `_get_report_context()`       | Pass extra context to `report_action()`            |
| `_validate_report()`          | Add server-side report validation rules            |
