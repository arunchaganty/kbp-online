/*
 * KBP online.
 * Arun Chaganty <arunchaganty@gmail.com>
 */

// 
var Mention = function(m) {
  this.id = Mention.count++;
  this.tokens = m.tokens;
  this.sentenceIdx = m.tokens[0].sentenceIdx;
  this.type = TYPES[m.type];
  this.gloss = m.gloss;
  this.canonicalId = m['canonical-id'];
  this.canonicalGloss = m['canonical-gloss'];
}
Mention.count = 0;

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

  m.inRelation = false;
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

// Create a mention from a set of spans.
DocWidget.prototype.addMention = function(mention) {
  $(mention.tokens).wrapAll($("<span class='mention' />").addClass(mention.type).attr("id", "mention-"+mention.id));
  var elem = $(mention.tokens[0].parentNode);
  elem[0].mention = mention;

  elem.prepend($("<span class='link-marker' />").html(mention.canonicalGloss + "<sup>" + mention.canonicalId + "</sup>"));
  elem.prepend($("<span class='type-marker fa fa-fw' />").addClass(mention.type.icon));
  return elem;
}

DocWidget.prototype.removeMention = function(mention) {
  var div = $(mention.tokens[0].parentNode);
  div.find(".link-marker").remove();
  div.find(".type-marker").remove();
  $(mention.tokens).unwrap();
}

