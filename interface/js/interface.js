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
    this.id = "m_"+Mention.count;
    Mention.count+=1;
    /*for (i =0; i<list_of_words.len; i++){
        Mention.token_to_mention_map[list_of_words[i].id]
    }*/
}
Mention.count = 0;
Mention.prototype.highlight = function(color){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).css("background-color", color);
    }
};
Mention.token_to_mention_map = {}
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
    this.id = "e_"+Entity.count;
    Entity.count +=1;
};
Entity.count = 0;
Entity.prototype.addMention = function(mention){
    this.mentions.push(mention);
};
Entity.prototype.canonical_text = function(){
    return this.canonical_mention.text();
};
Entity.mention_to_entity_map = {}

entities = {}
var current_mention = null;
//should actually take mention as input or mention span even (as list of words)
function linkEntity(entity_id){
    console.log('ah');
    var i = 0
    console.log(entity_id);
    var entity = entities[entity_id];
    //TODO: check if current mention is null?
    entity.addMention(current_mention);
    current_mention.highlight(entity.type.color);
    disable_pane();
}
function addEntity(type){
    type = entity_types[type];
    
    var new_entity = new Entity(current_mention, type);
    entities[new_entity.id]=new_entity;
    var new_entity_dom = $('.entity_template').clone();
    new_entity_dom.removeClass('hidden').removeClass('entity_template');
    new_entity_dom.children('i').addClass(new_entity.type.icon);
    new_entity_dom.append(new_entity.canonical_text());
    new_entity_dom.attr('onclick', 'linkEntity(\''+new_entity.id+'\')');
    new_entity_dom.attr('value', new_entity.id).prop('checked', 'checked');
    new_entity_dom.appendTo($('#entities'));
    new_entity_dom.focus();
    current_mention.highlight(type.color);
    if (Entity.count>=0){
        $('.zero_entity').addClass('hidden');
    }
    else{
        $('.zero_entity').removeClass('hidden');
    }
    disable_pane();
}

function entity_type(type, icon, color){
    this.type = type;
    this.icon = icon;
    this.color = color;
}
var entity_types = {};
var colors = ['#7fc97f','#beaed4','#fdc086','#ffff99','#386cb0'];
entity_types['Person'] = new entity_type("Person", "fa-user", colors[0]);
entity_types['Organization'] = new entity_type("Organization", "fa-building-o", colors[1]);
entity_types['GPE'] = new entity_type("GPE", "fa-globe", colors[2]);
entity_types['Date'] = new entity_type("Date", "fa-calendar", colors[3]);
entity_types['Title'] = new entity_type("Title", "fa-id-card-o", colors[4]);
function populate_types(){
    for (type in entity_types){
        var new_type = $('.type_template').clone();
        new_type.removeClass('hidden').removeClass('type_template');
        new_type.children('a').append(entity_types[type].type);
        new_type.attr('entity_type', entity_types[type].type);
        new_type.find('span').addClass(entity_types[type].icon);
        new_type.appendTo($('#types'));
    }
}
function type_clicked(type_name){
    var type = $(type_name).parent().attr('entity_type');
//change entity name 
    addEntity(type);
}
populate_types();
function process_selection(token_span){
    enable_pane();
    current_mention = new Mention(token_span);
    current_mention.highlight('grey');
}
//function process_click(
function disable_pane(){
    $('.entity-pane *').attr("disabled", "disabled");
}
function enable_pane(){
    $('.entity-pane *').removeAttr("disabled");
}
disable_pane();
//$('.entity-pane').css('pointer-events', 'none');
