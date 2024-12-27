/** @odoo-module **/

import {registerInstancePatchModel} from "@mail/model/model_core";

registerInstancePatchModel("mail.chatter", "line_chatbot.ChatterPatch", {
    // Inherit the setup method to add the onClickSendLineMessage method
    _created() {
        this._super(...arguments);
        this.onClickSendLineMessage = this.onClickSendLineMessage.bind(this);
    },

    // Add the onClickSendLineMessage method
    onClickSendLineMessage() {
        // Rough copy of composer view function `openFullComposer`.
        // Get composer from thread.
        // We access data from the composer since history still is saved there.
        // e.g. open and close "Log note".
        const composer = this.thread.composer;
        console.log("composer", composer);
        console.log("composerxx", composer.suggestedRecipientInfo);

        const context = {
            default_model: this.threadModel,
            // Default_partner_ids: composer.recipients.map((partner) => partner.id),
            default_res_id: this.threadId,
        };
        const action = {
            type: "ir.actions.act_window",
            res_model: "line.compose.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context,
        };
        const options = {
            on_close: () => {
                if (composer.exists()) {
                    composer._reset();
                    if (composer.activeThread) {
                        composer.activeThread.loadNewMessages();
                    }
                }
            },
        };
        this.env.bus.trigger("do-action", {action, options});
    },
});
