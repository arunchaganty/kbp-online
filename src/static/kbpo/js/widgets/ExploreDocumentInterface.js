/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../defs', '../util', './DocWidget', './RelationListWidget'], function ($, defs, util, DocWidget, RelationListWidget) {
  /**
   * Stores actual relations and iterates through every mention pair in
   * the document, controlling various UI elements.
   */
  var ExploreDocumentInterface = function(elem) {
    var self = this;
    self.elem = elem;

    util.getDOMFromTemplate('/static/kbpo/html/ExploreDocumentInterface.html', function(elem_) {
      self.elem.html(elem_.html());
      self.docWidget = new DocWidget($("#document"));
      self.listWidget = new RelationListWidget($("#relation-list-widget"));

      self.listWidget.mouseEnterListeners.push(function(p) {self.highlightExistingMentionPair(p);});
      self.listWidget.mouseLeaveListeners.push(function(p) {self.unhighlightExistingMentionPair(p);});

      self.docWidget.elem[0].scrollTop = 0;
      self.readyListeners.forEach(function(cb) {cb(self);});
    });
  };
  ExploreDocumentInterface.prototype.readyListeners = [];
  ExploreDocumentInterface.prototype.onReady = function(cb) {
    this.readyListeners.push(cb);
  };

  ExploreDocumentInterface.prototype.loadMentionPairs = function(mentionPairs) {
    var self = this;
    // First load the mentions into the document.
    var mentions = {};

    var mentionPair, subject, object;
    for (var i = 0; i < mentionPairs.length; i++) {
      mentionPair = mentionPairs[i];
      if (mentions[mentionPair.subject.span] === undefined) {
        subject = defs.Mention.fromJSON(mentionPair.subject, self.docWidget);
        self.docWidget.addMention(subject);
        mentions[subject.span] = subject;
      }
      if (mentions[mentionPair.object.span] === undefined) {
        object = defs.Mention.fromJSON(mentionPair.object, self.docWidget);
        self.docWidget.addMention(object);
        mentions[object.span] = object;
      }
    }

    self.mentionPairs = [];
    for (i = 0; i < mentionPairs.length; i++) {
      mentionPair = mentionPairs[i];
      subject = mentions[mentionPair.subject.span];
      object = mentions[mentionPair.object.span];
      console.assert(subject !== undefined);
      console.assert(object !== undefined);

      self.mentionPairs.push({'subject': subject, 'object': object, 'id': i, 'relation': null});
    }

    console.assert(self.mentionPairs.length > 0);
  };

  ExploreDocumentInterface.prototype.loadRelations = function(relations) {
    var self = this;
    // TODO: Add each relation into listWidget. 
  };


  function centerOnMention(m) {
    var sentence = $(m.elem).parent();
    var elem = sentence[0];

    var topPosRel = elem.offsetTop;
    var parentPosRel = $('#document')[0].offsetTop;
    $('#document').scrollTop(topPosRel - parentPosRel);
  }
  function centerOnMentionPair(p) {
    if (p.subject.span[0] < p.object.span[0])
      centerOnMention(p.subject);
    else
      centerOnMention(p.object);
  }

  ExploreDocumentInterface.prototype.highlightExistingMentionPair = function(mentionPair) {
    this.unselect(this.mentionPair);
    this.select(mentionPair);
  };
  ExploreDocumentInterface.prototype.unhighlightExistingMentionPair = function(mentionPair) {
    this.unselect(mentionPair);
    this.select(this.mentionPair);
  };

  return ExploreDocumentInterface;
});
