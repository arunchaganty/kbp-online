/*
 * KBP online.
 * Arun Chaganty <arunchaganty@gmail.com>
 */

// 
var Mention = function(m) {

}

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
    span[0].sentenceIdx = i;

    for (var j = 0; j < sentence.length; j++) {
      var token = sentence[j];
      var tokenSpan = $("<span>", {'class': 'token', 'id': 'token-' + i + '-' + j})
                   .text(token.word);
      tokenSpan[0].token = token;
      tokenSpan[0].sentenceIdx = i;
      tokenSpan[0].tokenIdx = j;

      if (j > 0 && sentence[j].doc_char_begin > sentence[j-1].doc_char_end) {
        tokenSpan.html('&nbsp;' + tokenSpan.text());
      }
      span.append(tokenSpan);
    }
    this.elem.append(span);
  };
};

DocWidget.prototype.getTokens = function(docCharBegin, docCharEnd) {
  return $('span.token').filter(function(_, t) {
    return t.token.doc_char_begin >= docCharBegin 
        && t.token.doc_char_end <= docCharEnd
  }).get(); 
};

// Build mention.
DocWidget.prototype.buildMention = function(m) {
  m.tokens = this.getTokens(m.doc_char_begin, m.doc_char_end);
  m.tokens.forEach(function(t) {$(t).addClass("mention");});
  console.assert(m.tokens.length > 0);

  m.sentenceIdx = m.tokens[0].sentenceIdx;
  return m;
}

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
    
    //console.log("span-selected:", selectedTokens);
    self.highlightListener.forEach(function (listener) {listener(selectedTokens);});

    sel.collapseToEnd();
  });

  // mouseEnter
  this.elem.find('span.token').on("mouseenter.kbpo.docWidget", function(evt) { // Any selection in the document.
    //console.log("span-enter:", this);
    self.mouseEnterListener.forEach(function (listener) {listener(this);});
  });

  // mouseLeave
  this.elem.find('span.token').on("mouseleave.kbpo.docWidget", function(evt) { // Any selection in the document.
    //console.log("span-leave:", this);
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
    if (reln["subject-types"].indexOf(mentionPair[0].type) >= 0 
        && reln["object-types"].indexOf(mentionPair[1].type) >= 0) {
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
  this.mentionPair = mentionPair;
  this.cb = cb;
  console.log("initializing relation widget for", mentionPair);

  this.relns = getCandidateRelations(mentionPair);
  console.log("using candiates", this.relns);
  for (var i = 0; i < this.relns.length; i++) {
    this.elem.find("#relation-options").append(this.makeRelnOption(this.relns[i], i));
  }
}

RelationWidget.prototype.updateText = function(template) {
  var div = this.elem.find("#relation-option-preview");
  if (template) { // update text
    var txt = template
      .replace("{subject}", "<span class='subject'>" + this.mentionPair[0].gloss + "</span>")
      .replace("{object}", "<span class='object'>" + this.mentionPair[1].gloss + "</span>");
    div.html(txt);
  } else { // clear
    div.html("");
  }
}

RelationWidget.prototype.makeRelnOption = function(reln, id) {
  var self = this;
  var div = $("#relation-option-widget").clone();
  div.html(div.html().replace("{short}", reln.short));
  div.attr("id", "relation-option-" + id);
  div.on("click.kbpo.relationWidget", function(evt) {self.done(reln.name)});
  // Update widget text. 
  div.on("mouseenter.kbpo.relationWidget", function(evt) {self.updateText(reln.template)});
  div.on("mouseleave.kbpo.relationWidget", function(evt) {self.updateText()});
  return div;
}

// TODO: support editing.
// The widget selection is done -- send back results.
RelationWidget.prototype.done = function(chosen_reln) {
  // Clear the innards of the html.
  this.elem.find("#relation-options").html("");
  this.elem.find("#relation-option-preview").html("");
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
RelationInterface.prototype.run = function(mentions) {
  var self = this;
  this.mentions = [];
  mentions.forEach(function (m) {self.mentions.push(self.docWidget.buildMention(m))});
  this.mentionPairs = this.constructMentionPairs(mentions);

  this.currentIndex = -1;
  this.next();
}

function outOfSentenceLimit(m, n) {
  return Math.abs(m.sentenceIdx - n.sentenceIdx) > 1;
}

function isRelationCandidate(m, n) {
  if (m.type == "PER") {
    return true;
  } else if (m.type == "ORG") {
    return !(n.type == "TITLE");
  } else if (m.type == "GPE") {
    return (n.type == "ORG");
  } else { // All other mentions are not entities; can't be subjects.
    return false;
  }
}

function notDuplicated(pairs, m, n) {
  // Only need to look backwards through list until the sentence
  // limit
  for(var i = pairs.length-1; i >= 0; i--) {
    var m_ = pairs[i][0];
    var n_ = pairs[i][1];

    if (outOfSentenceLimit(m, m_)
        || outOfSentenceLimit(m, n_)
        || outOfSentenceLimit(n, m_)
        || outOfSentenceLimit(n, n_)) break;
    if (m_ === n && n_ == m) return false;
  }
  return true;
}


// For every pair of mentions in a span of (2) sentences.
RelationInterface.prototype.constructMentionPairs = function(mentions) {
  var pairs = [];

  // Get pairs.
  for (var i = 0; i < mentions.length; i++) {
    var m = mentions[i];
    // - Go backwards until you cross a sentence boundary.
    for (var j = i-1; j >= 0; j--) {
      var n = mentions[j];
      if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 1 ) break;

      // Check that the pair is type compatible and not duplicated.
      if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n))
        pairs.push([m,n]);
    }
    // - Go forwards until you cross a sentence boundary.
    for (var j = i+1; j < mentions.length; j++) {
      var n = mentions[j];
      if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 1 ) break;
      // Check that the pair is type compatible and not duplicated.
      if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n))
        pairs.push([m,n]);
    }
  }

  console.log(pairs);

  return pairs;
}

function centerOnMention(m) {
  loc = "#token-" + Math.max(0, m.sentenceIdx - 1) + "-0";
  $(loc)[0].scrollIntoView();
  console.log(loc);
  //document.location.hash = loc;
}

// Draw mention pair
RelationInterface.prototype.select = function(mentionPair) {
  // Move to the location.
  centerOnMention(mentionPair[0]);
  document.location.hash = $(mentionPair[0].tokens[0]).attr("id")
  mentionPair[0].tokens.forEach(function(t) {$(t).addClass("subject");});
  mentionPair[1].tokens.forEach(function(t) {$(t).addClass("object");});
}

RelationInterface.prototype.unselect = function(mentionPair) {
  mentionPair[0].tokens.forEach(function(t) {$(t).removeClass("subject");});
  mentionPair[1].tokens.forEach(function(t) {$(t).removeClass("object");});
}

// Progress to the next mention pair.
RelationInterface.prototype.next = function() {
  var self = this;
  this.currentIndex += 1;
  if (this.currentIndex > this.mentionPairs.length - 1) {
    return this.done();
  }

  var mentionPair = this.mentionPairs[this.currentIndex];
  this.select(mentionPair);
  this.relnWidget.init(mentionPair, function(reln) {
    mentionPair.relation = reln;
    self.unselect(mentionPair);
    self.next();
  });
}

// Called when the interface is done.
RelationInterface.prototype.done = function() {
  // Hide the relation panel, and show the Done > (submit) button.
  $("#relation-row").addClass("hidden");
  $("#done-row").removeClass("hidden");
}

// TODO: Show previous reported relations.
// TODO: allow moving to a previous mention pair for correction.

