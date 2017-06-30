/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', './CheckWikiLinkWidget'], function ($, CheckWikiLinkWidget) {
    var CheckEntityLinkWidget = function(elem){
        this.elem = elem;
        // TODO: Fix this.
        // this.linkVerificationWidget = new CheckWikiLinkWidget($("#wiki-verification-modal"));
    };
    CheckEntityLinkWidget.prototype.init = function(mention, cb){
        this.mention = mention;
        this.canonicalMention = this.mention.entity.mentions[0];
        //this.linkVerificationWidget.init(mention);
        this.cb = cb;
        //Check if canonical mention is the same as this mention
        if (this.mention.span[0] == this.canonicalMention.span[0] && this.mention.span[1] == this.canonicalMention.span[1]){
            this.done(true);
            return;
        }
        this.elem.find("#relation-options").empty(); // Clear.
        this.elem.find("#relation-option-preview").empty(); // Clear.
        this.elem.find("#relation-examples").empty();
        var yesDiv = this.makeRelnOption(0, "Yes", "fa-check", "DarkGreen");
        var noDiv = this.makeRelnOption(1, "No", "fa-times", "coral");
        if (this.mention.canonicalCorrect !== null && this.mention.canonicalCorrect == "Yes") yesDiv.addClass("btn-primary"); 
        if (this.mention.canonicalCorrect !== null && this.mention.canonicalCorrect == "No") noDiv.addClass("btn-primary"); 
        this.elem.find("#relation-options").append(yesDiv);
        this.elem.find("#relation-options").append(noDiv);
        this.updateText(this.renderTemplate(this.mention));

        //this.mention.tokens.forEach(function(t) {$(t).addClass("subject highlight");});
        this.canonicalMention.tokens.forEach(function(t) {$(t).addClass("canonical highlight");});
        $(this.canonicalMention.elem).parent().addClass("highlight");
    };
    CheckEntityLinkWidget.prototype.updateText = function(previewText) {
        var div = this.elem.find("#relation-option-preview");
        div.html(previewText || "");
    };
    CheckEntityLinkWidget.prototype.makeRelnOption = function(id, text, icon, color) {
        var self = this;
        var div = $("#relation-option").clone();
        div.html(div.html().replace("{short}", text));
        div.find('.icon').removeClass('hidden').addClass(icon).css('color', color);
        div.attr("id", "relation-option-" + id);
  
        div.on("click.kbpo.entityLinkWidget", function(evt) {
            var ret = (text == "Yes") ? true : false;
            self.done(ret);
        });

        return div;
    };

    // The widget selection is done -- send back results.
    CheckEntityLinkWidget.prototype.done = function(correctlyLinked) {
        // Clear the innards of the html.
        this.elem.find("#relation-options").empty();
        this.elem.find("#relation-option-preview").empty();
        this.elem.find("#relation-examples").empty();
        this.mention.entity.canonicalCorrect = correctlyLinked;
        var self = this;

        //if (correctlyLinked == "Yes") {
        //    //Now verify wiki linking
        //    // this.linkVerificationWidget.cb = function(){
        //    //     if (self.cb) {
        //    //         self.cb(correctlyLinked);
        //    //     } else {
        //    //         console.log("[Warning] Relation chosen but no callback", chosen_reln);
        //    //     }
        //    // };
        //    // this.linkVerificationWidget.show();
        //    //this.wikiLinkWidget
        //}
        //else {
            // Send a call back to the interface.
        if (this.cb) {
            this.cb(correctlyLinked);
        } else {
            console.log("[Warning] Relation chosen but no callback", chosen_reln);
        }
        //}
    };

    CheckEntityLinkWidget.prototype.renderTemplate = function(mention) {
        var template = "In the sentence you just read (shown below) does "+$('#mention-'+mention.id)[0].outerHTML+" refer to the <span class='canonical'>{canonical}</span> highlighted above?" + $('#sentence-'+mention.sentenceIdx).clone().addClass('highlight')[0].outerHTML;
        return template
            .replace("{mention}", mention.text())
            .replace("{canonical}", mention.entity.gloss);
    };

    return CheckEntityLinkWidget;
});
