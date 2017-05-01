/*!
 * KBPOnline: Main entry point
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

requirejs.config({
    baseUrl: 'static/js',
});


requirejs(["jquery/dist/jquery", "bootstrap/dist/bootstrap", "widgets/DocWidget.js"], function($, bootstrap, DocWidget) {
  // TODO: Based on the page, define the appropriate widgets.
  var docWidget = new DocWidget($("#document"));
  // Right now, docId is specified on the page.
  var docId = $("#doc-id").value();
  $.getJSON("/api/document/" + docId, function(doc) {
    console.log("loaded data.");
    docWidget.loadDocument(doc);
    if (doc["suggested-mentions"]) {
      docWidget.setSuggestions(doc["suggested-mentions"]);
    }
  });
});
