
var AddEntityWidget = function(elem) {
  this.elem = elem;

  var self = this;
  for (var i = 0; i < Object.keys(TYPES).length; i++) {
    var type = TYPES[Object.keys(TYPES)[i]];
    var elem = this.elem.find("#type-template").clone();
    elem
      .removeClass("hidden")
      .attr("id", "type-" + type.name)
      .attr("disabled", "disabled")
      ;
    elem.html(elem.html()
      .replace("{icon}", type.icon)
      .replace("{name}", type.gloss)
      );
    elem[0]._type = type;
    elem.on("click.kbpo.addEntityWidget", function (evt) {
      var type = this._type;
      self.clickListeners.forEach(function(cb) {cb(type)})
    });
    this.elem.find("#types").append(elem);
  }
  this.deactivate();
}
AddEntityWidget.prototype.clickListeners = [];
AddEntityWidget.prototype.activate = function() {
  this.elem
    .find(".type")
    .not("#type-template")
    .removeAttr("disabled");
  this.elem.removeClass("hidden")
}
AddEntityWidget.prototype.deactivate = function() {
  this.elem
    .find(".type")
    .not("#type-template")
    .attr("disabled", "disabled");
  this.elem.removeClass("hidden")
}
AddEntityWidget.prototype.hide = function() {
  this.elem.addClass("hidden");
}

var RemoveSpanWidget = function(elem) {
  var self = this;
  this.elem = elem;
  this.elem.find("#remove-span").on("click.kbpo.RemoveSpanWidget", function(evt) {
    self.clickListeners.forEach(function (cb) {cb(true);});
  });
}
RemoveSpanWidget.prototype.clickListeners = [];
RemoveSpanWidget.prototype.activate = function() {
  this.elem.removeClass("hidden");
}
RemoveSpanWidget.prototype.deactivate = function() {
  this.elem.addClass("hidden");
}

var EntityListWidget = function(elem) {
  this.elem = elem;
}
EntityListWidget.prototype.clickListeners = [];
EntityListWidget.prototype.mouseEnterListeners = [];
EntityListWidget.prototype.mouseLeaveListeners = [];

// A span in the text has been selected; activate this UI.
EntityListWidget.prototype.activate = function(mention) {
  this.elem.find("*").removeAttr("disabled");
  // Find all entities that are very similar to this one and suggest them.

  console.log("act", mention.entity);
  if (mention.entity) {
    $(mention.entity.elem).addClass('list-group-item-success');
  } else {
    var entities = this.entities();
    for(var i = 0; i < entities.length; i++) {
      if(mention.tokens[0].token.pos_tag != 'PRP'){
          if (entities[i].entity.levenshtein(mention.gloss.toLowerCase()) <= 2) {
            $(entities[i]).addClass('list-group-item-warning');
            entities[i].scrollIntoView();
          }
      }
    }
  }
}

EntityListWidget.prototype.deactivate = function() {
  this.elem.find("*").attr("disabled", "disabled");

  this.currentEntity = null;
  this.elem.find('.list-group-item-success').removeClass("list-group-item-success");
  this.elem.find('.list-group-item-warning').removeClass('list-group-item-warning');
}

// Get current entities
EntityListWidget.prototype.entities = function() {
  return this.elem.find(".entity").not("#entity-empty").not("#entity-template");
}

