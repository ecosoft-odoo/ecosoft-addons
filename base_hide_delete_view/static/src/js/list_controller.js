/* Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

odoo.define("base_hide_delete_view.list_controller", function (require) {
    "use strict";

    const ListController = require("web.ListController");

    ListController.include({
        /**
         * The active model
         * @private
         * @returns {Promise}
         */
        _getActionMenuItems: function () {
            this.activeActions.delete = false;
            return this._super(...arguments);
        },
    });
});
