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

  // Iterates through the mention pairs that need to be verified.
  RelationInterface.prototype.runVerify = function(relations) {
    var self = this;
    this.mentionPairs = [];
    relations.forEach(function(rel, idx){
      var link, canonicalMention;
      //If object is PER, swap with subject
      if(rel.object.type == 'PER'){
        var temp = rel.object;
        rel.object = rel.subject;
        rel.subject = temp;
      }
      rel.subject.tokens = self.docWidget.getTokens(rel.subject.doc_char_begin, rel.subject.doc_char_end);
      if(rel.subject.tokens.length >0){
        rel.subject = new Mention(rel.subject);
        self.docWidget.addMention(rel.subject);
      }
      //TODO: Create a mention and add entity 
      if (rel.subject.entity !== undefined) {
        rel.subject.entity.type = rel.subject.type;
        rel.subject.entity.tokens = self.docWidget.getTokens(rel.subject.entity.doc_char_begin, rel.subject.entity.doc_char_end);
        link = rel.subject.entity.link;
        canonicalMention = new Mention(rel.subject.entity);
        self.docWidget.addMention(canonicalMention);
        rel.subject.entity = new Entity(canonicalMention);
        rel.subject.entity.link = link;
      }
      rel.object.tokens = self.docWidget.getTokens(rel.object.doc_char_begin, rel.object.doc_char_end);
      if(rel.object.tokens.length >0){
        rel.object = new Mention(rel.object);
        self.docWidget.addMention(rel.object);
        //TODO: Check if entities need to be added as well
      }
      //TODO: Create a mention and add entity 
      if (rel.object.entity !== undefined){
        rel.object.entity.type = rel.object.type;
        rel.object.entity.tokens = self.docWidget.getTokens(rel.object.entity.doc_char_begin, rel.object.entity.doc_char_end);
        link = rel.object.entity.link;
        canonicalMention = new Mention(rel.object.entity);
        self.docWidget.addMention(canonicalMention);
        rel.object.entity = new Entity(canonicalMention);
        rel.object.entity.link = link;
      }
      self.mentionPairs.push({'subject': rel.subject, 'object': rel.object, 'id': idx, 'relation': null});
    });
    this.currentIndex = -1;
    this.viewStack = [];
    this.next();
  };

  RelationInterface.prototype.run = function(mentions) {
    var self = this;
    this.mentions = [];

    mentions.forEach(function (m) {
      m.tokens = self.docWidget.getTokens(m.doc_char_begin, m.doc_char_end);
      if (m.tokens.length > 0) {
        m = new Mention(m);
        self.docWidget.addMention(m);
        self.mentions.push(m);
      }
    });
    this.mentionPairs = this.constructMentionPairs(this.mentions);

    this.currentIndex = -1;
    this.viewStack = []; // Used when changing relations.
    this.next();
  };

  function outOfSentenceLimit(m, n) {
    return Math.abs(m.sentenceIdx - n.sentenceIdx) > 1;
  }

  function isRelationCandidate(m, n) {
    if (m.gloss == n.gloss) return false;
    if (m.entity.link == n.entity.link) return false;
    if (m.type.name == "PER") {
      return true;
    } else if (m.type.name == "ORG") {
      return n.type.name !== "PER" && n.type.name !== "TITLE";
    } else { // All other mentions are not entities; can't be subjects.
      return false;
    }
  }

  function notDuplicated(pairs, m, n) {
    // Only need to look backwards through list until the sentence
    // limit
    console.log(pairs);
    for(var i = pairs.length-1; i >= 0; i--) {
      var m_ = pairs[i].subject;
      var n_ = pairs[i].object;

      if (outOfSentenceLimit(m, m_) || 
          outOfSentenceLimit(m, n_) || 
          outOfSentenceLimit(n, m_) || 
          outOfSentenceLimit(n, n_)) break;
      if (m_ === n && n_ == m) return false;
    }
    return true;
  }

  // For every pair of mentions in a span of (2) sentences.
  RelationInterface.prototype.constructMentionPairs = function(mentions) {
    var pairs = [];

    //var seenEntities = {}; // If you see two entities with the same link, don't ask for another relation between them?

    // Get pairs.
    var i, j;
    for (i = 0; i < mentions.length; i++) {
      var m = mentions[i];
      var n;
      // - Go backwards until you cross a sentence boundary.
      for (j = i-1; j >= 0; j--) {
        n = mentions[j];
        if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 0) break;

        // Check that the pair is type compatible and not duplicated.
        if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n)) {
          pairs.push({'subject':m,'object':n});
        }
      }
      // - Go forwards until you cross a sentence boundary.
      for (j = i+1; j < mentions.length; j++) {
        n = mentions[j];
        if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 0) break;
        // Check that the pair is type compatible and not duplicated.
        if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n))
          pairs.push({'subject':m,'object':n});
      }
    }
    for (i = 0; i < pairs.length; i++) {
      pairs[i].id = i;
      pairs[i].relation = null; // The none relation.
    }

    return pairs;
  };

  function centerOnMention(m) {
    var sentence = $(m.elem).parent();
    var elem = sentence[0];

    /*if (sentence.prev().length > 0) {
      elem = sentence.prev()[0];
    //.scrollIntoView(true);
    } else {
    elem = sentence[0];
    //.scrollIntoView(true);
    }*/
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
