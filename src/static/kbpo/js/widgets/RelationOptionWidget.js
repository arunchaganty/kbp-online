/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

// TODO: Maybe move CheckEntityLinkWidget out?
define(['jquery', '../defs', '../util', './CheckEntityLinkWidget', './WikiLinkModal', './DateModal'], function ($, defs, util, CheckEntityLinkWidget, WikiLinkModal, DateModal) {
    function getCandidateRelations(mentionPair) {
        var candidates = [];
        defs.RELATIONS.forEach(function (reln) {
            if (reln.isApplicable(mentionPair)) candidates.push(reln);
        });
        return candidates;
    }

    /**
     * The relation widget is controlled by the RelationInterface. */
    var RelationOptionWidget = function(elem, docWidget, verifyLinks) {
        this.elem = elem;
        this.docWidget = docWidget;
        this.verifyLinks = verifyLinks || false;

        var self = this;
        util.getDOMFromTemplate('/static/kbpo/html/RelationOptionWidget.html', function(elem_) {
          self.elem.html(elem_.html());
          self.canonicalLinkWidget = new CheckEntityLinkWidget(elem);

          self.wikiLinkModal = new WikiLinkModal(function(elem_) {
            self.elem.find("#modals").append(elem_);
          });
          self.dateModal = new DateModal(function(elem_) {
            self.elem.find("#modals").append(elem_);
          });
        });
    };

    // initialize the interface using @mentionPair. On completion, call @cb.
    RelationOptionWidget.prototype.init = function(mentionPair, cb) {
        this.mentionPair = mentionPair;
        this.cb = cb;
        console.info("initializing relation widget for", mentionPair);

        this.relns = getCandidateRelations(mentionPair);
        this.elem.find("#relation-options").empty(); // Clear.
        this.elem.find("#relation-option-preview").empty(); // Clear.
        for (var i = 0; i < this.relns.length; i++) {
            var relnDiv = this.makeRelnOption(this.relns[i], i);
            // if this relation has already been selected, then show it in
            // a different color.
            if (this.mentionPair.relation !== null && this.mentionPair.relation.name == this.relns[i].name) {
                relnDiv.addClass("btn-primary"); 
            }
            this.elem.find("#relation-options").append(relnDiv);

            if (this.relns[i].examples.length > 0) {
                var relnHelp = this.makeRelnHelp(this.relns[i], i);
                this.elem.find("#relation-examples").append(relnHelp);
            }
        }

        this.updateText(this.renderTemplate(this.mentionPair));
    };

    RelationOptionWidget.prototype.updateText = function(previewText) {
        var div = this.elem.find("#relation-option-preview");
        div.html(previewText || "");
    };

    RelationOptionWidget.prototype.doLinkingVerification = function(mentionPair, doSubject) {
      console.assert(mentionPair.reln !== undefined);
      var self = this;
      var mention;
      if (doSubject) {
        mention = mentionPair.subject;
      } else {
        mention = mentionPair.object;
      }
      var canonicalMention = mention.entity.mentions[0];

      var linkDone = function (link) {
        if (link !== null) {
          console.assert(link !== undefined);
          mention.entity.linkGold = link;
        } else { // Couldn't find a link.
          mention.entity.linkGold = null;
        }
        if (doSubject) {
          self.doCanonicalVerification(mentionPair, false);
        } else {
          self.done(mentionPair.reln);
        }
      };

      if (mention.type.name === "TITLE") {
        linkDone(mention.entity.link);
      } else if (mention.type.name === "DATE") {
        // TODO: launch date modeal
        self.dateModal.doneListeners.length = 0; // fscking javascript
        self.dateModal.doneListeners.push(function (link) {linkDone(link);});
        self.dateModal.show(mention.gloss, mention.entity.link);
        linkDone(mention.entity.link);
      } else {
        // Alright, launch the WikiModal!
        entityStr = mention.entity.link.substring(0,5) == "wiki:" ? mention.entity.link.substring(5) : mention.entity.gloss;
        self.wikiLinkModal.cb = function (link) {linkDone(link);};
        self.wikiLinkModal.show(entityStr);
      }
    };

    RelationOptionWidget.prototype.doCanonicalVerification = function(mentionPair, doSubject) {
      var self = this;
      console.assert(mentionPair.reln !== undefined);

      var mention;
      if (doSubject) {
        mention = mentionPair.subject;
      } else {
        mention = mentionPair.object;
      }
      var canonicalMention = mention.entity.mentions[0];


      // Preheat entity linking
      if (mention.type.name === "TITLE") {
      } else if (mention.type.name === "DATE") {
      } else {
        // Preheat the entity linking widget in the background.
        var entityStr = mention.entity.link.substring(0,5) == "wiki:" ? mention.entity.link.substring(5) : mention.entity.gloss;
        self.wikiLinkModal.preload(entityStr);
      }

      // Check if this is a canonical mention
      if (mention.span[0] === canonicalMention.span[0] && mention.span[1] === canonicalMention.span[1]) {
        mention.canonicalCorrect = true; // tautologically.
        self.doLinkingVerification(mentionPair, doSubject);
      } else { // Uh, we need to verify this!
        mention.entity.linkGold = null;
        self.docWidget.centerOnMentionSpan(mention.entity.span);
        // Call canonical entity
        self.canonicalLinkWidget.init(mention, function(correctlyLinked) {
          mention.entity.canonicalCorrect = correctlyLinked;
          mention.entity.linkGold = null;
          if (correctlyLinked) { // Wiki time!
            self.doLinkingVerification(mentionPair, doSubject);
          } else if (doSubject) {
            self.doCanonicalVerification(mentionPair, false);
          } else {
            self.done(mentionPair.reln);
          }
        });
      }
    };

    RelationOptionWidget.prototype.makeRelnOption = function(reln, id) {
      var self = this;
      var div = $("#relation-option").clone();
      div.html(div.html().replace("{short}", reln.short));
      if (reln.image !== "") {
        div.find('img').removeClass('hidden').attr('src', '/static/kbpo/img/relations/'+reln.image);
      } else if(reln.icon !== "") {
        div.find('.icon').removeClass('hidden').addClass(reln.icon);
      } else {
        div.find('.icon').removeClass('hidden').addClass('fa-question-circle-o').css('color',  'coral');
      }
      div.attr("id", "relation-option-" + id);

      div.on("click.kbpo.relationWidget", function(evt) {
        $(self.mentionPair.subject).parent().removeClass("highlight");
        self.mentionPair.reln = reln;

        if (self.verifyLinks) {
          self.doCanonicalVerification(self.mentionPair, true);
        }
        else {
          self.done(reln);
          return false;
        }
      });
      // Update widget text. 
      //console.log(self.mentionPair);
      div.on("mouseenter.kbpo.relationWidget", function(evt) {self.updateText(reln.renderTemplate(self.mentionPair), this.verifyLinks);});
      div.on("mouseleave.kbpo.relationWidget", function(evt) {self.updateText(self.renderTemplate(self.mentionPair));});
      return div;
    };

    RelationOptionWidget.prototype.makeRelnHelp = function(reln, id) {
        var elem = $("<li>");
        elem.html("<b>{}</b>".replace("{}", reln.short));
        var elems = $("<ul>");
        for (var i = 0; i < reln.examples.length; i++) {
            elems.append($("<li>").html(
                        reln.examples[i]
                        .replace("{", "<span class='subject'>") 
                        .replace("}", "</span>") 
                        .replace("[", "<span class='object'>") 
                        .replace("]", "</span>") 
                        ));
        }
        elem.append(elems);
        return elem;
    };

    RelationOptionWidget.prototype.renderTemplate = function(mentionPair) {
        var template = "Please choose how <span class='subject'>{subject}</span> and <span class='object'>{object}</span> are related from the options below.";
        return template
            .replace("{subject}", mentionPair.subject.gloss)
            .replace("{object}", mentionPair.object.gloss);
    };

    // The widget selection is done -- send back results.
    RelationOptionWidget.prototype.done = function(chosen_reln) {
        // Clear the innards of the html.
        this.elem.find("#relation-options").empty();
        this.elem.find("#relation-option-preview").empty();
        this.elem.find("#relation-examples").empty();

        // Send a call back to the interface.
        if (this.cb) {
            this.cb(chosen_reln);
        } else {
            console.log("[Warning] Relation chosen but no callback", chosen_reln);
        }
    };

    return RelationOptionWidget;
});
