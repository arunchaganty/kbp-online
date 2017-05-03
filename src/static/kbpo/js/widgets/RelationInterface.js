/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../util', './DocWidget', './RelationOptionWidget', './RelationListWidget'], function ($, util, DocWidget, RelationOptionWidget, RelationListWidget) {
  /**
   * Stores actual relations and iterates through every mention pair in
   * the document, controlling various UI elements.
   */
  var RelationInterface = function(docWidget, root, optionElem, verifyLinks) {
    var self = this;
    this.docWidget = docWidget; 
    this.root = root;
    this.verifyLinks = verifyLinks;

    util.getDOMFromTemplate('/static/kbpo/html/RelationInterface.html', function(elem_) {
      self.root.html(elem_.html());
      self.relnWidget = new RelationOptionWidget(optionElem, verifyLinks);
      self.listWidget = new RelationListWidget($("#relation-list-widget"));

      self.listWidget.mouseEnterListeners.push(function(p) {self.highlightExistingMentionPair(p);});
      self.listWidget.mouseLeaveListeners.push(function(p) {self.unhighlightExistingMentionPair(p);});
      self.listWidget.clickListeners.push(function(p) {self.editExistingMentionPair(p);});

      self.docWidget.elem[0].scrollTop = 0;

      $("#done")[0].disabled = true;
      $("#back")[0].disabled = true;

      $("#back").on("click.kbpo.interface", function (evt) {
        self.editExistingMentionPair(self.mentionPairs[self.currentIndex-1]); 
        return false;
      });

      $("#done").on("click.kbpo.interface", function (evt) {
        var relations = [];
        self.mentionPairs.forEach(function(e){
          relations.push({
            "subject": (e.subject).toJSON(),
            "relation": e.relation.name,
            "object": (e.object).toJSON(),
          });
        });
        var data = JSON.stringify(relations);
        $("#relations-output").attr('value', data);
        $("#td").attr('value', new Date().getTime() / 1000 - st);
        self.doneListeners.forEach(function(cb) {cb(data);});
        //return true;
      });
    });
  };

  RelationInterface.prototype.doneListeners = [];

  RelationInterface.prototype.loadMentionPairs = function(mentionPairs) {
    var self = this;

    var mentions = [];
    self.mentionPairs = [];
    for (var i = 0; i < mentionPairs.length; i++) {
      var mentionPair = mentionPairs[i];
      // Add mention pairs to mentions.
      subject = Mention.fromJSON(mentionPair.subject, self.docWidget);
      object = Mention.fromJSON(mentionPair.object, self.docWidget);

      mentions.push(subject);
      mentions.push(object);
      self.mentionPairs.push({'subject': subject, 'object': object, 'id': idx, 'relation': null});
    }

    var seen = new Set();
    for (i = 0; i < mentions.length; i++) {
      var mention = mentions[i];
      var key = mention.doc_char_begin + "-" + mention.doc_char_end;
      if (!seen.has(key)) {
        self.docWidget.addMention(mention);
        seen.add(key);
      }
    }
  };

  RelationInterface.prototype.run = function() {
    console.assert(self.mentionPairs.length > 0);
    this.currentIndex = -1;
    this.viewStack = []; // Used when changing relations.
    this.next();
  };

  function centerOnMention(m) {
    var sentence = $(m.elem).parent();
    var elem = sentence[0];

    var topPosRel = elem.offsetTop;
    console.log(topPosRel);
    var parentPosRel = $('#document')[0].offsetTop;
    console.log(parentPosRel);
    $('#document').scrollTop(topPosRel - parentPosRel);
  }

  function centerOnMentionPair(p) {
    if (p.subject.doc_char_begin < p.object.doc_char_begin)
      centerOnMention(p.subject);
    else
      centerOnMention(p.object);
  }

  // Draw mention pair
  RelationInterface.prototype.select = function(mentionPair) {
    // Move to the location.
    centerOnMentionPair(mentionPair);
    mentionPair.subject.tokens.forEach(function(t) {$(t).addClass("subject highlight");});
    mentionPair.object.tokens.forEach(function(t) {$(t).addClass("object highlight");});
    $(mentionPair.subject.elem).parent().addClass("highlight");

  };

  RelationInterface.prototype.unselect = function(mentionPair) {
    mentionPair.subject.tokens.forEach(function(t) {$(t).removeClass("subject highlight");});
    mentionPair.object.tokens.forEach(function(t) {$(t).removeClass("object highlight");});
    $(mentionPair.subject.elem).parent().removeClass("highlight");
  };

  RelationInterface.prototype.highlightExistingMentionPair = function(mentionPair) {
    this.unselect(this.mentionPair);
    this.select(mentionPair);
  };
  RelationInterface.prototype.unhighlightExistingMentionPair = function(mentionPair) {
    this.unselect(mentionPair);
    this.select(this.mentionPair);
  };
  RelationInterface.prototype.editExistingMentionPair = function(mentionPair) {
    this.unselect(this.mentionPair);
    if (this.viewStack.length === 0) this.viewStack.push(this.currentIndex);
    this.next(mentionPair.id);
  };

  // Progress to the next mention pair.
  RelationInterface.prototype.next = function(idx) {
    var self = this;

    if (idx !== null) {
      this.currentIndex = idx;
    } else if (this.viewStack.length > 0) {
      this.currentIndex = this.viewStack.pop();
    } else {
      this.currentIndex += 1;
    }
    if (this.currentIndex > 0) {
      $("#back")[0].disabled = false;
    } else {
      $("#back")[0].disabled = true;
    }
    if (this.currentIndex > this.mentionPairs.length - 1) {
      return this.done();
    } else {
      $("#relation-row").removeClass("hidden");
    }
    var mentionPair = this.mentionPairs[this.currentIndex];

    this.mentionPair = mentionPair;
    this.select(mentionPair);
    this.relnWidget.init(mentionPair, function(reln) {
      self.unselect(mentionPair);

      // Remove a previous relation from the list if it existed.
      if (mentionPair.relation && mentionPair.relation.name != reln.name) {
        self.listWidget.removeRelation(mentionPair);
      } 
      if (mentionPair.relation && mentionPair.relation.name == reln.name) {
      } else {
        // Set the relation of the pair.
        mentionPair.relation = reln;
        // Add mention to the relationList widget.
        if (reln.name != "no_relation") {
          self.listWidget.addRelation(mentionPair);
        }
      }

      self.next();
    }, this.verify);
  };

  // Called when the interface is done.
  RelationInterface.prototype.done = function() {
    // Hide the relation panel, and show the Done > (submit) button.
    $("#done")[0].disabled = false;
    $("#relation-row").addClass("hidden");
  };

  return RelationInterface;
});
