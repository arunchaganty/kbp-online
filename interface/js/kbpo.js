/*
 * KBP online.
 * Arun Chaganty <arunchaganty@gmail.com>
 */

/**
 * The document object -- handles the storage and representation of
 * sentences.
 *
 * @elemId - DOM element that the document is rooted at.
 */
var DocWidget = function(elem) {
  console.assert(elem);
  this.elem = $(elem);
};

DocWidget.prototype.load = function(doc) {
  this.doc = doc;
  this.insertIntoDOM(doc);
  this.attachHandlers();
};

DocWidget.prototype.insertIntoDOM = function(doc) {
  // Load every sentence into the DOM.
  for (var i = 0; i < doc.sentences.length; i++) {
    sentence = doc.sentences[i];
    var span = $("<span>", {'class': 'sentence', 'id': 'sentence-' + i});
    span[0].sentence = sentence;

    for (var j = 0; j < sentence.length; j++) {
      var token = sentence[j];
      var tokenSpan = $("<span>", {'class': 'token', 'id': 'token-' + i + '-' + j})
                   .text(token.word);
      if (j > 0 && sentence[j].doc_char_begin > sentence[j-1].doc_char_end) {
        tokenSpan.html("&nbsp;" + tokenSpan.text());
      }
      tokenSpan[0].token = token;
      span.append(tokenSpan);
    }
    this.elem.append(span);
  };
};

DocWidget.prototype.highlightListener = []
DocWidget.prototype.mouseEnterListener = []
DocWidget.prototype.mouseLeaveListener = []
DocWidget.prototype.clickListener = []

/**
 * Attaches handlers to the DOM elements in the document and forwards
 * events to the listeners.
 */
DocWidget.prototype.attachHandlers = function() {
  var self = this;

  // highlightListener (a bit complicated because selection objects must
  // be handled.
  this.elem.on("mouseup.kbpo.docWidget", function(evt) { // Any selection in the document.
    var sel = document.getSelection();
    if (sel.isCollapsed) return; // Collapsed => an empty selection.

    var startNode = sel.anchorNode.parentNode;
    var endNode = sel.focusNode.parentNode;

    // Ensure that the start and end nodes are in the document.
    if (!self.elem[0].contains(startNode) || !self.elem[0].contains(endNode)) {
      // Otherwise, kill the selection.
    } else {
      // Create a selection object of the spans in between the start and
      // end nodes.
      var selectedTokens = [];
      while (startNode != endNode) {
        if ($(startNode).hasClass('token')) {
          selectedTokens.push(startNode);
        }
        startNode = startNode.nextSibling;
      }
      if ($(startNode).hasClass('token')) {
        selectedTokens.push(startNode);
      }
      
      console.log("span-selected:", selectedTokens);
      self.highlightListener.forEach(function (listener) {listener(selectedTokens);});
    }
    // Kill the selection.
    sel.collapseToEnd();
  });

  // mouseEnter
  this.elem.find('span.token').on("mouseenter.kbpo.docWidget", function(evt) { // Any selection in the document.
    console.log("span-enter:", this);
    self.mouseEnterListener.forEach(function (listener) {listener(this);});
  });

  // mouseLeave
  this.elem.find('span.token').on("mouseleave.kbpo.docWidget", function(evt) { // Any selection in the document.
    console.log("span-leave:", this);
    self.mouseLeaveListener.forEach(function (listener) {listener(this);});
  });

  // clickListener
  this.elem.find("span.token").on("click.kbpo.docWidget", function(evt) {
    console.log("span-click:", this);
    self.clickListener.forEach(function (listener) {listener(this);});
  });
};

// TODO: hooks for rendering subtext (for the linked entity), colors,
// underlines, relations.

