/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function ($) {
    var EntityListWidget = function(elem) {
        this.elem = elem;
    };

    EntityListWidget.prototype.clickListeners = [];
    EntityListWidget.prototype.mouseEnterListeners = [];
    EntityListWidget.prototype.mouseLeaveListeners = [];

    // A span in the text has been selected; activate this UI.
    EntityListWidget.prototype.activate = function(mention) {
        this.elem.find("*").removeAttr("disabled");
        // Find all entities that are very similar to this one and suggest them.

        if (mention.entity) {
            $(mention.entity.elem).addClass('list-group-item-success');
        } else {
            var entities = this.entities();
            for(var i = 0; i < entities.length; i++) {
                if(mention.tokens[0].token.pos_tag != 'PRP'){
                    if (entities[i].entity.levenshtein(mention.gloss.toLowerCase()) <= 2) {
                        $(entities[i]).addClass('list-group-item-warning');
                        this.scrollEntityIntoView(entities[i]);
                    }
                }
            }
        }
    };

    EntityListWidget.prototype.deactivate = function() {
        this.elem.find("*").attr("disabled", "disabled");

        this.currentEntity = null;
        this.elem.find('.list-group-item-success').removeClass("list-group-item-success");
        this.elem.find('.list-group-item-warning').removeClass('list-group-item-warning');
    };

    // Get current entities
    EntityListWidget.prototype.scrollEntityIntoView = function(entity) {
        var topPosRel = entity.offsetTop;
        var parentPosRel = this.elem.parent()[0].offsetTop;
        this.elem.parent().scrollTop(topPosRel - parentPosRel);
        //$(entity).position();
    };
    EntityListWidget.prototype.entities = function() {
        return this.elem.find(".entity").not("#entity-empty").not("#entity-template");
    };

    EntityListWidget.prototype.addEntity = function(entity) {
        var self = this;
        var elem = $('#entity-template')
            .clone()
            .removeClass('hidden')
            .attr("id", entity.id)
            ;
        elem.html(elem.html()
                .replace("{icon}", entity.type.icon)
                .replace("{gloss}", entity.gloss)
                .replace("{id}", entity.idx)
                );
        elem.on("click.kbpo.entityListWidget", function(evt) {
            self.clickListeners.forEach(function(cb) {cb(entity);});
        });
        elem.on("mouseenter.kbpo.entityListWidget", function(evt) {
            self.mouseEnterListeners.forEach(function(cb) {cb(entity);});
        });
        elem.on("mouseleave.kbpo.entityListWidget", function(evt) {
            self.mouseLeaveListeners.forEach(function(cb) {cb(entity);});
        });
        elem.prop("checked", "checked");

        elem[0].entity = entity;
        entity.elem = elem[0];

        // Insert into the list in a sorted order.
        // Remove the 'empty box';
        $("#entity-empty").addClass("hidden");
        var entities = this.entities();

        // Sorted based on the tuple (type, name)
        for (var i = 0; i < entities.length; i++) {
            if ((entity.type.idx < entities[i].entity.type.idx) || 
                (entity.type.idx == entities[i].entity.type.idx && 
                     entity.gloss.toLowerCase() <= entities[i].entity.gloss.toLowerCase())) {
                elem.insertBefore(entities[i]);
                break;
            }
        }
        if (i == entities.length) {
            this.elem.append(elem);
        }
    };
    EntityListWidget.prototype.removeEntity = function(entity) {
        entity.elem.remove();
        if (this.entities().length === 0) {
            this.elem.find("#entity-empty").removeClass("hidden");
        }
    };
    EntityListWidget.prototype.highlight = function(entity) {
        $(entity.elem).addClass("highlight");
    };
    EntityListWidget.prototype.unhighlight = function(entity) {
        $(entity.elem).removeClass("highlight");
    };

    return EntityListWidget;
});
