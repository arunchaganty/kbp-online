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
function Entity(canonical_mention, type){
    this.canonical_mention = canonical_mention;
    this.type = type;
    this.mentions = [canonical_mention, ];
};
Entity.prototype.addMention = function(mention){
    this.mentions.push(mention);
};
entities = [];
//should actually take mention as input or mention span even (as list of words)
function type_clicked(type_name){
    var type = $(type_name).text()
//change entity name 
    addEntity('aha', type);
}
function addEntity(entity_name, type){
    
    //new_entity = new Entity(canonical_mention);
    var new_entity = $('.entity_template').clone();
    new_entity.removeClass('hidden').removeClass('entity_template');
    new_entity.append(entity_name);
    new_entity.appendTo($('#entities>div'));
}

var types = ["Person", "Organization", "GPE", "Date", "Title"];
function populate_types(){
    for (var i = 0; i< types.length; i++){
        var new_type = $('.type_template').clone();
        new_type.removeClass('hidden').removeClass('type_template');
        new_type.children('a').append(types[i]);
        new_type.appendTo($('#types'));
    }
}
populate_types();

