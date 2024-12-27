/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from "@mail/model/model_core";
import {one2one} from "@mail/model/model_field";

registerInstancePatchModel("mail.discuss", "line_chatbot.DiscussLINE", {
    /**
     * @override
     */
    onInputQuickSearch(value) {
        if (!this.sidebarQuickSearchValue) {
            this.categoryLINEChat.open();
        }
        return this._super(value);
    },
});

registerFieldPatchModel("mail.discuss", "line_chatbot.DiscussLINEField", {
    /**
     * Discuss sidebar category for `livechat` channel threads.
     */
    categoryLINEChat: one2one("mail.discuss_sidebar_category", {
        inverse: "discussAsLINEChat",
        isCausal: true,
    }),
});
