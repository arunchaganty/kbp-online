/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../defs','../util', './DocWidget', './EntityListWidget', './AddEntityWidget', './RemoveSpanWidget', './DateModal', './WikiLinkModal'], function ($, defs, util, DocWidget, EntityListWidget, AddEntityWidget, RemoveSpanWidget, DateModal, WikiLinkModal) {

  var EntityInterface = function(docWidget, elem) {
    var self = this;
    this.elem = elem;
    this.startTime = new Date().getTime();

    // Inject HTML into DOM
    util.getDOMFromTemplate('/static/kbpo/html/EntityInterface.html', function(elem_) {
      self.elem.html(elem_.html());
      self.dateModal = new DateModal(function(elem_) {
        self.dateModal.cb = function(link) {self.processLinkingDone(link);};
        self.elem.append(elem_);
      });
      self.wikiLinkModal = new WikiLinkModal(function(elem_) {
        self.wikiLinkModal.cb = function(link) {self.processLinkingDone(link);};
        self.elem.append(elem_);
      });

      self.docWidget = docWidget;
      self.docWidget.highlightListeners.push(function(selection) {self.processSpanSelection(selection);});
      self.docWidget.clickListeners.push(function(mention) {self.processMentionClick(mention);});

      self.listWidget = new EntityListWidget($("#entity-list-widget"), function() {
        self.listWidget.clickListeners.push(function(entity) {self.processEntityClick(entity);});
        self.listWidget.mouseEnterListeners.push(function(entity) {self.processEntityMouseEnter(entity);});
        self.listWidget.mouseLeaveListeners.push(function(entity) {self.processEntityMouseLeave(entity);});
      });

      self.addEntityWidget = new AddEntityWidget($("#add-entity-widget"), function() {
        self.addEntityWidget.clickListeners.push(function(type) {self.processTypeSelected(type);});
      });
      self.removeSpanWidget = new RemoveSpanWidget($("#remove-span-widget"), function() {
        // Attach a listener for entity selections.
        self.removeSpanWidget.clickListeners.push(function() {self.processRemoveSpan();});
      });

      self.entities = [];
      self.currentMention = null;

      //$("#done")[0].disabled = false;
      $("#done").on("click.kbpo.interface", function (evt) {
        var entities = [];
        for (var i = 0; i < self.entities.length; i++) {
          var entity = self.entities[i];
          for (var j = 0; j < entity.mentions.length; j++) {
            var mention = entity.mentions[j];
            entities.push(mention.toJSON());
          }
        }
        var data = JSON.stringify(entities);
        $("#workerTime").attr('value', (new Date().getTime() - self.startTime) / 1000);
        $("#response").attr('value', data);
        self.doneListeners.forEach(function(cb) {cb(data);});
      });
    });
  };
  entities = {};

  EntityInterface.prototype.doneListeners = [];

  EntityInterface.prototype.minOutput = function() {
    return this.entities.length > 0;
  };
  EntityInterface.prototype.deactivate = function() {
    this.listWidget.deactivate();
    this.addEntityWidget.deactivate();
    this.removeSpanWidget.deactivate();

    // Unhighlight any selection.
    if (this.currentMention) {
      // Only keep a mention if it has already been assigned an entity.
      this.docWidget.unselectMention(this.currentMention);
      if (!this.currentMention.entity || !this.currentMention.entity.type) {
        this.docWidget.removeMention(this.currentMention);
      }

      this.currentSelection = null;
      this.currentMention = null;
    }
  };

  EntityInterface.prototype.processSpanSelection = function(tokens) {
    this.deactivate();

    // Are these tokens arelady part of a mention?
    for (var i = 0; i < tokens.length; i++) {
      if (tokens[i].mention !== undefined) {
        return this.processMentionClick(tokens[i].mention);
      }
    }

    // Highlight all of the tokens being selected.
    this.currentSelection = tokens;
    this.currentMention = defs.Mention.fromTokens(tokens);
    this.docWidget.addMention(this.currentMention);
    this.docWidget.selectMention(this.currentMention);
    this.listWidget.activate(this.currentMention);
    this.wikiLinkModal.preload(this.currentMention.gloss);
    this.addEntityWidget.activate();

  };

  // A type has been selected for the current mention which is now going
  // to become a new entity!
  EntityInterface.prototype.processTypeSelected = function(type) {
    this.currentMention.type = type;

    if (type.linking == 'wiki-search') {
      this.wikiLinkModal.show(this.currentMention.gloss);
    } else if (type.linking == 'date-picker') {
      //Find the first related entity
      var i=0;
      for (; i<this.currentMention.tokens.length; i++) {
        if ('suggestedMention' in this.currentMention.tokens[i]) {
          if ('entity' in this.currentMention.tokens[i].suggestedMention) {
            if ('link' in this.currentMention.tokens[i].suggestedMention.entity) {
              this.dateModal.show(this.currentMention.gloss, this.currentMention.tokens[i].suggestedMention.entity.link);
              break;
            }
          }
        }
      }
      if (i == this.currentMention.tokens.length) {
        this.dateModal.show(this.currentMention.gloss);
      }
    } else {
      return this.processLinkingDone("");
    }
  };

  EntityInterface.prototype.processLinkingDone = function(link) {
    var entity = new defs.Entity(this.currentMention);
    entity.link = link;

    this.entities.push(entity);
    this.listWidget.addEntity(entity);
    this.docWidget.updateMention(this.currentMention);

    // TODO: any graphics stuff?

    // Deactivate the widgets and unselect.
    this.deactivate();
  };

  // An existing entity has been chosen for this brave mention!
  EntityInterface.prototype.processEntityClick = function(entity) {
    if (this.currentMention.entity !== undefined && this.currentMention.entity !== null) {
      if (this.currentMention.entity == entity) {
        this.deactivate();
        return; // If the entities are the same, don't do anything.
      }

      if(!this.currentMention.entity.removeMention(this.currentMention)) this.removeEntity(this.currentMention.entity);
    }

    this.currentMention.entity = entity;
    this.currentMention.type = entity.type;
    entity.addMention(this.currentMention);

    // Update the mention
    this.docWidget.updateMention(this.currentMention);

    // Deactivate the widgets and unselect.
    this.deactivate();
  };

  // A mention has been click. Allow the user to either modify the link or
  // remove the mention.
  EntityInterface.prototype.processMentionClick = function(mention) {
    this.deactivate();

    // Don't do anything for an undefined entity.
    if (mention.entity === undefined || mention.entity === null) return; 

    this.docWidget.selectMention(mention);
    this.currentMention = mention; // Make "editMention" 

    // Highlight the current
    this.listWidget.activate(mention);
    this.addEntityWidget.deactivate();
    this.addEntityWidget.hide();
    this.removeSpanWidget.activate();
  };

  EntityInterface.prototype.processRemoveSpan = function() {
    if (!this.currentMention.entity.removeMention(this.currentMention)) {
      this.removeEntity(this.currentMention.entity);
    }
    this.docWidget.removeMention(this.currentMention);

    // Deactivate the widgets and unselect.
    this.deactivate();
  };

  // Highlight all the mentions for this entity.
  EntityInterface.prototype.processEntityMouseEnter = function(entity) {
    var self = this;
    this.listWidget.highlight(entity);
    entity.mentions.forEach(function(mention) {self.docWidget.highlightMention(mention);});
  };

  EntityInterface.prototype.processEntityMouseLeave = function(entity) {
    var self = this;
    this.listWidget.unhighlight(entity);
    entity.mentions.forEach(function(mention) {self.docWidget.unhighlightMention(mention);});
  };

  EntityInterface.prototype.removeEntity = function(entity) {
    var self = this;
    console.info("removing entity", entity);
    var idx = this.entities.indexOf(entity);
    console.assert(idx > -1);

    entity.mentions.forEach(function(mention) {self.docWidget.removeMention(mention);});
    this.listWidget.removeEntity(entity);
    this.entities.splice(idx,1);
  };

  EntityInterface.prototype.reportCostTime = function(cost, time) {
    time = parseInt(time);
    var lowerTime = Math.floor(0.8 * time / 60);
    var upperTime = Math.ceil(1.2 * time / 60);
    $("#reward").text("$" + cost);
    $("#estimated-time").text(lowerTime + " - " + upperTime + " minutes");
  };

  EntityInterface.prototype.setDocDate = function(docdate) {
    this.dateModal.setDocDate(docdate);
  };

  return EntityInterface;
});
