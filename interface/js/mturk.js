function getUrlVars()
{
    var vars = {}, hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars[hash[0]] = hash[1];
    }
    return vars;
}
//Test to see if it is preview mode
function initialize_doc(doc_id){
    //$.getJSON("exhaustive/ENG_NW_001436_20150718_F0010006Q.json", function(data) {
    $.getJSON("exhaustive/"+doc_id+".json", initialize_interface)
    .fail(function() {
        console.log("Could not load data.");
    });
}
mainInterface.doneListeners.push(function(data){
    //var submitUrl = "https://www.mturk.com/mturk/externalSubmit";
    var submitUrl = "https://workersandbox.mturk.com/mturk/externalSubmit";
    //Basic test to prevent development runs from submitting 
    var urlVars = getUrlVars();
    if ('assignmentId' in urlVars){
        urlVars['data'] = data;
        $.post(submitUrl , urlVars );
    }
});
