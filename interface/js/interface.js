//var test_sentence = {tokens: [{word: 'A', lemma: 'a'
/*function getSelectionText() {
    var text = "";
    if (window.getSelection) {
        text = window.getSelection();
    } else if (document.selection && document.selection.type != "Control") {
        text = document.selection;
    }
    return text;
}
document.onmouseup =  document.onselectionchange = function() {
  var sel_val = getSelectionText();
  document.getElementById("sel").value = sel_val;
  console.log(sel_val);
};
$.getJSON("example1.json", function(data){
    console.log(data);
};);*/

function Mention(list_of_words){
    this.span = list_of_words;
}
Mention.prototype.highlight = function(color){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).css("background-color", color);
    }
};
Mention.prototype.text = function(){
    text = ""
    for (i = 0; i<this.span.length;i++){
        text+=$(this.span[i]).text();
    }
    return text;
}
function Entity(canonical_mention, type){
    this.canonical_mention = canonical_mention;
    this.type = type;
    this.mentions = [canonical_mention, ];
    this.id = "e_"+total_entities;
};
Entity.prototype.addMention = function(mention){
    this.mentions.push(mention);
};
Entity.prototype.canonical_text = function(){
    return this.canonical_mention.text();
};

entities = [];
total_entities = 0;
var current_mention = null;
//should actually take mention as input or mention span even (as list of words)
function linkEntity(entity_id){
    var i = 0
    for(; i<entities.length; i++){
        if (entities[i].id == entity_id){
            break;
        }
    }
    //TODO: check if current mention is null?
    entities[i].addMention(current_mention);
    disable_pane();
}
function addEntity(type){
    var new_entity = new Entity(current_mention);
    entities.push(new_entity);
    total_entities +=1;
    var new_entity_dom = $('.entity_template').clone();
    new_entity_dom.removeClass('hidden').removeClass('entity_template');
    new_entity_dom.append(new_entity.canonical_text());
    new_entity_dom.attr('onclick', 'link_entity('+new_entity.id+')');
    new_entity_dom.attr('value', new_entity.id).prop('checked', 'checked');
    new_entity_dom.appendTo($('#entities'));
    new_entity_dom.focus();
    if (total_entities>=0){
        $('.zero_entity').addClass('hidden');
    }
    else{
        $('.zero_entity').removeClass('hidden');
    }
    disable_pane();
}

var types = ["Person", "Organization", "GPE", "Date", "Title"];
var type_icons = ["fa-user", "fa-building-o", "fa-globe", "fa-calendar", "fa-id-card-o"]
function populate_types(){
    for (var i = 0; i< types.length; i++){
        var new_type = $('.type_template').clone();
        new_type.removeClass('hidden').removeClass('type_template');
        new_type.children('a').append(types[i]);
        new_type.children('i').addClass(type_icons[i]);
        new_type.appendTo($('#types'));
    }
}
function type_clicked(type_name){
    var type = $(type_name).text()
//change entity name 
    addEntity(type);
}
populate_types();
function process_selection(token_span){
    enable_pane();
    current_mention = new Mention(token_span);
    current_mention.highlight('grey');
}
function disable_pane(){
    $('.entity-pane *').attr("disabled", "disabled");
}
function enable_pane(){
    $('.entity-pane *').removeAttr("disabled");
}
disable_pane();
//$('.entity-pane').css('pointer-events', 'none');
