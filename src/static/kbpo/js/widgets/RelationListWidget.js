/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../util'], function ($, util) {
    RelationListWidget = function(elem) {
        this.elem = elem;
        util.getDOMFromTemplate('/static/kbpo/html/RelationListWidget.html', function(elem_) {
          elem.html(elem_.html());
        });
    };

    RelationListWidget.prototype.mouseEnterListeners = [];
    RelationListWidget.prototype.mouseLeaveListeners = [];
    RelationListWidget.prototype.clickListeners = [];

    RelationListWidget.prototype.addRelation = function(mentionPair) {
        var self = this;

        // Make sure that #empty-extraction is hidden.
        this.elem.find("#extraction-empty").addClass("hidden");

        // Create a new relation to add to the list.
        var div = this.elem.find("#extraction-template").clone();
        div.find(".relation-sentence").html(mentionPair.relation.renderTemplate(mentionPair));
        div.removeClass("hidden");
        div.attr("id", "mention-pair-" + mentionPair.id);
        div[0].mentionPair = mentionPair;

        // attach listeners.
        div.on("mouseenter.kbpo.list", function(evt) {
            //console.log("mention.mouseenter", mentionPair);
            self.mouseEnterListeners.forEach(function(cb) {cb(mentionPair);});
        });
        div.on("mouseleave.kbpo.list", function(evt) {
            //console.log("mention.mouseleave", mentionPair);
            self.mouseLeaveListeners.forEach(function(cb) {cb(mentionPair);});
        });
        div.on("click.kbpo.click", function(evt) {
            //console.log("mention.cancel", mentionPair);
            self.clickListeners.forEach(function(cb) {cb(mentionPair);});
        });

        this.elem.append(div);
        return true;
    };

    RelationListWidget.prototype.removeRelation = function(mentionPair) {
        this.elem.find(".extraction")
            .filter(function (_, e) {
                return e.mentionPair !== undefined && e.mentionPair.id == mentionPair.id;})
            .remove();
        if (this.elem.find(".extraction").length == 2) {
            this.elem.find("#extraction-empty").removeClass("hidden");
        }
    };

    RelationListWidget.prototype.relations = function() {
        return this.elem.find(".extraction").not("#extraction-empty").not("#extraction-template");
    };

    return RelationListWidget;
});
