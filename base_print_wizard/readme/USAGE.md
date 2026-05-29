# Usage

## Pattern 1 - Use wizard directly (no Python subclass)

Best for: multiple reports on one model, wizard just picks which to print.

**Step 1:** Mark reports with `show_in_wizard = True` _(Technical menu → Reporting →
Reports, or via XML data)_

```xml
<record id="action_report_my_document" model="ir.actions.report">
    <field name="show_in_wizard" eval="True" />
    <!-- optional: only show when record matches this domain -->
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
`domain_form` is set, the report only appears when active records match the domain. When
only one report qualifies, it is auto-selected and the user can click Print immediately.

---

## Pattern 2 - Subclass for extra wizard fields

Best for: single fixed report with extra options (e.g. print mode, date range).

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
        # Pin to a specific report - skip the dynamic selection logic
        return self.env.ref("my_module.action_report_my_document")

    def action_print(self):
        self.ensure_one()
        objs = self._get_action_report()
        return self.doctype.with_context(print_mode=self.print_mode).report_action(objs)
```

**Step 2:** Extend the base view to show the extra field

```xml
<record id="view_my_document_print_wizard_form" model="ir.ui.view">
    <field name="name">my.document.print.wizard.form</field>
    <field name="model">my.document.print.wizard</field>
    <field name="inherit_id" ref="base_print_wizard.view_print_wizard_base" />
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

## Override reference

| Method                        | When to override                                   |
| ----------------------------- | -------------------------------------------------- |
| `_get_doctype_default()`      | Fix a single default report instead of auto-select |
| `_get_available_report_ids()` | Custom report filtering logic                      |
| `_get_action_report()`        | Change which records are passed to the report      |
| `action_print()`              | Pass extra context to `report_action()`            |
