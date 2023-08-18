/* Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

odoo.define("base_hide_delete_view.form_controller", function (require) {
    "use strict";

    const FormController = require("web.FormController");
    const Core = require("web.core");
    const _t = Core._t;

    FormController.include({
        /**
         * The active model
         * @private
         * @returns {Promise}
         */
        _getActionMenuItems: function () {
            const props = this._super(...arguments);
            console.log(props);
            console.log("=====test======");
            if (props && props.items && props.items.other) {
                const other_list = props.items.other;
                const duplicate_index = other_list.findIndex(
                    (item) => item.description === _t("Delete")
                );
                if (other_list[duplicate_index]) {
                    other_list[duplicate_index] = false;
                }
            }
            return props;
        },
    });
});
