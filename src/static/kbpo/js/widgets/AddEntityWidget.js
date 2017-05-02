/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../defs'], function ($, defs) {
    var AddEntityWidget = function(elem_) {
        this.elem = elem_;

        var self = this;
        var triggerClickListeners = function (evt) {
            var type = this._type;
            self.clickListeners.forEach(function(cb) {cb(type);});
        };

        for (var i = 0; i < Object.keys(defs.TYPES).length; i++) {
            var type = defs.TYPES[Object.keys(defs.TYPES)[i]];
            var elem = this.elem.find("#type-template").clone();
            elem
                .removeClass("hidden")
                .attr("id", "type-" + type.name)
                .attr("disabled", "disabled")
                ;
            elem.html(elem.html()
                    .replace("{icon}", type.icon)
                    .replace("{name}", type.gloss)
                    );
            elem[0]._type = type;
            elem.on("click.kbpo.addEntityWidget", triggerClickListeners);
            this.elem.find("#types").append(elem);
        }
        this.deactivate();
    };

    AddEntityWidget.prototype.clickListeners = [];
    AddEntityWidget.prototype.activate = function() {
        this.elem
            .find(".type")
            .not("#type-template")
            .removeAttr("disabled");
        this.elem.removeClass("hidden");
    };
    AddEntityWidget.prototype.deactivate = function() {
        this.elem
            .find(".type")
            .not("#type-template")
            .attr("disabled", "disabled");
        this.elem.removeClass("hidden");
    };
    AddEntityWidget.prototype.hide = function() {
        this.elem.addClass("hidden");
    };

    return AddEntityWidget;
});
