/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function ($) {
    var CheckEntityLinkWidget = function(elem){
        this.elem = elem;
        this.linkVerificationWidget = new CheckWikiLinkWidget($("#wiki-verification-modal"));
    };
    CheckEntityLinkWidget.prototype.init = function(mention, cb){
        this.mention = mention;
        this.canonicalMention = this.mention.entity.mentions[0];
        this.linkVerificationWidget.init(mention);
        this.cb = cb;
        //Check if canonical mention is the same as this mention
        if (this.mention.doc_char_begin == this.canonicalMention.doc_char_begin && this.mention.doc_char_end == this.canonicalMention.doc_char_end){
            this.done('Yes');
            return;
        }
        this.elem.find("#relation-options").empty(); // Clear.
        this.elem.find("#relation-option-preview").empty(); // Clear.
        this.elem.find("#relation-examples").empty();
        var yesDiv = this.makeRelnOption("Yes", "fa-check", "DarkGreen");
        var noDiv = this.makeRelnOption("No", "fa-times", "coral");
        if (this.mention.canonicalCorrect !== null && this.mention.canonicalCorrect == "Yes") yesDiv.addClass("btn-primary"); 
        if (this.mention.canonicalCorrect !== null && this.mention.canonicalCorrect == "No") noDiv.addClass("btn-primary"); 
        this.elem.find("#relation-options").append(yesDiv);
        this.elem.find("#relation-options").append(noDiv);
        this.updateText(this.renderTemplate(this.mention));

        centerOnMention(this.canonicalMention);
        //this.mention.tokens.forEach(function(t) {$(t).addClass("subject highlight");});
        this.canonicalMention.tokens.forEach(function(t) {$(t).addClass("canonical highlight");});
        $(this.canonicalMention.elem).parent().addClass("highlight");
    };
    CheckEntityLinkWidget.prototype.updateText = function(previewText) {
        var div = this.elem.find("#relation-option-preview");
        div.html(previewText || "");
    };
    CheckEntityLinkWidget.prototype.makeRelnOption = function(text, icon, color) {
        var self = this;
        var div = $("#relation-option-widget").clone();
        div.html(div.html().replace("{short}", text));
        div.find('.icon').removeClass('hidden').addClass(icon).css('color',  color);
        div.on("click.kbpo.checkEntityLinkWidget", function(evt) {
            self.done(text);
        });
        // Update widget text. 
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

        if (correctlyLinked == "Yes"){
            //Now verify wiki linking
            this.linkVerificationWidget.cb = function(){
                if (self.cb) {
                    self.cb(correctlyLinked);
                } else {
                    console.log("[Warning] Relation chosen but no callback", chosen_reln);
                }
            };
            this.linkVerificationWidget.show();

            //this.wikiLinkWidget
        }
        else{
            // Send a call back to the interface.
            if (this.cb) {
                this.cb(correctlyLinked);
            } else {
                console.log("[Warning] Relation chosen but no callback", chosen_reln);
            }
        }
    };

    CheckEntityLinkWidget.prototype.renderTemplate = function(mention) {
        var template = "In the sentence you just read (shown below) does "+$('#mention-'+mention.id)[0].outerHTML+" refer to the <span class='canonical'>{canonical}</span> highlighted above?" + $('#sentence-'+mention.sentenceIdx).clone().addClass('highlight')[0].outerHTML;
        return template
            .replace("{mention}", mention.text())
            .replace("{canonical}", mention.entity.gloss);
    };

    return CheckEntityLinkWidget;
});
