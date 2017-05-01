/*!
 * KBPOnline: The DocumentWidget
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function () {
  /**
   * The document object -- handles the storage and representation of
   * sentences.
   *
   * @elem - DOM element that this widget is rooted at.
   */
  var DocWidget = function(elem) {
    console.assert(elem);
    this.elem = $(elem);
  };

  // Load a document specified in json @doc.
  DocWidget.prototype.loadDocument = function(doc) {
    this.doc = doc;
    this._insertIntoDOM(doc);
    this.attachHandlers();
  };

  // Insert the document @doc into the DOM
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
    }
  };

  // Highlight certain portions of the document.
  DocWidget.prototype.setSuggestions = function(mentions, highlightClass) {
    var self = this;

    if (highlightClass === null) {
      highlightClass = "suggestion";
    }

    mentions.forEach(function(m) {
      m.tokens = self.getTokens(m.doc_char_begin, m.doc_char_end);
      m.tokens.forEach(function(t) {
        $(t).addClass("suggestion");
        t.suggestedMention = m;
      });
      $(m.tokens[m.tokens.length-1]).addClass("suggestion-end");
    });
  };

  // Provide the DOM elements corresponding to tokens between specified
  // character offsets 
  DocWidget.prototype.getTokens = function(docCharBegin, docCharEnd) {
    return $('span.token').filter(function(_, t) {
      if (t.token.doc_char_begin >= docCharBegin && 
          t.token.doc_char_end <= docCharEnd) {
      }
      return t.token.doc_char_begin >= docCharBegin && 
        t.token.doc_char_end <= docCharEnd;
    }).get(); 
  };

  // Create a mention from a set of spans.
  DocWidget.prototype.addMention = function(mention) {
    var self = this;
    $(mention.tokens).wrapAll($("<span class='mention' />").attr("id", "mention-"+mention.id));
    var elem = $(mention.tokens[0].parentNode)[0];
    // Create links between the mention and DOM elements.
    elem.mention = mention;
    mention.elem = elem;
    mention.tokens.forEach(function(t) {t.mention = mention;});

    return this.updateMention(mention);
  };
  DocWidget.prototype.updateMention = function(mention) {
    var elem = $(mention.elem);

    // If we have type and entity information, populate.
    if (mention.entity && mention.entity.gloss) {
      if (elem.find(".link-marker").length === 0) elem.prepend($("<span class='link-marker' />"));
      elem.find(".link-marker")
        .html(mention.entity.gloss + "<sup>" + (mention.entity.idx ? mention.entity.idx : "") + "</sup>");
    } else {
      elem.find(".link-marker").remove();
    }
    if (mention.type) {
      elem.addClass(mention.type.name);
      if (elem.find(".type-marker").length === 0) 
        elem.append($("<span class='type-marker fa fa-fw' />"));
      elem.find('.type-marker')
        .attr("class", "type-marker fa fa-fw").addClass(mention.type.icon);
    } else {
      elem.find(".type-marker").remove();
    }
    return elem;
  };

  DocWidget.prototype.removeMention = function(mention) {
    var div = $(mention.tokens[0].parentNode);
    div.find(".link-marker").remove();
    div.find(".type-marker").remove();
    console.log(mention.tokens);
    for(var i=0; i<mention.tokens.length; i++){
          mention.tokens[i].mention = undefined;
    }
    $(mention.tokens).unwrap();
  };

  DocWidget.prototype.highlightMention = function(mention) {
    $(mention.elem).addClass("highlight");
  };

  DocWidget.prototype.unhighlightMention = function(mention) {
    $(mention.elem).removeClass("highlight");
  };

  DocWidget.prototype.selectMention = function(mention) {
    $(mention.elem).addClass("selected");
  };

  DocWidget.prototype.unselectMention = function(mention) {
    $(mention.elem).removeClass("selected");
  };

  // Listeners
  DocWidget.prototype.highlightListeners = [];
  DocWidget.prototype.clickListeners = [];

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

      var startNode;
      var selectedTokens;
      if (sel.isCollapsed) {
        // This is a click event.
        var parents = $(sel.anchorNode).parentsUntil(".sentence");
        startNode = parents[parents.length-1];

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
      } else if (!self.elem[0].contains(sel.anchorNode) || !self.elem[0].contains(sel.focusNode)) {
        // The selected elements are not even in the #document.
        sel.collapseToEnd();
        return;
      } else {
        // Handle the case that the node is an '&nbsp;' text.
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
        selectedTokens = [];
        while (startNode != endNode) {
          console.assert(startNode !== null);
          if ($(startNode).hasClass('token')) {
            selectedTokens.push(startNode);
          }
          startNode = startNode.nextSibling;
        }
        if ($(startNode).hasClass('token')) {
          selectedTokens.push(startNode);
        }

        self.highlightListeners.forEach(function (listener) {listener(selectedTokens);});
      }

      sel.collapseToEnd();
    });
  };

  return DocWidget;
});