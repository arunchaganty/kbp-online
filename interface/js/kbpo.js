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
      tokenSpan[0].token = token;

      if (j > 0 && sentence[j].doc_char_begin > sentence[j-1].doc_char_end) {
        tokenSpan.html('&nbsp;' + tokenSpan.text());
      }
      span.append(tokenSpan);
    }
    this.elem.append(span);
  };
};

DocWidget.prototype.highlightListener = []
DocWidget.prototype.mouseEnterListener = []
DocWidget.prototype.mouseLeaveListener = []
DocWidget.prototype.clickListener = []

DocWidget.prototype.isSentence = function(node) {
  return node.classList.contains("sentence");
}
DocWidget.prototype.isToken = function(node) {
  return node.classList.contains("token");
}

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
    //if (sel.isCollapsed) return; // Collapsed => an empty selection.
    if (sel.isCollapsed) {
      // This is a click event.
      // Handle the case that the node is an '&nbsp;' text.
      var startNode;
      if (self.isToken(sel.anchorNode.parentNode)) {
        startNode = sel.anchorNode.parentNode;
      } else if (self.isSentence(sel.anchorNode.parentNode)) {
        startNode = sel.anchorNode.nextSibling;
      } else {
        console.log("[Error] selected anchor node is not part of a sentence or a token");
        sel.collapseToEnd();
        return;
      }
      self.clickListener.forEach(function (listener) {listener(startNode);});
      evt.stopPropagation();
    
      return; // Collapsed => an empty selection. 
    }

    // The selected elements are not even in the #document.
    if (!self.elem[0].contains(sel.anchorNode) || !self.elem[0].contains(sel.focusNode)) {
      sel.collapseToEnd();
      return;
    }

    // Handle the case that the node is an '&nbsp;' text.
    var startNode;
    if (self.isToken(sel.anchorNode.parentNode)) {
      startNode = sel.anchorNode.parentNode;
    } else if (self.isSentence(sel.anchorNode.parentNode)) {
      startNode = sel.anchorNode.nextSibling;
    } else {
      console.log("[Error] selected anchor node is not part of a sentence or a token");
      sel.collapseToEnd();
      return;
    }

    var endNode;
    if (self.isToken(sel.focusNode.parentNode)) {
      endNode = sel.focusNode.parentNode;
    } else if (self.isSentence(sel.focusNode.parentNode)) {
      endNode = sel.focusNode.previousSibling;
    } else {
      console.log("[Error] selected focus node is not part of a sentence or a token");
      sel.collapseToEnd();
      return;
    }

    // Make sure both startNode and endNode are part of the same sentence.
    if (startNode.parentNode != endNode.parentNode) {
      console.log("[Error] selected tokens cross sentence boundaries");
      sel.collapseToEnd();
      return;
    }

    // Make sure startNode appears before endNode.
    if ($(startNode).nextAll().filter(endNode).length === 0) {
      var tmpNode = endNode;
      endNode = startNode;
      startNode = tmpNode;
    } 
    console.assert($(startNode).nextAll(endNode).length !== 0, "[Warning] start node does not preceed end node", startNode, endNode);

    // Create a selection object of the spans in between the start and
    // end nodes.
    var selectedTokens = [];
    while (startNode != endNode) {
      console.assert(startNode != null);
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
  /*this.elem.find("span.token").on("click.kbpo.docWidget", function(evt) {
    console.log("span-click:", this);
    self.clickListener.forEach(function (listener) {listener(this);});
  });*/
};

// TODO: hooks for rendering subtext (for the linked entity), colors,
// underlines, relations.

function getCandidateRelations(mentionPair) {
  var candidates = [];
  RELATIONS.forEach(function (reln) {
    if (reln["subject-types"].indexOf(mentionPair.first.type) >= 0 
        && reln["object-types"].indexOf(mentionPair.second.type) >= 0) {
      candidates.push(reln);
    }
  });
  return candidates;
}

/**
 * The relation widget is controlled by the RelationInterface. */
var RelationWidget = function(elem) {
  this.elem = elem;
};

// initialize the interface using @mentionPair. On completion, call @cb.
RelationWidget.prototype.init = function(mentionPair, cb) {
  this.cb = cb;
  console.log("initializing relation widget for", mentionPair);

  this.relns = getCandidateRelations(mentionPair);
  console.log("using candiates", this.relns);
  for (var i = 0; i < this.relns.length; i++) {
    this.elem.append(this.makeRelnOption(this.relns[i], i));
  }
}

RelationWidget.prototype.makeRelnOption = function(reln, id) {
  var self = this;
  var div = $("#relation-option-widget").clone();
  div.html(div.html().replace("{short}", reln.short));
  div.attr("id", "relation-option-" + id);
  div.on("click.kbpo.relationWidget", function(evt) {self.done(reln.name)});
  return div;
}

// TODO: support editing.
// The widget selection is done -- send back results.
RelationWidget.prototype.done = function(chosen_reln) {
  // Clear the innards of the html.
  this.elem.html("");
  if (this.cb) {
    this.cb(chosen_reln);
  } else {
    console.log("Relation chosen but no callback", chosen_reln);
  }
}

/**
 * Stores actual relations and iterates through every mention pair in
 * the document, controlling various UI elements.
 */
var RelationInterface = function(docWidget, relnWidget) {
  this.docWidget = docWidget; 
  this.relnWidget = relnWidget; 
};

// Iterates through the mention pairs provided.
RelationInterface.prototype.run = function(mentionPairs) {
  //this.mentions = mentions;
  //this.mentionPairs = constructMentionPairs(mentions);
  this.mentionPairs = mentionPairs;

  this.currentIndex = -1;
  this.next();
}

// Draw mention pair
RelationInterface.prototype.select = function(mentionPair) {
  mentionPair.first.tokens.forEach(function(t) {t.addClass("subject");});
  mentionPair.second.tokens.forEach(function(t) {t.addClass("object");});
}

RelationInterface.prototype.unselect = function(mentionPair) {
  mentionPair.first.tokens.forEach(function(t) {t.removeClass("subject");});
  mentionPair.second.tokens.forEach(function(t) {t.removeClass("object");});
}

// Progress to the next mention pair.
RelationInterface.prototype.next = function() {
  this.currentIndex += 1;
  if (this.currentIndex > this.mentionPairs.length - 1) {
    return this.done();
  }

  var mentionPair = this.mentionPairs[this.currentIndex];
  this.select(mentionPair);
  this.relnWidget.init(mentionPair, function(reln) {
    // TODO: Register that reln was chosen.
    // TODO: move on to next.
  });
}

// Called when the interface is done.
RelationInterface.prototype.done = function() {
}

// TODO: highlight a given mention pair
// TODO: activate relation selection interface.
// TODO: progress the interface when done.

// TODO: allow moving to a previous mention pair for correction.

