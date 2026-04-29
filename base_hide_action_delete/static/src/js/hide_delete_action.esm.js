import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {user} from "@web/core/user";

const SHOW_DELETE_GROUP = "base_hide_action_delete.group_show_delete";

// Returns a fresh patch object per call. Sharing one object across two
// patch() calls makes OWL resolve `super` to the last-patched controller.
function makeHideDeletePatch() {
    return {
        setup() {
            super.setup(...arguments);
            // Hidden by default; only "Show Delete Action" members keep it.
            this.showDeleteAction = false;
            onWillStart(async () => {
                this.showDeleteAction = await user.hasGroup(SHOW_DELETE_GROUP);
            });
        },
        getStaticActionMenuItems() {
            const items = super.getStaticActionMenuItems(...arguments);
            if (!this.showDeleteAction) {
                delete items.delete;
            }
            return items;
        },
    };
}

patch(FormController.prototype, makeHideDeletePatch());
patch(ListController.prototype, makeHideDeletePatch());
