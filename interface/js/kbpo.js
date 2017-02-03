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
  //if (doc["mentions"]) {
  //  this.setMentions(doc["mentions"]);
  //}
};

DocWidget.prototype.setSuggestions = function(mentions) {
  var self = this;
  mentions.forEach(function(m) {
    m.tokens = self.getTokens(m.doc_char_begin, m.doc_char_end);
    m.tokens.forEach(function(t) {
      $(t).addClass("suggestion");
      t.suggestedMention = m;
    });
  });
};

DocWidget.prototype.setMentions = function(mentions) {
  var self = this;
  mentions.forEach(function(m) {
    m.tokens = self.getTokens(m.doc_char_begin, m.doc_char_end);
    m.tokens.forEach(function(t) {
      $(t).addClass("true-suggestion");
      t.mention = m;
    });
  });
};

DocWidget.prototype.getTokens = function(docCharBegin, docCharEnd) {
  return $('span.token').filter(function(_, t) {
    if (t.token.doc_char_begin >= docCharBegin 
        && t.token.doc_char_end <= docCharEnd) {
    }
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

DocWidget.prototype.highlightListeners = []
DocWidget.prototype.mouseEnterListeners = []
DocWidget.prototype.mouseLeaveListeners = []
DocWidget.prototype.clickListeners = []

DocWidget.prototype.isSentence = function(node) {
  return node.classList.contains("sentence");
}
DocWidget.prototype.isToken = function(node) {
  return node.classList.contains("token");
}
DocWidget.prototype.isMention = function(node) {
  return node.classList.contains("mention");
}

/**
 * Attaches handlers to the DOM elements in the document and forwards
 * events to the listeners.
 */
DocWidget.prototype.attachHandlers = function() {
  var self = this;

  // highlightListeners (a bit complicated because selection objects must
  // be handled.
  this.elem.on("mouseup.kbpo.docWidget", function(evt) { // Any selection in the document.
    var sel = document.getSelection();
    //if (sel.isCollapsed) return; // Collapsed => an empty selection.
    if (!self.elem[0].contains(sel.anchorNode)) return;
    if (sel.isCollapsed) {
      // This is a click event.
      var parents = $(sel.anchorNode).parentsUntil(".sentence");
      var startNode = parents[parents.length-1];

      console.assert(startNode && startNode.nodeName != "HTML");
      // startNode is either a token or a sentence.
      if (self.isToken(startNode)) {
        selectedTokens = [startNode];
        self.highlightListeners.forEach(function (listener) {listener(selectedTokens);});
      } else if (self.isMention(startNode)) {
        self.clickListeners.forEach(function (cb) {cb(startNode.mention);});
      } else {
        console.log("[Error] selected anchor node is not part of a sentence or a token", sel.anchorNode.parentNode);
        sel.collapseToEnd();
        return;
      }
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
    if (startNode != endNode && $(startNode).nextAll().filter(endNode).length === 0) {
      var tmpNode = endNode;
      endNode = startNode;
      startNode = tmpNode;
    } 
    console.assert(startNode == endNode || $(startNode).nextAll(endNode).length !== 0, "[Warning] start node does not preceed end node", startNode, endNode);

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
    
    self.highlightListeners.forEach(function (listener) {listener(selectedTokens);});

    sel.collapseToEnd();
  });

  // mouseEnter
  // this.elem.find('span.token').on("mouseenter.kbpo.docWidget", function(evt) { // Any selection in the document.
  //   self.mouseEnterListeners.forEach(function (listener) {listener(this);});
  // });

  // // mouseLeave
  // this.elem.find('span.token').on("mouseleave.kbpo.docWidget", function(evt) { // Any selection in the document.
  //   self.mouseLeaveListeners.forEach(function (listener) {listener(this);});
  // });

  // clickListeners
  /*this.elem.find("span.token").on("click.kbpo.docWidget", function(evt) {
    console.log("span-click:", this);
    self.clickListeners.forEach(function (listener) {listener(this);});
  });*/
};

// Create a mention from a set of spans.
DocWidget.prototype.addMention = function(mention) {
  var self = this;
  $(mention.tokens).wrapAll($("<span class='mention' />").attr("id", "mention-"+mention.id));
  var elem = $(mention.tokens[0].parentNode)[0];
  // Create links between the mention and DOM elements.
  elem.mention = mention;
  mention.elem = elem;
  mention.tokens.forEach(function(t) {t.mention = mention});

  return this.updateMention(mention);
}
DocWidget.prototype.updateMention = function(mention) {
  var elem = $(mention.elem);

  // If we have type and entity information, populate.
  if (mention.entity && mention.entity.gloss) {
    if (elem.find(".link-marker").length == 0) elem.prepend($("<span class='link-marker' />"));
    elem.find(".link-marker")
      .html(mention.entity.gloss + "<sup>" + (mention.entity.idx ? mention.entity.idx : "") + "</sup>");
  } else {
    elem.find(".link-marker").remove();
  }
  if (mention.type) {
    elem.addClass(mention.type.name);
    if (elem.find(".type-marker").length == 0) 
      elem.append($("<span class='type-marker fa fa-fw' />"));
    elem.find('.type-marker')
      .attr("class", "type-marker fa fa-fw").addClass(mention.type.icon);
  } else {
    elem.find(".type-marker").remove();
  }
  return elem;
}


DocWidget.prototype.removeMention = function(mention) {
  var div = $(mention.tokens[0].parentNode);
  div.find(".link-marker").remove();
  div.find(".type-marker").remove();
  console.log(mention.tokens);
  for(var i=0; i<mention.tokens.length; i++){
        mention.tokens[i].mention = undefined;
  }
  $(mention.tokens).unwrap();
}

DocWidget.prototype.highlightMention = function(mention) {
  $(mention.elem).addClass("highlight");
}

DocWidget.prototype.unhighlightMention = function(mention) {
  $(mention.elem).removeClass("highlight");
}

DocWidget.prototype.selectMention = function(mention) {
  $(mention.elem).addClass("selected");
}

DocWidget.prototype.unselectMention = function(mention) {
  $(mention.elem).removeClass("selected");
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
  if (reln.image !=""){
    div.find('img').removeClass('hidden').attr('src', 'images/relations/'+reln.image);
  }
  else if(reln.icon != ""){
    div.find('.icon').removeClass('hidden').addClass(reln.icon);
  }
  else{
    div.find('.icon').removeClass('hidden').addClass('fa-question-circle-o').css('color',  'coral');
  }
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
    .replace("{subject}", mentionPair.subject.gloss)
    .replace("{object}", mentionPair.object.gloss);
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

  this.listWidget.mouseEnterListeners.push(function(p) {self.highlightExistingMentionPair(p)});
  this.listWidget.mouseLeaveListeners.push(function(p) {self.unhighlightExistingMentionPair(p)});
  this.listWidget.clickListeners.push(function(p) {self.editExistingMentionPair(p)});

  this.docWidget.elem[0].scrollTop = 0;

  $("#done")[0].disabled = true;
  $("#back")[0].disabled = true;

  $("#back").on("click.kbpo.interface", function (evt) {
    self.editExistingMentionPair(self.mentionPairs[self.currentIndex-1]); 
    return false;
  });

  $("#done").on("click.kbpo.interface", function (evt) {
    var relations = [];
    self.listWidget.relations().each(function(_, e){
      e = e.mentionPair;
      relations.push({
        "subject": (e.subject).toJSON(),
        "relation": e.relation.name,
        "object": (e.object).toJSON(),
      });
    });
    var data = JSON.stringify(relations);
    $("#relations-output").attr('value', data);
    self.doneListeners.forEach(function(cb) {cb(data);});
    //return true;
  });
};

RelationInterface.prototype.doneListeners = [];
// Iterates through the mention pairs provided.
RelationInterface.prototype.run = function(mentions) {
  var self = this;
  this.mentions = [];

  mentions.forEach(function (m) {
    m.tokens = self.docWidget.getTokens(m.doc_char_begin, m.doc_char_end);
    if (m.tokens.length > 0) {
      m = new Mention(m);
      self.docWidget.addMention(m);
      self.mentions.push(m);
    }
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
  if (m.gloss == n.gloss) return false;
  if (m.entity.link == n.entity.link) return false;
  if (m.type.name == "PER") {
    return true;
  } else if (m.type.name == "ORG") {
    return !(n.type.name == "PER") && !(n.type.name == "TITLE");
  } else { // All other mentions are not entities; can't be subjects.
    return false;
  }
}

function notDuplicated(pairs, m, n) {
  // Only need to look backwards through list until the sentence
  // limit
  console.log(pairs)
  for(var i = pairs.length-1; i >= 0; i--) {
    var m_ = pairs[i].subject;
    var n_ = pairs[i].object;

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

  //var seenEntities = {}; // If you see two entities with the same link, don't ask for another relation between them?

  // Get pairs.
  for (var i = 0; i < mentions.length; i++) {
    var m = mentions[i];
    // - Go backwards until you cross a sentence boundary.
    for (var j = i-1; j >= 0; j--) {
      var n = mentions[j];
      if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 0) break;

      // Check that the pair is type compatible and not duplicated.
      if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n)) {
        pairs.push({'subject':m,'object':n});
      }
    }
    // - Go forwards until you cross a sentence boundary.
    for (var j = i+1; j < mentions.length; j++) {
      var n = mentions[j];
      if (Math.abs(m.sentenceIdx - n.sentenceIdx) > 0) break;
      // Check that the pair is type compatible and not duplicated.
      if (isRelationCandidate(m,n) && notDuplicated(pairs, m, n))
        pairs.push({'subject':m,'object':n});
    }
  }
  for (var i = 0; i < pairs.length; i++) {
    pairs[i].id = i;
    pairs[i].relation = null; // The none relation.
  }

  return pairs;
}

function centerOnMention(m) {
  var sentence = $(m.elem).parent();
  var elem = null;
  if (sentence.prev().length > 0) {
    elem = sentence.prev()[0];
//.scrollIntoView(true);
  } else {
    elem = sentence[0];
//.scrollIntoView(true);
  }
    var topPosRel = elem.offsetTop;
    console.log(topPosRel);
    var parentPosRel = $('#document')[0].offsetTop;
    console.log(parentPosRel);
    $('#document').scrollTop(topPosRel - parentPosRel);
}

function centerOnMentionPair(p) {
  if (p.subject.doc_char_begin < p.object.doc_char_begin)
    centerOnMention(p.subject);
  else
    centerOnMention(p.object);
}

// Draw mention pair
RelationInterface.prototype.select = function(mentionPair) {
  // Move to the location.
  centerOnMentionPair(mentionPair);
  mentionPair.subject.tokens.forEach(function(t) {$(t).addClass("subject highlight");});
  mentionPair.object.tokens.forEach(function(t) {$(t).addClass("object highlight");});
  $(mentionPair.subject.elem).parent().addClass("highlight");

}

RelationInterface.prototype.unselect = function(mentionPair) {
  mentionPair.subject.tokens.forEach(function(t) {$(t).removeClass("subject highlight");});
  mentionPair.object.tokens.forEach(function(t) {$(t).removeClass("object highlight");});
  $(mentionPair.subject.elem).parent().removeClass("highlight");
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

RelationListWidget.prototype.mouseEnterListeners = [];
RelationListWidget.prototype.mouseLeaveListeners = [];
RelationListWidget.prototype.clickListeners = [];

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
    self.mouseEnterListeners.forEach(function(cb) {cb(mentionPair);});
  });
  div.on("mouseleave.kbpo.list", function(evt) {
    //console.log("mention.mouseleave", mentionPair);
    self.mouseLeaveListeners.forEach(function(cb) {cb(mentionPair);});
  });
  div.on("click.kbpo.click", function(evt) {
    //console.log("mention.cancel", mentionPair);
    self.clickListeners.forEach(function(cb) {cb(mentionPair);});
  });

  this.elem.append(div);
  return true;
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

RelationListWidget.prototype.relations = function() {
  return this.elem.find(".extraction").not("#extraction-empty").not("#extraction-template");
}


// TODO: Allow for keyboard shortcuts.
