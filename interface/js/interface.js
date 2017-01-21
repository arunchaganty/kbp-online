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
    console.log(list_of_words);
    for (i =0; i<list_of_words.length; i++){
        console.log(list_of_words[i].id);
        Mention.token_to_mention_map[list_of_words[i].id] = this;
    }
}
Mention.count = 0;
Mention.prototype.color = function(color){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).css("background-color", color);
    }
};
Mention.prototype.remove = function(color){
    this.color("");
    this.unhighlight();
    for (i =0; i<this.span.length; i++){
        console.log(this.span[i].id);
        delete Mention.token_to_mention_map[this.span[i].id];
    }
    if (this.id in Entity.mention_to_entity_map){
        Entity.mention_to_entity_map[this.id].removeMention(this);
    }
};
Mention.prototype.highlight = function(){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).addClass("highlight");
    }
}
Mention.prototype.unhighlight = function(){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).removeClass("highlight");
    }
}
Mention.prototype.select = function(){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).addClass("select");
    }
}
Mention.prototype.deselect = function(){
    for (i = 0; i<this.span.length;i++){
        $(this.span[i]).removeClass("select");
    }
}
Mention.token_to_mention_map = {}
Mention.prototype.text = function(){
    text = ""
    for (i = 0; i<this.span.length;i++){
        text+=$(this.span[i]).text();
    }
    return text;
}
Mention.prototype.levenshtein = function(string){
    return window.Levenshtein.get(this.text(), string);
}
function Entity(canonical_mention, type){
    this.canonical_mention = canonical_mention;
    this.type = type;
    this.mentions = [canonical_mention, ];
    this.id = "e_"+Entity.count;
    Entity.count +=1;
    Entity.mention_to_entity_map[canonical_mention.id] = this;
    entities[this.id]=this;
    
    //add a dom element
    this.entity_dom = $('.entity_template').clone();
    this.entity_dom.removeClass('hidden').removeClass('entity_template').addClass('selected-entity');
    this.entity_dom.children('i').addClass(this.type.icon);
    this.entity_dom.append(this.canonical_text());
    this.entity_dom.attr('onclick', 'linkEntity(\''+this.id+'\')');
    this.entity_dom.attr('id', this.id).prop('checked', 'checked');
    this.entity_dom.attr('entity-type', this.type.type);
    var entities_in_dom = $(".entity").not(".zero_entity").not(".entity_template");
    var total_len = entities_in_dom.length;
    console.log(total_len);
    if (total_len == 0){
        this.entity_dom.appendTo($('#entities'));
    }
    var _this = this;
    entities_in_dom.each(function(i){
        console.log(i);
        console.log($(this).attr("entity-type"));
        console.log(_this.type.type);
        console.log(_this.canonical_text());
        console.log($(this).text());
        console.log($(this).attr("entity-type")>=_this.type);
        console.log($(this).text()>=_this.canonical_text());
        if($(this).attr("entity-type")>=_this.type.type && $(this).text()>=_this.canonical_text()){
            _this.entity_dom.insertBefore(this);
            return false;
        }
        else if (i ==  total_len- 1) {
            _this.entity_dom.insertAfter(this);
            return false;
        }
    });
    this.canonical_mention.color(type.color);
    update_zero_entity();
};
Entity.count = 0;
Entity.prototype.addMention = function(mention){
    this.mentions.push(mention);
    Entity.mention_to_entity_map[mention.id] = this;
    mention.color(this.type.color);
};
Entity.prototype.removeMention = function(mention){
    var index= this.mentions.indexOf(mention);
    if (index > -1) {
        this.mentions.splice(index, 1);
    }
    delete Entity.mention_to_entity_map[mention.id];
    if(this.mentions.length < 1){
        this.remove();
    }
};
Entity.prototype.canonical_text = function(){
    return this.canonical_mention.text();
};
Entity.prototype.remove = function(){
    for (var i = 0; i<this.mentions.length; i++){
        delete Entity.mention_to_entity_map[i.id]
    }
    this.entity_dom.remove();
    update_zero_entity();
}
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
Entity.prototype.levenshtein = function(new_mention_string){
    var best_match = null
    var best_score = 1000;
    for (var i = 0; i<this.mentions.length; i++){
        var score = this.mentions[i].levenshtein(new_mention_string);
        if (best_score > score){
            best_score = score;
            best_match = this.mentions[i]
        }
    }
    return best_score;
}
Entity.mention_to_entity_map = {}

function update_zero_entity(){
    if (Entity.count>=0){
        $('.zero_entity').addClass('hidden');
    }
    else{
        $('.zero_entity').removeClass('hidden');
    }
}

entities = {}
var current_mention = null;
//should actually take mention as input or mention span even (as list of words)
function linkEntity(entity_id){
    console.log('ah');
    var i = 0
    console.log(entity_id);
    var entity = entities[entity_id];
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

function process_selection(token_span){
    disable_pane();
    for(var i=0; i<token_span.length; i++){
        if(token_span[i].id in Mention.token_to_mention_map){
            current_mention = Mention.token_to_mention_map[token_span[i].id];
            process_click(token_span[i]);
            return;
        }
    }
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

function disable_pane(){
    console.log('oh!');
    $('.entity-pane *').attr("disabled", "disabled");
    $('.selected-entity').removeClass("selected-entity");
    $('#add_entity_widget').removeClass('hidden');
    $('#cancel_mention_widget').addClass('hidden');
    if (current_mention !=null){
        current_mention.deselect();
        if (current_mention.id in Entity.mention_to_entity_map){
            var current_entity = Entity.mention_to_entity_map[current_mention.id];
            current_entity.unhighlight();
        }else{
            current_mention.remove();
        }
    }
    $('.suggested-entity').removeClass('suggested-entity');
    current_mention = null;
    //$('.entity-pane').unbind("click", disable_pane);
}
/*function sort_entities(){
    var entity_list = $('#entities');
    var entities = entity_list.children('button');
    entities.sort(function(a, b){
        
    }
}*/

function enable_pane(){
    $('.entity-pane *').removeAttr("disabled");
}
//$('.entity-pane').css('pointer-events', 'none');

function entity_type(type, icon, color){
    this.type = type;
    this.icon = icon;
    this.color = color;
}
var entity_types = {};
var colors = ['#7fc97f','#beaed4','#fdc086','#ffff99','#386cb0'];
entity_types['Person'] = new entity_type("Person", "fa-user", colors[0]);
entity_types['Organization'] = new entity_type("Organization", "fa-building-o", colors[1]);
entity_types['City/State/Country'] = new entity_type("City/State/Country", "fa-globe", colors[2]);
entity_types['Date'] = new entity_type("Date", "fa-calendar", colors[3]);
entity_types['Title'] = new entity_type("Title", "fa-id-card-o", colors[4]);
function populate_types(){
    for (type in entity_types){
        var new_type = $('.type_template').clone();
        new_type.removeClass('hidden').removeClass('type_template');
        new_type.append(entity_types[type].type);
        new_type.attr('entity_type', entity_types[type].type);
        new_type.find('span').addClass(entity_types[type].icon);
        new_type.appendTo($('#types'));
    }
}
populate_types();
disable_pane();
//$('.document').bind("click", disable_pane);