EntityListWidget.prototype.addEntity = function(entity) {
  var self = this;
  var elem = $('#entity-template')
    .clone()
    .removeClass('hidden')
    .attr("id", entity.id)
    ;
  console.log(entity);
  elem.html(elem.html()
      .replace("{icon}", entity.type.icon)
      .replace("{gloss}", entity.gloss)
      .replace("{id}", entity.idx)
      );
  elem.on("click.kbpo.entityListWidget", function(evt) {
    self.clickListeners.forEach(function(cb) {cb(entity)})
  });
  elem.on("mouseenter.kbpo.entityListWidget", function(evt) {
    self.mouseEnterListeners.forEach(function(cb) {cb(entity)})
  });
  elem.on("mouseleave.kbpo.entityListWidget", function(evt) {
    self.mouseLeaveListeners.forEach(function(cb) {cb(entity)})
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
    console.log("type", entities[i].entity.type.name, entity.type.name, entities[i].entity.type.idx <= entity.type.idx);
    console.log("gloss", entities[i].entity.gloss, entity.gloss, entities[i].entity.gloss <= entity.gloss);
    console.log("id", entities[i].entity.idx, entity.idx, entities[i].entity.idx < entity.idx);

    if ((entity.type.idx < entities[i].entity.type.idx) 
        || (entity.type.idx == entities[i].entity.type.idx 
            && entity.gloss.toLowerCase() <= entities[i].entity.gloss.toLowerCase())) {
      elem.insertBefore(entities[i]);
      break;
    }
  }
  if (i == entities.length) {
    this.elem.append(elem);
  }
}
EntityListWidget.prototype.removeEntity = function(entity) {
  entity.elem.remove();
  if (this.entities().length == 0) {
    this.elem.find("#entity-empty").removeClass("hidden");
  }
}
EntityListWidget.prototype.highlight = function(entity) {
  $(entity.elem).addClass("highlight");
}
EntityListWidget.prototype.unhighlight = function(entity) {
  $(entity.elem).removeClass("highlight");
}

var EntityInterface = function(docWidget, listWidget, addEntityWidget, removeSpanWidget, linkWidget) {
  var self = this;
  this.docWidget = docWidget;
  this.listWidget = listWidget;
  this.addEntityWidget = addEntityWidget;
  this.removeSpanWidget = removeSpanWidget;
  this.linkWidget = linkWidget;
  this.dateWidget = dateWidget;

  this.entities = [];
  this.currentMention = null;

  // Attach a listener for entity selections.
  this.docWidget.highlightListeners.push(function(selection) {self.processSpanSelection(selection)});
  this.docWidget.clickListeners.push(function(mention) {self.processMentionClick(mention)});
  this.addEntityWidget.clickListeners.push(function(type) {self.processTypeSelected(type)});
  this.removeSpanWidget.clickListeners.push(function() {self.processRemoveSpan()});
  this.listWidget.clickListeners.push(function(entity) {self.processEntityClick(entity)});
  this.listWidget.mouseEnterListeners.push(function(entity) {self.processEntityMouseEnter(entity)});
  this.listWidget.mouseLeaveListeners.push(function(entity) {self.processEntityMouseLeave(entity)});
  this.linkWidget.doneListeners.push(function(link) {self.processLinkingDone(link)});
  this.dateWidget.doneListeners.push(function(link) {self.processLinkingDone(link)});

  $("#done")[0].disabled = true;
  $("#done").on("click.kbpo.interface", function (evt) {
    var entities = [];
    for (var i = 0; i < self.entities.length; i++) {
      var entity = self.entities[i];
      for (var j = 0; j < entity.mentions.length; j++) {
        var mention = entity.mentions[j];
        entities.push(mention.toJSON());
      }
    }
    var data = JSON.stringify(entities)
    $("#entities-output").attr('value', data);
    self.doneListeners.forEach(function(cb) {cb(data);});
    return true;
  });

  // TODO: doc mouseEnter, mouseLeave?
  // doc.mouseEnterListeners.push(process_mouse_enter);
  // doc.mouseLeaveListeners.push(process_mouse_leave);
}
entities = {}
EntityInterface.prototype.doneListeners = [];

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
}

EntityInterface.prototype.processSpanSelection = function(tokens) {
  console.log("span");
  this.deactivate();

  // Are these tokens arelady part of a mention?
  for (var i = 0; i < tokens.length; i++) {
    if (tokens[i].mention !== undefined) {
      return this.processMentionClick(tokens[i].mention);
    }
  }

  // Highlight all of the tokens being selected.
  this.currentSelection = tokens;
  this.currentMention = Mention.fromTokens(tokens);
  this.docWidget.addMention(this.currentMention);
  this.docWidget.selectMention(this.currentMention);
  this.listWidget.activate(this.currentMention);
  this.linkWidget.preload(this.currentMention.gloss);
  this.addEntityWidget.activate();

}

// A type has been selected for the current mention which is now going
// to become a new entity!
EntityInterface.prototype.processTypeSelected = function(type) {
  this.currentMention.type = type;

  if (type.linking == 'wiki-search') {
    linkWidget.show(this.currentMention.gloss);
  } else if (type.linking == 'date-picker') {
      //Find the first related entity
      var i=0;
      for(; i<this.currentMention.tokens.length; i++){
           if ('suggestedMention' in this.currentMention.tokens[i]){
               if('entity' in this.currentMention.tokens[i].suggestedMention){
                   if('link' in this.currentMention.tokens[i].suggestedMention.entity){
                       dateWidget.show(this.currentMention.gloss, this.currentMention.tokens[i].suggestedMention.entity.link);
                       break;
                   }
               }
           }
      }
      if(i == this.currentMention.tokens.length){
          console.log('link not found');
          dateWidget.show(this.currentMention.gloss);
      }
  } else {
    return this.processLinkingDone("");
  }
}

EntityInterface.prototype.processLinkingDone = function(link) {
  var entity = new Entity(this.currentMention);
  entity.link = link;

  this.entities.push(entity);
  this.listWidget.addEntity(entity);
  this.docWidget.updateMention(this.currentMention);

  // TODO: any graphics stuff?

  // Deactivate the widgets and unselect.
  this.deactivate();
}


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
  docWidget.updateMention(this.currentMention);

  // Deactivate the widgets and unselect.
  this.deactivate();
}

// A mention has been click. Allow the user to either modify the link or
// remove the mention.
EntityInterface.prototype.processMentionClick = function(mention) {
  console.log("click", mention);
  this.deactivate();

  // Don't do anything for an undefined entity.
  if (mention.entity === undefined || mention.entity === null) return; 
  console.log("click", mention);

  this.docWidget.selectMention(mention);
  this.currentMention = mention; // Make "editMention" 

  // Highlight the current
  this.listWidget.activate(mention);
  this.addEntityWidget.deactivate();
  this.addEntityWidget.hide();
  this.removeSpanWidget.activate();
}

