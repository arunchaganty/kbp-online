
// TODO: Move this code into an interface.
Entity.prototype.highlight = function(){
    for (var i = 0; i<this.mentions.length; i++){
        this.mentions[i].highlight();
    }
    this.entity_dom.addClass('highlight');
}
Entity.prototype.unhighlight = function(){
    for (var i = 0; i<this.mentions.length; i++){
        this.mentions[i].unhighlight();
    }
    this.entity_dom.removeClass('highlight');
}

// TODO:Package functions below into a EntityWidget and an
// EntityInterface.
class AddEntityWidget = function(elem) {
  this.elem = elem;

  var self = this;
  for (type in TYPES) {
    var type = TYPES[type];
    var elem = this.elem.find("#type-template")
      .clone()
      .removeClass("hidden")
      .attr(id, "type-" + type.name);
    elem.html(elem.html()
      .replace("{icon}", type.icon)
      .replace("{name}", type.name)
      ;
    elem.on("click.kbpo.addEntityWidget", function (evt) {
      self.clickListeners.forEach(function(cb) {cb(type)})
    });
    this.elem.append(elem);
  }
}
AddEntityWidget.prototype.clickListeners = [];

class RemoveSpanWidget = function(elem) {
  var self = this;
  this.elem = elem;
  this.elem.find("#remove-span").on("click.kbpo.RemoveSpanWidget", function(evt) {
    self.clickListeners.forEach(function (cb) {cb(true);});
  });
}
RemoveSpanWidget.prototype.clickListeners = [];

class EntityListWidget = function(elem) {
  this.elem = elem;
}
EntityListWidget.prototype.entitySelectedListeners = [];
EntityListWidget.prototype.entityMouseEnterListeners = [];
EntityListWidget.prototype.entityMouseLeaveListeners = [];

// A span in the text has been selected; activate this UI.
EntityListWidget.prototype.activate = function(mention) {
  this.elem.find("*").removeAttr("disabled");
}

EntityListWidget.prototype.deactivate = function() {
  this.elem.find("*").attr("disabled", "disabled");

  // TODO: why is this all here?
  this.currentEntity = null;
  $('.selected-entity').removeClass("selected-entity");
  $('#add-entity-widget').removeClass('hidden'); // TODO: ???
  $('#cancel-mention-widget').addClass('hidden');
  $('.suggested-entity').removeClass('suggested-entity');
}

EntityListWidget.prototype.addEntity = function(entity) {
  var elem = $('.entity_template')
    .clone()
    .removeClass('hidden')
    .addClass('selected-entity')
    .attr("id", entity.id)
    ;
  elem.html(elem.html()
      .replace("{icon}", entity.type.icon)
      .replace("{gloss}", entity.gloss));
  elem.on("click.kbpo.entityListWidget", function(evt) {
    self.clickListeners.forEach(function(cb) {cb(entity)})
  });
  elem.prop("checked", "checked");

  elem.entity = entity;
  entity.elem = elem;

  // Insert into the list in a sorted order.
  // Remove the 'empty box';
  $("#entity-empty").addClass("hidden");
  var entities = $(".entity").not("#entity-empty").not("#entity-template");

  // Sorted based on the tuple (type, name)
  for (var i = 0; i < entities.length; i++) {
    if (entities[i].entity.type.name > entity.type.name
        && entities[i].entity.gloss > entity.gloss) {
      entities[i].insertAfter(elem);
      break;
    }
  }
  if (i == entities.length) {
    this.elem.append(elem);
  }
}

EntityListWidget.prototype.removeEntity = function(entity) {
  entity.elem.remove();
  if ($(".entity").not("#entity-empty").not("#entity-template").length == 0) {
    this.elem.find("#entity-empty").removeClass("hidden");
  }
}

class EntityInterface = function(docWidget, listWidget, addEntityWidget, removeSpanWidget) {
  var self = this;
  this.docWidget = docWidget;
  this.listWidget = listWidget;

  this.entities = [];
  this.currentMention = null;

