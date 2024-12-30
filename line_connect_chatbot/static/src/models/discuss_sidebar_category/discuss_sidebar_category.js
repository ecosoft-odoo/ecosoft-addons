/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerIdentifyingFieldsPatch,
} from "@mail/model/model_core";
import {one2one} from "@mail/model/model_field";

registerFieldPatchModel(
    "mail.discuss_sidebar_category",
    "line_connect_chatbot.DiscussSidebarLINE",
    {
        discussAsLINEChat: one2one("mail.discuss", {
            inverse: "categoryLINEChat",
            readonly: true,
        }),
    }
);

registerIdentifyingFieldsPatch(
    "mail.discuss_sidebar_category",
    "line_connect_chatbot.DiscussFieldLINE",
    (identifyingFields) => {
        identifyingFields[0].push("discussAsLINEChat");
    }
);
