/*!
 * set vi:sw=2 ts=2
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', 'sprintf-js/dist/sprintf.min', '../defs', '../util', './DocWidget', './InstructionWidget', './RelationOptionWidget', './RelationListWidget'], function ($, pp, defs, util, DocWidget, InstructionWidget, RelationOptionWidget, RelationListWidget) {

  VERSION = 0.2;

  function checkResponse(resp) {
    console.assert(resp.version === VERSION, "Version incorrectly set");
    console.assert(resp.doc_id !== undefined);
    console.assert(resp.subject !== undefined);
    console.assert(resp.object !== undefined);
    console.assert(resp.relation !== undefined);
    
    var mentions = [resp.subject, resp.object];
    var entities = [];
    var i;
    for (i=0; i < mentions.length; i++) {
      if(mentions[i] === undefined) continue;
      mention = mentions[i];
      console.assert(mention.type !== undefined);
      console.assert(mention.span !== undefined);
      console.assert(mention.gloss !== undefined);
      console.assert(mention.entity !== undefined);
      if (mention.entity !== undefined) {
        entities.push(mention.entity);
      }
    }
    for (i=0; i < entities.length; i++) {
      if(entities[i] === undefined) continue;
      entity = entities[i];
      console.assert(entity.type !== undefined);
      console.assert(entity.span !== undefined);
      console.assert(entity.gloss !== undefined);
      console.assert(entity.link !== undefined);
      console.assert(entity.linkGold !== undefined);
      console.assert(entity.canonicalCorrect !== undefined);
    }
  }


  /**
   * Stores actual relations and iterates through every mention pair in
   * the document, controlling various UI elements.
   */
  var RelationInterface = function(docWidget, root, optionElem, verifyLinks) {
    var self = this;
    this.docWidget = docWidget; 
    this.root = root;
    this.verifyLinks = verifyLinks;
    this.startTime = new Date().getTime();

    util.getDOMFromTemplate('/static/kbpo/html/RelationInterface.html', function(elem_) {
      self.root.html(elem_.html());
      self.optionWidget = new RelationOptionWidget(optionElem, docWidget, verifyLinks);
      self.listWidget = new RelationListWidget($("#relation-list-widget"));

      self.instructionWidget = new InstructionWidget("kbpo-relations-" + self.verifyLinks + VERSION, 
        self.verifyLinks ?  "/static/kbpo/html/InstructionsRelations.html"
                         : "/static/kbpo/html/InstructionsRelationsExhaustive.html");

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
        var docId = self.docWidget.doc.id;
        var relations = [];
        self.mentionPairs.forEach(function(e){
          relations.push({
            "version": VERSION,
            "doc_id": docId,
            "subject": (e.subject).toJSON(),
            "relation": e.relation.name,
            "object": (e.object).toJSON(),
          });
        });

        var assignmentId = $("input[name='assignmentId']").val();
        var hitId = $("input[name='hitId']").val();
        var workerId = $("input[name='workerId']").val();
        var csrftoken =  $("input[name='csrfmiddlewaretoken']").val();
        var data = JSON.stringify(relations);
        relations.forEach(checkResponse);
        var workerTime = (new Date().getTime() - self.startTime) / 1000;
        var comments = $("#comments").val();

        $("#workerTime").attr('value', workerTime);
        $("#response").attr('value', data);

        self.doneListeners.forEach(function(cb) {cb(data);});
        if (assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE") {
            alert("You must accept this HIT before submitting");
            return false;
        } else {
            // Send out to server.
            $.ajax({
                type: "POST",
                url: "",
                data: {
                    "csrfmiddlewaretoken": csrftoken,
                    "hitId": hitId,
                    "assignmentId": assignmentId,
                    "workerId": workerId,
                    "response": data,
                    "workerTime": workerTime,
                    "comments": comments,
                },
                success: function() {
                  return $("#mturk_form").submit();
                }
            });
            return false;
        }
      });
    });
  };

  RelationInterface.prototype.doneListeners = [];

  RelationInterface.prototype.loadMentionPairs = function(mentionPairs) {
    var self = this;

    // First load the mentions into the document.
    var mentions = {};

    var mentionPair, subject, object;
    for (var i = 0; i < mentionPairs.length; i++) {
      mentionPair = mentionPairs[i];
      mentionPair.id = i;
      if (mentionPair.subject.entity.type === undefined) {
        mentionPair.subject.entity.type = mentionPair.subject.type;
      }
      if (mentionPair.object.entity.type === undefined) {
        mentionPair.object.entity.type = mentionPair.object.type;
      }


      if (mentions[mentionPair.subject.span] === undefined) {
        subject = defs.Mention.fromJSON(mentionPair.subject, self.docWidget);
        self.docWidget.addMention(subject);
        mentions[subject.span] = subject;
      }
      if (mentions[mentionPair.subject.entity.span] === undefined) {
        subject_canonical = defs.Mention.fromJSON(mentionPair.subject.entity, self.docWidget);
        self.docWidget.addMention(subject_canonical);
        mentions[subject_canonical.span] = subject_canonical;
      }

      if (mentions[mentionPair.object.span] === undefined) {
        object = defs.Mention.fromJSON(mentionPair.object, self.docWidget);
        self.docWidget.addMention(object);
        mentions[object.span] = object;
      }
      if (mentions[mentionPair.object.entity.span] === undefined) {
        object_canonical = defs.Mention.fromJSON(mentionPair.object.entity, self.docWidget);
        self.docWidget.addMention(object_canonical);
        mentions[object_canonical.span] = object_canonical;
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

  RelationInterface.prototype.run = function() {
    console.assert(this.mentionPairs.length > 0);
    this.currentIndex = -1;
    this.viewStack = []; // Used when changing relations.
    this.next();
  };

  RelationInterface.prototype.setReward = function(reward) {
    $("#reward").text(pp.sprintf("$%0.02f", reward));
  };

  RelationInterface.prototype.setDuration = function(time) {
    var lowerTime = Math.floor(0.8 * time / 60);
    var upperTime = Math.ceil(1.2 * time / 60);
    $("#estimated-time").text(pp.sprintf("%d - %d minutes", lowerTime, upperTime));
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

    if (idx !== undefined) {
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
      $("#relation-option-widget").removeClass("hidden");
    }
    var mentionPair = this.mentionPairs[this.currentIndex];

    this.mentionPair = mentionPair;
    this.select(mentionPair);
    this.optionWidget.init(mentionPair, function(reln) {
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
    $("#relation-option-widget").addClass("hidden");
  };

  return RelationInterface;
});