  // Attach a listener for entity selections.
  this.docWidget.highlightListener.push(function(selection) {self.processSpanSelection(selection)});
  this.docWidget.clickListener.push(function(mention) {self.processMentionClick(mention)});
  this.addEntityWidget.clickListener.push(function(type) {self.processTypeSelected(type)});
  this.removeSpanWidget.clickListener.push(function(type) {self.processRemoveSpan(type)});
  this.listWidget.clickListener.push(function(entity) {self.processEntityClicked(entity)});
  this.listWidget.mouseEnterListener.push(function(entity) {self.processEntityMouseEnter(entity)});
  this.listWidget.mouseLeaveListener.push(function(entity) {self.processEntityMouseLeave(entity)});

  // TODO: doc mouseEnter, mouseLeave?
  // doc.mouseEnterListener.push(process_mouse_enter);
  // doc.mouseLeaveListener.push(process_mouse_leave);
}
entities = {}

EntityInterface.prototype.deactivate = function() {
  this.listWidget.deactivate();
  this.addEntityWidget.deactivate();
  this.removeSpanWidget.deactivate();
}

EntityInterface.prototype.processSpanSelection = function(tokens) {
  this.deactivate();
  // Remove previous selection.
  if (this.currentSelection) {
    // TODO: remove any annotation here.
    this.currentSelection = null;
  }

  // Are these tokens arelady part of a mention?
  for (var i = 0; i < tokens.length; i++) {
    if (tokens[i].mention !== undefined) {
      return processMentionClick(tokens[i].mention);
    }
  }

  // Highlight all of the tokens being selected.
  this.currentSelection = tokens;
  this.currentMention = new Mention(tokens);

  current_entity = null;
  current_mention = new Mention(token_span);
  current_mention.select();
  current_mention.color('grey');
  var cur_text = current_mention.text()
    for(entity_id in entities){
      if (entities[entity_id].levenshtein(cur_text)<=3){
        entities[entity_id].entity_dom.addClass('suggested-entity');
      }
    }
  enable_pane();
}

// TODO: at the end of a mention being selected.
{
  if (this.currentMention != null) {
    current_mention.deselect();
    if (current_mention.id in Entity.mention_to_entity_map){
      var current_entity = Entity.mention_to_entity_map[current_mention.id];
      current_entity.unhighlight();
    }else{
      current_mention.remove();
    }
  }
  this.currentMention = null;
}



// link the entity to the currently highlighted mention.
//should actually take mention as input or mention span even (as list of words)
function linkEntity(entity_id){
    var i = 0
    console.log(entity_id);
    var entity = entities[entity_id];
    if (current_entity != null){
        current_entity.removeMention(current_mention);
    }
    entity.addMention(current_mention);
    current_mention.highlight(entity.type.color);
    disable_pane();
}
function type_clicked(type_name){
    var type = $(type_name).attr('entity_type');
    type = entity_types[type];
    new Entity(current_mention, type);
    disable_pane(); 
}


function process_click(token){
    disable_pane();
    if(token.id in Mention.token_to_mention_map){
        current_mention = Mention.token_to_mention_map[token.id];
        current_entity = Entity.mention_to_entity_map[current_mention.id];
        current_entity.highlight();
        current_entity.entity_dom.addClass('selected-entity');
        $('#add_entity_widget').addClass('hidden');
        $('#cancel_mention_widget').removeClass('hidden');
        enable_pane();
    }
    else{
    }
}
var highlighted_entity = null;
function process_mouse_enter(token){
    if(current_mention == null && token.id in Mention.token_to_mention_map){
        var hovered_mention = Mention.token_to_mention_map[token.id];
        highlighted_entity = Entity.mention_to_entity_map[current_mention.id];
        highlighted_entity.highlight();
    }
}
function process_mouse_leave(token){
    if (highlighted_entity != null){
        highlighted_entity.unhighlight();
    }
    highlighted_entity = null;
}
function remove_mention(){
    if (current_mention != null){
        current_mention.remove();
    }
    disable_pane();
}

// CHAGANTY TODO
// - Refactor functions into a widget and an interface.
// - Make class to docWidget.addMention and docWidget.removeMention.