EntityInterface.prototype.processRemoveSpan = function() {
  if (!this.currentMention.entity.removeMention(this.currentMention)) {
    this.removeEntity(this.currentMention.entity);
  };
  this.docWidget.removeMention(this.currentMention);

  // Deactivate the widgets and unselect.
  this.deactivate();
}

// Highlight all the mentions for this entity.
EntityInterface.prototype.processEntityMouseEnter = function(entity) {
  this.listWidget.highlight(entity);
  entity.mentions.forEach(function(mention) {this.docWidget.highlightMention(mention)});
}

EntityInterface.prototype.processEntityMouseLeave = function(entity) {
  this.listWidget.unhighlight(entity);
  entity.mentions.forEach(function(mention) {this.docWidget.unhighlightMention(mention)});
}

EntityInterface.prototype.removeEntity = function(entity) {
    console.log("removing entity", entity);
  var idx = this.entities.indexOf(entity);
  console.assert(idx > -1);

  entity.mentions.forEach(function(mention) {this.docWidget.removeMention(mention)});
  this.listWidget.removeEntity(entity);
  this.entities.splice(idx,1);
}


//LinkWidget to link with wikipedia entries
function LinkWidget(elem){
  var self = this;

  this.elem = elem;

  this.resultLimit = 5;
  this.thumbSize = 50;

  $('#submit-wiki-search').click(function(){self.populate(this.form.search_input.value);});
  $('#no-wiki-link').click(function(){
    self.doneListeners.forEach(function(cb) {cb("");})
    self.hide();
  });
}
LinkWidget.prototype.doneListeners = [];

LinkWidget.prototype.fetchResults = function(term){
  return $.ajax({
    url: 'https://en.wikipedia.org/w/api.php',
    data: { action: 'opensearch', limit: this.resultLimit, search: term, format: 'json' , redirects:'resolve', namespace:0},
    dataType: 'jsonp',
  });
}
LinkWidget.prototype.fetchThumbs = function(searchResults){
  return $.ajax({
    url: 'https://en.wikipedia.org/w/api.php',
    data: { action: 'query', titles: searchResults[1].join('|'), format: 'json',prop: 'pageimages' , pithumbsize: this.thumbSize, pilimit:this.resultLimit },
    dataType: 'jsonp',

  });
}

LinkWidget.prototype.preload = function(mentionText){
  this.mentionText = mentionText;
  this.populate(mentionText);
  $('#wiki-search-input').val(mentionText);
}
LinkWidget.prototype.show = function(mentionText){
  if(this.mentionText != mentionText){
      this.mentionText = mentionText;
      this.populate(mentionText);
      $('#wiki-search-input').val(mentionText);
  }
  $('#wiki-linking-modal').modal('show');
}

LinkWidget.prototype.hide = function(){
  $('#wiki-linking-modal').modal('hide');
  $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
}

LinkWidget.prototype.populate = function(mentionText){
  if (mentionText === undefined) {
    mentionText = this.mentionText;
  }

  var self = this;
  this.fetchResults(mentionText).done(function(searchResults) {
    console.log('callback working');
    if (searchResults[1].length == 0){
        //No results were found, simply clear and move on
        $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
    }
    self.fetchThumbs(searchResults).done(function(images){
      console.log(images);
      var pages = images['query']['pages'];
      var thumbs = [];
      for (page in pages) {
        if ('thumbnail' in pages[page]) {
          thumbs.push(pages[page]['thumbnail']['source']);
        } else {
          thumbs.push(null);
        }
      }
      searchResults.push(thumbs);
      var titles = searchResults[1];
      var texts = searchResults[2];
      var urls = searchResults[3];
      var thumbs = searchResults[4];


      // Clear existing entries.
      $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
      for(var i=titles.length-1; i>=0; i--) {
        var resultDom = $('.wiki-entry-template').clone();
        resultDom.removeClass('hidden').removeClass('wiki-entry-template');

        resultDom.children('button').click(function() {
          var url = $(this).siblings('.list-group-item-heading').children('a').attr('href');
          var name = url.substr(url.lastIndexOf('/') + 1);
          self.doneListeners.forEach(function(cb) {cb(name);});
          self.hide();
        });

        resultDom.children('.list-group-item-heading').prepend('<a href=\"'+urls[i]+'\" target=\'_blank\'>'+titles[i]+'</a>');
        if (thumbs[i] != null) {
          resultDom.prepend("<img src=\'"+thumbs[i]+"\' style='float:left; padding-right:3px;' class='img-responsive' ></img>");
        }
        resultDom.children('.list-group-item-text').append(texts[i]);
        resultDom.prependTo($('#wiki-search-results'));
      }   
    });
  });
}

$(window).on('beforeunload', function () {
  $("#document").scrollTop(0);
});

$(window).on('load', function () {
  $("#document").scrollTop(0);
    $('#document').bind('scroll', function(e){
      var elem = $(e.currentTarget);
      if (elem[0].scrollHeight - elem.scrollTop() == elem.outerHeight()) {
        $("#done")[0].disabled = false;
      }
    });
});