function getCandidateRelations(mentionPair) {
  var candidates = [];
  RELATIONS.forEach(function (reln) {
    if (reln.isApplicable(mentionPair)) candidates.push(reln);
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
  this.elem.find("#relation-options").empty(); // Clear.
  this.elem.find("#relation-option-preview").empty(); // Clear.
  for (var i = 0; i < this.relns.length; i++) {
    var relnDiv = this.makeRelnOption(this.relns[i], i);
    // if this relation has already been selected, then show it in
    // a different color.
    if (this.mentionPair.relation != null && this.mentionPair.relation.name == this.relns[i].name) relnDiv.addClass("btn-primary"); 
    this.elem.find("#relation-options").append(relnDiv);
  }

  this.updateText(this.renderTemplate(this.mentionPair))
}

RelationWidget.prototype.updateText = function(previewText) {
  var div = this.elem.find("#relation-option-preview");
  div.html(previewText || "");
}

RelationWidget.prototype.makeRelnOption = function(reln, id) {
  var self = this;
  var div = $("#relation-option-widget").clone();
  div.html(div.html().replace("{short}", reln.short));
  div.attr("id", "relation-option-" + id);
  div.on("click.kbpo.relationWidget", function(evt) {self.done(reln)});
  // Update widget text. 
  div.on("mouseenter.kbpo.relationWidget", function(evt) {self.updateText(reln.renderTemplate(self.mentionPair))});
  div.on("mouseleave.kbpo.relationWidget", function(evt) {self.updateText(self.renderTemplate(self.mentionPair))});
  return div;
}

RelationWidget.prototype.renderTemplate = function(mentionPair) {
  var template = "Please choose how <span class='subject'>{subject}</span> and <span class='object'>{object}</span> are related from the options below.";
  return template
    .replace("{subject}", mentionPair[0].gloss)
    .replace("{object}", mentionPair[1].gloss);
}

// The widget selection is done -- send back results.
RelationWidget.prototype.done = function(chosen_reln) {
  // Clear the innards of the html.
  this.elem.find("#relation-options").empty();
  this.elem.find("#relation-option-preview").empty();

  // Send a call back to the interface.
  if (this.cb) {
    this.cb(chosen_reln);
  } else {
    console.log("[Warning] Relation chosen but no callback", chosen_reln);
  }
}

/**
 * Stores actual relations and iterates through every mention pair in
 * the document, controlling various UI elements.
 */
var RelationInterface = function(docWidget, relnWidget, listWidget) {
  var self = this;
  this.docWidget = docWidget; 
  this.relnWidget = relnWidget; 
  this.listWidget = listWidget; 

  this.listWidget.mouseEnterListener.push(function(p) {self.highlightExistingMentionPair(p)});
  this.listWidget.mouseLeaveListener.push(function(p) {self.unhighlightExistingMentionPair(p)});
  this.listWidget.clickListener.push(function(p) {self.editExistingMentionPair(p)});

  $("#done")[0].disabled = true;
  $("#back")[0].disabled = true;

  $("#back").on("click.kbpo.interface", function (evt) {
    self.editExistingMentionPair(self.mentionPairs[self.currentIndex-1]);
  });
};

// Iterates through the mention pairs provided.
RelationInterface.prototype.run = function(mentions) {
  var self = this;
  this.mentions = [];
  mentions.forEach(function (m) {
    m.tokens = self.docWidget.getTokens(m['doc_char_begin'], m['doc_char_end']);
    m = new Mention(m);
    self.docWidget.addMention(m);
    self.mentions.push(m);
  });
  this.mentionPairs = this.constructMentionPairs(this.mentions);

  this.currentIndex = -1;
  this.viewStack = []; // Used when changing relations.
  this.next();
}

function outOfSentenceLimit(m, n) {
  return Math.abs(m.sentenceIdx - n.sentenceIdx) > 1;
}

function isRelationCandidate(m, n) {
  if (m.type.name == "PER") {
    return true;
  } else if (m.type.name == "ORG") {
    return !(n.type.name == "TITLE");
  } else if (m.type.name == "GPE") {
    return (n.type.name == "ORG");
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
  console.log(mentions);

  // Get pairs.
  for (var i = 0; i < mentions.length; i++) {
    var m = mentions[i];
    // - Go backwards until you cross a sentence boundary.
    for (var j = i-1; j >= 0; j--) {
      var n = mentions[j];
      if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 1 ) break;

      // Check that the pair is type compatible and not duplicated.
      if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n)) {
        pairs.push([m,n]);
      }
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
  for (var i = 0; i < pairs.length; i++) {
    pairs[i].id = i;
    pairs[i].relation = null; // The none relation.
  }

  console.log(pairs);
  return pairs;
}

function centerOnMention(m) {
  loc = "#mention-" + m.id;
  console.log(loc);
  $(loc)[0].scrollIntoView();
}

// Draw mention pair
RelationInterface.prototype.select = function(mentionPair) {
  // Move to the location.
  centerOnMention(mentionPair[0]);
  document.location.hash = $(mentionPair[0].tokens[0]).attr("id")
  mentionPair[0].tokens.forEach(function(t) {$(t).addClass("subject selected");});
  mentionPair[1].tokens.forEach(function(t) {$(t).addClass("object selected");});
}

RelationInterface.prototype.unselect = function(mentionPair) {
  mentionPair[0].tokens.forEach(function(t) {$(t).removeClass("subject selected");});
  mentionPair[1].tokens.forEach(function(t) {$(t).removeClass("object selected");});
}

RelationInterface.prototype.highlightExistingMentionPair = function(mentionPair) {
  this.unselect(this.mentionPair);
  this.select(mentionPair);
}
RelationInterface.prototype.unhighlightExistingMentionPair = function(mentionPair) {
  this.unselect(mentionPair);
  this.select(this.mentionPair);
}
RelationInterface.prototype.editExistingMentionPair = function(mentionPair) {
  this.unselect(this.mentionPair);
  if (this.viewStack.length == 0) this.viewStack.push(this.currentIndex);
  this.next(mentionPair.id);
}


// Progress to the next mention pair.
RelationInterface.prototype.next = function(idx) {
  var self = this;

  if (idx != null) {
    this.currentIndex = idx;
  } else if (this.viewStack.length > 0) {
    this.currentIndex = this.viewStack.pop();
  } else {
    this.currentIndex += 1;
  }
  if (this.currentIndex > 0) {
    $("#back")[0].disabled = false;
  } else {
    $("#back")[0].disabled = true;
  }
  if (this.currentIndex > this.mentionPairs.length - 1) {
    return this.done();
  } else {
    $("#relation-row").removeClass("hidden");
  }
  var mentionPair = this.mentionPairs[this.currentIndex];

  this.mentionPair = mentionPair;
  this.select(mentionPair);
  this.relnWidget.init(mentionPair, function(reln) {
    self.unselect(mentionPair);

    // Remove a previous relation from the list if it existed.
    if (mentionPair.relation && mentionPair.relation.name != reln.name) {
      self.listWidget.removeRelation(mentionPair);
    } 
    if (mentionPair.relation && mentionPair.relation.name == reln.name) {
    } else {
      // Set the relation of the pair.
      mentionPair.relation = reln;
      // Add mention to the relationList widget.
      if (reln.name != "no_relation") {
        self.listWidget.addRelation(mentionPair);
      }
    }

    self.next();
  });
}

// Called when the interface is done.
RelationInterface.prototype.done = function() {
  // Hide the relation panel, and show the Done > (submit) button.
  $("#done")[0].disabled = false;
  $("#relation-row").addClass("hidden");
}

RelationListWidget = function(elem) {
  this.elem = elem;
}

RelationListWidget.prototype.mouseEnterListener = [];
RelationListWidget.prototype.mouseLeaveListener = [];
RelationListWidget.prototype.clickListener = [];

RelationListWidget.prototype.addRelation = function(mentionPair) {
  var self = this;

  // Make sure that #empty-extraction is hidden.
  this.elem.find("#extraction-empty").addClass("hidden");

  // Create a new relation to add to the list.
  var div = this.elem.find("#extraction-template").clone();
  div.find(".relation-sentence").html(mentionPair.relation.renderTemplate(mentionPair));
  div.removeClass("hidden");
  div.attr("id", "mention-pair-" + mentionPair.id);
  div[0].mentionPair = mentionPair;

  // attach listeners.
  div.on("mouseenter.kbpo.list", function(evt) {
    //console.log("mention.mouseenter", mentionPair);
    self.mouseEnterListener.forEach(function(cb) {cb(mentionPair);});
  });
  div.on("mouseleave.kbpo.list", function(evt) {
    //console.log("mention.mouseleave", mentionPair);
    self.mouseLeaveListener.forEach(function(cb) {cb(mentionPair);});
  });
  div.on("click.kbpo.click", function(evt) {
    //console.log("mention.cancel", mentionPair);
    self.clickListener.forEach(function(cb) {cb(mentionPair);});
  });

  this.elem.append(div);
}

RelationListWidget.prototype.removeRelation = function(mentionPair) {
  this.elem.find(".extraction")
    .filter(function (_, e) {
      return e.mentionPair !== undefined && e.mentionPair.id == mentionPair.id;})
    .remove();
  if (this.elem.find(".extraction").length == 2) {
    this.elem.find("#extraction-empty").removeClass("hidden");
  }
}


// TODO: Allow for keyboard shortcuts.
